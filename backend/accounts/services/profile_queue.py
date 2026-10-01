import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import PlatonusConnection, StudentProfile
from .profile_sync import SyncError


logger = logging.getLogger(__name__)


def queue_profile(user, *, force=False):
    if not user.is_active:
        raise SyncError("Аккаунт Altyn отключён.", 403)

    if not PlatonusConnection.objects.filter(user=user).exists():
        raise SyncError(
            "Подключение Platonus отсутствует.",
            409,
        )

    profile, _ = StudentProfile.objects.get_or_create(
        user=user,
    )

    with transaction.atomic():
        profile = (
            StudentProfile.objects
            .select_for_update()
            .get(pk=profile.pk)
        )

        now = timezone.now()
        attempted = profile.last_sync_attempt_at

        # Не создаём дубликат действующей задачи.
        # Зависшую попытку можно заменить через 10 минут.
        if (
            profile.sync_status in {"queued", "syncing"}
            and attempted
            and attempted > now - timedelta(minutes=10)
        ):
            return profile

        # При обычном входе уже загруженный профиль оставляем.
        if not force and profile.last_synced_at is not None:
            return profile

        # Частые повторные входы после ошибки не создают
        # постоянные запросы в Platonus.
        if (
            not force
            and profile.sync_status == "error"
            and attempted
            and attempted > now - timedelta(minutes=1)
        ):
            return profile

        profile.sync_status = "queued"
        profile.sync_message = ""
        profile.last_sync_attempt_at = now

        profile.save(update_fields=[
            "sync_status",
            "sync_message",
            "last_sync_attempt_at",
        ])

        profile_id = profile.pk
        user_id = user.pk

        def publish():
            from accounts.tasks import sync_profile_task

            try:
                sync_profile_task.apply_async(
                    args=[user_id, now.isoformat()],
                    queue="default",
                    expires=300,
                    retry=False,
                )
            except Exception:
                # Не перезаписываем состояние, если worker
                # уже успел начать выполнение задачи.
                StudentProfile.objects.filter(
                    pk=profile_id,
                    sync_status="queued",
                    last_sync_attempt_at=now,
                ).update(
                    sync_status="error",
                    sync_message=(
                        "Не удалось поставить обновление "
                        "в очередь. Попробуйте позже."
                    ),
                )

                logger.error(
                    "Не удалось отправить задачу профиля user_id=%s",
                    user_id,
                )

        transaction.on_commit(publish)

    profile.refresh_from_db()
    return profile