import logging
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import PlatonusConnection, StudentProfile
from journal.models import JournalImportState, JournalSnapshot


logger = logging.getLogger(__name__)


def is_current(year, term):
    return (year, term) == (
        settings.ALTYN_CURRENT_YEAR,
        settings.ALTYN_CURRENT_TERM,
    )


def is_fresh(snapshot, now):
    return bool(
        snapshot
        and snapshot.last_synced_at
        and snapshot.last_synced_at > now - timedelta(minutes=15)
    )


def import_active(state, now):
    if not state or not state.attempted_at:
        return False

    minutes = {
        "queued": 5,
        "running": 30,
    }.get(state.status)

    return bool(
        minutes
        and state.attempted_at > now - timedelta(minutes=minutes)
    )


def queue_journal_import(user, *, current_only=False):
    if not user.is_active:
        return

    if not PlatonusConnection.objects.filter(user=user).exists():
        return

    # Профиль должен загрузиться раньше журналов.
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

        # Несколько вкладок используют одну задачу.
        if import_active(state, now):
            return

        if current_only:
            snapshot = JournalSnapshot.objects.filter(
                user=user,
                year=settings.ALTYN_CURRENT_YEAR,
                term=settings.ALTYN_CURRENT_TERM,
            ).first()

            if is_fresh(snapshot, now):
                return

            # Например, пользователь уже обновляет журнал вручную.
            if (
                snapshot
                and snapshot.sync_token
                and snapshot.last_sync_attempt_at
                and snapshot.last_sync_attempt_at
                > now - timedelta(minutes=5)
            ):
                return

            # При ошибке даём Platonus минуту перед новой
            # автоматической попыткой. Ручная кнопка доступна.
            if (
                state.status in {"error", "partial"}
                and state.finished_at
                and state.finished_at
                > now - timedelta(minutes=1)
            ):
                return

        if state.attempted_at and not current_only:
            last_activity = (
                state.finished_at or state.attempted_at
            )

            if (
                state.status not in {"queued", "running"}
                and last_activity > now - timedelta(minutes=15)
            ):
                return

        token = uuid4()

        state.token = token
        state.status = "queued"
        state.attempted_at = now
        state.finished_at = None
        state.report = {"current_only": current_only}
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
                    args=[user_id, str(token), current_only],
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
                    message="Не удалось отправить импорт в очередь.",
                )

                logger.error(
                    "Не удалось поставить импорт журналов user_id=%s",
                    user_id,
                )

        transaction.on_commit(publish)