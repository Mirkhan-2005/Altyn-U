import hashlib
import secrets
from datetime import timedelta

from cryptography.fernet import Fernet

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework.exceptions import APIException, ValidationError

from ..models import PendingRegistration, PlatonusConnection


class RegistrationExpired(APIException):
    status_code = 410
    default_detail = (
        "Подтверждение истекло или уже использовано. "
        "Пройдите проверку Platonus снова."
    )


class AccountExists(APIException):
    status_code = 409
    default_detail = (
        "Аккаунт с этим ИИН уже существует. "
        "Перейдите на страницу входа."
    )


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_registration(iin, platonus_password):
    """Вызывать только после успешной проверки Platonus и согласия."""
    User = get_user_model()

    if User.objects.filter(iin=iin).exists():
        raise AccountExists()

    now = timezone.now()

    PendingRegistration.objects.filter(
        expires_at__lte=now,
    ).delete()

    token = secrets.token_urlsafe(32)

    cipher = Fernet(
        settings.PLATONUS_ENCRYPTION_KEY.encode("ascii")
    )

    encrypted = cipher.encrypt(
        platonus_password.encode("utf-8")
    ).decode("ascii")

    PendingRegistration.objects.create(
        token_digest=token_digest(token),
        iin=iin,
        encrypted_password=encrypted,
        expires_at=now + timedelta(minutes=10),
        consent_at=now,
        consent_version="platonus-sync-v1",
    )

    return token


def complete_registration(token, password):
    User = get_user_model()

    pending = PendingRegistration.objects.filter(
        token_digest=token_digest(token),
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()

    if pending is None:
        raise RegistrationExpired()

    if User.objects.filter(iin=pending.iin).exists():
        raise AccountExists()

    # ИИН берём из серверной записи подтверждения.
    user = User(iin=pending.iin)

    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(
            {"password": exc.messages}
        ) from None

    user.set_password(password)

    try:
        with transaction.atomic():
            now = timezone.now()

            # Только один запрос может использовать подтверждение.
            claimed = PendingRegistration.objects.filter(
                pk=pending.pk,
                used_at__isnull=True,
                expires_at__gt=now,
            ).update(used_at=now)

            if claimed != 1:
                raise RegistrationExpired()

            user.save(force_insert=True)

            PlatonusConnection.objects.create(
                user=user,
                encrypted_password=pending.encrypted_password,
                consent_at=pending.consent_at,
                consent_version=pending.consent_version,
                last_verified_at=pending.created_at,
            )

            PendingRegistration.objects.filter(
                iin=pending.iin,
            ).delete()

    except IntegrityError:
        if User.objects.filter(iin=pending.iin).exists():
            raise AccountExists() from None
        raise

    return user