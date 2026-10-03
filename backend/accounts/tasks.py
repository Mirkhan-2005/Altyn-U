from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

from .models import StudentProfile
from .services.profile_sync import sync_profile

import logging

from journal.services.import_queue import queue_journal_import


logger = logging.getLogger(__name__)


@shared_task(
    name="accounts.check_queue",
    ignore_result=False,
)
def check_queue():
    return {
        "status": "ok",
        "message": "Фоновая задача Altyn выполнена.",
    }


@shared_task(
    name="accounts.sync_profile",
    ignore_result=True,
    soft_time_limit=180,
    time_limit=240,
)
def sync_profile_task(user_id, requested_at):
    requested_at = parse_datetime(requested_at)

    if requested_at is None:
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

    # Используем существующий сервис:
    # имя, фамилия, GPA, фото и сообщения об ошибках.
    sync_profile(user)
        # Профиль уже сохранён — теперь можно загружать журналы.
    try:
        queue_journal_import(user)
    except Exception:
        logger.error(
            "Не удалось подготовить импорт журналов "
            "после загрузки профиля user_id=%s",
            user.pk,
        )