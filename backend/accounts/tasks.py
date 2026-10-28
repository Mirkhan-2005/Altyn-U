import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from journal.services.import_queue import queue_journal_import

from .models import StudentProfile
from .services.profile_sync import sync_profile


logger = logging.getLogger(__name__)

# Две дополнительные попытки после первоначальной.
PHOTO_RETRY_DELAYS = (60, 180)


@shared_task(
    name="accounts.check_queue",
    ignore_result=False,
)
def check_queue():
    return {
        "status": "ok",
        "message": "Фоновая задача Altyn выполнена.",
    }


def schedule_photo_retry(profile, retry_number):
    if not getattr(profile, "photo_retryable", False):
        return

    if retry_number >= len(PHOTO_RETRY_DELAYS):
        logger.warning(
            "Повторные попытки загрузки фото исчерпаны: "
            "user_id=%s",
            profile.user_id,
        )
        return

    delay = PHOTO_RETRY_DELAYS[retry_number]
    requested_at = timezone.now()

    previous_message = profile.sync_message
    waiting_message = (
        f"{previous_message} "
        f"Повторная попытка {retry_number + 1}/"
        f"{len(PHOTO_RETRY_DELAYS)} запланирована "
        f"не раньше чем через {delay} сек."
    )

    # Меняем только состояние той попытки, которую завершили.
    # Если уже началось другое обновление, его не трогаем.
    changed = StudentProfile.objects.filter(
        pk=profile.pk,
        sync_status="partial",
        last_sync_attempt_at=profile.last_sync_attempt_at,
    ).update(
        sync_status="queued",
        sync_message=waiting_message,
        last_sync_attempt_at=requested_at,
    )

    if changed != 1:
        return

    try:
        sync_profile_task.apply_async(
            args=[
                profile.user_id,
                requested_at.isoformat(),
                retry_number + 1,
            ],
            queue="default",
            countdown=delay,
            retry=False,
        )

    except Exception:
        # Если отправить задачу не удалось, возвращаем partial.
        # Уже сохранённые данные и фотографию не изменяем.
        StudentProfile.objects.filter(
            pk=profile.pk,
            sync_status="queued",
            last_sync_attempt_at=requested_at,
        ).update(
            sync_status="partial",
            sync_message=(
                f"{previous_message} "
                "Не удалось поставить повторную попытку в очередь."
            ),
        )

        logger.error(
            "Не удалось отправить повторную задачу фото: "
            "user_id=%s",
            profile.user_id,
        )

    else:
        logger.info(
            "Повторная загрузка фото запланирована: "
            "user_id=%s, retry=%s, delay=%s",
            profile.user_id,
            retry_number + 1,
            delay,
        )


@shared_task(
    name="accounts.sync_profile",
    ignore_result=True,
    soft_time_limit=180,
    time_limit=240,
)
def sync_profile_task(user_id, requested_at, retry_number=0):
    requested_at = parse_datetime(requested_at)

    if requested_at is None:
        return

    if (
        type(retry_number) is not int
        or not 0 <= retry_number <= len(PHOTO_RETRY_DELAYS)
    ):
        return

    pending = StudentProfile.objects.filter(
        user_id=user_id,
        sync_status="queued",
        last_sync_attempt_at=requested_at,
    )

    user = get_user_model().objects.filter(
        pk=user_id,
        is_active=True,
    ).first()

    if user is None:
        pending.update(
            sync_status="error",
            sync_message="Аккаунт недоступен.",
        )
        return

    # Старую или повторно доставленную задачу не выполняем.
    if pending.update(sync_status="syncing") != 1:
        return

    profile = sync_profile(user)

    schedule_photo_retry(profile, retry_number)

    # Импорт журналов запускаем после первоначальной
    # синхронизации, не после каждой повторной попытки фото.
    if retry_number == 0:
        try:
            queue_journal_import(user)
        except Exception:
            logger.error(
                "Не удалось подготовить импорт журналов "
                "после загрузки профиля user_id=%s",
                user.pk,
            )