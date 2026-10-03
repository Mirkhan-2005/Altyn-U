import logging
from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from accounts.models import PlatonusConnection, StudentProfile
from journal.models import JournalImportState


logger = logging.getLogger(__name__)


def queue_journal_import(user):
    if not user.is_active:
        return

    if not PlatonusConnection.objects.filter(user=user).exists():
        return

    # Сначала должен завершиться первоначальный импорт профиля.
    profile_ready = (
        StudentProfile.objects
        .filter(
            user=user,
            last_synced_at__isnull=False,
        )
        .exclude(sync_status__in=["queued", "syncing"])
        .exists()
    )

    if not profile_ready:
        return

    state, _ = JournalImportState.objects.get_or_create(
        user=user,
    )

    with transaction.atomic():
        state = (
            JournalImportState.objects
            .select_for_update()
            .get(pk=state.pk)
        )

        now = timezone.now()

        if state.attempted_at:
            # Не запускаем второй импорт одновременно с первым.
            # Зависшую попытку можно заменить при следующем
            # входе спустя 30 минут.
            if (
                state.status in {"queued", "running"}
                and state.attempted_at
                > now - timedelta(minutes=30)
            ):
                return

            # После завершения или ошибки — пауза 15 минут.
            last_activity = (
                state.finished_at or state.attempted_at
            )

            if (
                state.status not in {"queued", "running"}
                and last_activity
                > now - timedelta(minutes=15)
            ):
                return

        token = uuid4()

        state.token = token
        state.status = "queued"
        state.attempted_at = now
        state.finished_at = None
        state.report = {}
        state.message = ""

        state.save(
            update_fields=[
                "token",
                "status",
                "attempted_at",
                "finished_at",
                "report",
                "message",
            ],
        )

        user_id = user.pk

        def publish():
            try:
                from journal.tasks import import_journals_task

                import_journals_task.apply_async(
                    args=[user_id, str(token)],
                    queue="default",
                    expires=300,
                    retry=False,
                )
            except Exception:
                JournalImportState.objects.filter(
                    user_id=user_id,
                    token=token,
                    status="queued",
                ).update(
                    status="error",
                    finished_at=timezone.now(),
                    message=(
                        "Не удалось отправить импорт в очередь."
                    ),
                )

                logger.error(
                    "Не удалось поставить импорт журналов "
                    "user_id=%s",
                    user_id,
                )

        transaction.on_commit(publish)