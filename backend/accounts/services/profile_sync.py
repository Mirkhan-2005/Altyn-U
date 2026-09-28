import logging
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from accounts.models import PlatonusConnection, StudentProfile
from .photo_client import PhotoCheck
from .platonus_client import Result


class SyncError(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code


@sensitive_variables()
def download_profile(user):
    connection = PlatonusConnection.objects.filter(user=user).first()

    if connection is None:
        raise SyncError("Подключение к Platonus не сохранено.", 409)

    try:
        cipher = Fernet(
            settings.PLATONUS_ENCRYPTION_KEY.encode("ascii")
        )
        password = cipher.decrypt(
            connection.encrypted_password.encode("ascii")
        ).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError, AttributeError):
        raise SyncError(
            "Не удалось расшифровать подключение. Проверьте ключ сервера.",
            500,
        )

    with PhotoCheck() as client:
        try:
            login = client.login(user.iin, password)
        finally:
            password = None

        if login.authenticated is not True:
            if login.status == "requires_code":
                raise SyncError(
                    "Platonus запросил код. Нужно повторное подключение.",
                    409,
                )

            if login.status in {
                "authentication_rejected",
                "not_confirmed",
            }:
                raise SyncError(
                    "Platonus не подтвердил вход. Проверьте подключение.",
                    409,
                )

            raise SyncError(
                "Platonus сейчас не подтвердил вход. Попробуйте позже."
            )

        role = client.check_role()

        if role.is_student is not True:
            code = 403 if role.is_student is False else 503
            raise SyncError("Роль студента не подтверждена.", code)

        study = client.check_study_status()

        if (
            study.study_status_verified is not True
            or study.active_student is not True
        ):
            code = 403 if study.active_student is False else 503
            raise SyncError(
                "Статус «Обучается» не подтверждён.",
                code,
            )

        result = client.get_profile()

        if isinstance(result, Result):
            raise SyncError(
                "Не удалось получить профиль из Platonus."
            )

        photo = client.get_photo()

    warnings = list(result.get("warnings", []))

    if isinstance(photo, Result):
        warnings.append(
            "Фото не обновлено; предыдущее фото сохранено, если оно было."
        )
        photo = None

    if client.logout_confirmed is not True:
        warnings.append(
            "Platonus не подтвердил завершение сессии."
        )

    return result["profile"], photo, warnings


def delete_photo(storage, name):
    if name:
        try:
            storage.delete(name)
        except Exception:
            logging.getLogger(__name__).warning(
                "Не удалось удалить старый файл фото."
            )


def sync_profile(user):
    if not user.is_active:
        raise SyncError("Аккаунт Altyn отключён.", 403)

    profile, _ = StudentProfile.objects.get_or_create(user=user)

    StudentProfile.objects.filter(pk=profile.pk).update(
        last_sync_attempt_at=timezone.now()
    )

    storage = StudentProfile._meta.get_field("photo").storage
    new_photo = None

    try:
        data, photo, warnings = download_profile(user)

        User = get_user_model()
        names = {}

        for field in ("first_name", "last_name"):
            value = data.get(field)

            if value is not None:
                max_length = User._meta.get_field(field).max_length

                if not isinstance(value, str) or len(value) > max_length:
                    raise SyncError(
                        "Имя или фамилия имеют неподдерживаемый формат."
                    )

                names[field] = value

        gpa = data.get("gpa")

        if gpa is not None:
            gpa = Decimal(gpa).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        if photo is not None:
            content, extension = photo

            try:
                new_photo = storage.save(
                    f"student_photos/{uuid4().hex}{extension}",
                    ContentFile(content),
                )
            except OSError:
                warnings.append(
                    "Не удалось сохранить новое фото; предыдущее сохранено."
                )

        now = timezone.now()

        # Запросы к Platonus уже завершены.
        # В транзакции выполняем только запись результата.
        with transaction.atomic():
            User.objects.filter(pk=user.pk).update(**names)

            profile = (
                StudentProfile.objects
                .select_for_update()
                .get(user=user)
            )

            old_photo = profile.photo.name

            if gpa is not None:
                profile.gpa = gpa
                profile.gpa_source = data["gpa_source"]
                profile.gpa_updated_at = now

            if new_photo is not None:
                profile.photo.name = new_photo
                profile.photo_updated_at = now

            profile.last_synced_at = now
            profile.sync_status = "partial" if warnings else "synced"
            profile.sync_message = " ".join(warnings)
            profile.save()

            PlatonusConnection.objects.filter(user=user).update(
                last_verified_at=now
            )

            if new_photo and old_photo and old_photo != new_photo:
                transaction.on_commit(
                    lambda: delete_photo(storage, old_photo)
                )

    except Exception as exc:
        if new_photo:
            delete_photo(storage, new_photo)

        error = (
            exc
            if isinstance(exc, SyncError)
            else SyncError(
                "Обновление не выполнено. Попробуйте позже."
            )
        )

        StudentProfile.objects.filter(pk=profile.pk).update(
            sync_status="error",
            sync_message=str(error),
        )

        raise error from None

    user.refresh_from_db()
    return profile