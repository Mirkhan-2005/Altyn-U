import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile
from journal.models import JournalImportState, JournalSnapshot
from journal.services.client import JournalSyncError
from journal.services.history import discover_periods
from journal.services.sync import sync_journal


logger = logging.getLogger(__name__)


@shared_task(
    name="journal.import_journals",
    ignore_result=True,
    soft_time_limit=900,
    time_limit=960,
)
def import_journals_task(user_id, token, current_only=False):
    owned = JournalImportState.objects.filter(
        user_id=user_id,
        token=token,
    )

    # Просроченную или повторно доставленную задачу
    # не запускаем.
    claimed = owned.filter(
        status="queued",
        attempted_at__gt=(
            timezone.now() - timedelta(minutes=5)
        ),
    ).update(status="running")

    if claimed != 1:
        return

    report = {
        "current_only": current_only,
        "total": 0,
        "saved": 0,
        "skipped": 0,
        "errors": [],
        "warnings": [],
    }

    try:
        User = get_user_model()

        user = User.objects.filter(
            pk=user_id,
            is_active=True,
        ).first()

        if user is None:
            raise JournalSyncError(
                "Аккаунт недоступен.",
                403,
            )

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
            raise JournalSyncError(
                "Сначала нужно загрузить профиль.",
                409,
            )

        current = (
            settings.ALTYN_CURRENT_YEAR,
            settings.ALTYN_CURRENT_TERM,
        )

        if not (
            2000 <= current[0] <= 2100
            and current[1] != 0
            and abs(current[1]) <= 20
        ):
            raise JournalSyncError(
                "Проверьте настройку текущего периода.",
                500,
            )

        if current_only:
            periods = [
                {
                    "year": current[0],
                    "term": current[1],
                },
            ]
            warnings = []
        else:
            periods, warnings = discover_periods(user)

        report["total"] = len(periods)
        report["warnings"] = warnings

        # Текущий период — первым.
        # Остальные сохраняют порядок из списка Platonus.
        periods.sort(
            key=lambda item: (
                (item["year"], item["term"]) != current
            ),
        )

        available = {
            (period["year"], period["term"])
            for period in periods
        }

        if current not in available:
            report["warnings"].append(
                "Настроенный текущий период отсутствует "
                "в списке Platonus."
            )

        owned.update(report=report)

        for period in periods:
            # Старая попытка не продолжает работу,
            # если ей на смену уже запущена другая.
            if not owned.filter(status="running").exists():
                return

            user.refresh_from_db(fields=["is_active"])

            if not user.is_active:
                raise JournalSyncError(
                    "Аккаунт отключён.",
                    403,
                )

            year = period["year"]
            term = period["term"]

            snapshot = JournalSnapshot.objects.filter(
                user=user,
                year=year,
                term=term,
            ).first()

            cached = (
                snapshot is not None
                and snapshot.last_synced_at is not None
            )

            current_period = (year, term) == current

            fresh = cached and (
                snapshot.last_synced_at
                > timezone.now() - timedelta(minutes=15)
            )

            # Сохранённые прошлые периоды пропускаем.
            # Текущий пропускаем, если обновлялся недавно.
            if cached and (not current_period or fresh):
                report["skipped"] += 1
                owned.update(report=report)
                continue

            try:
                snapshot = sync_journal(
                    user,
                    year,
                    term,
                )
            except JournalSyncError as exc:
                report["errors"].append(
                    {
                        "year": year,
                        "term": term,
                        "message": str(exc),
                    }
                )

                owned.update(report=report)

                # Ошибка разбора одного периода
                # не мешает загрузить другие.
                #
                # При сбое доступа, сети или ограничении
                # запросов прекращаем этот импорт.
                if exc.status_code != 502:
                    raise
            else:
                report["saved"] += 1

                if snapshot.sync_message:
                    report["warnings"].append(
                        snapshot.sync_message
                    )

                owned.update(report=report)

        report["warnings"] = list(
            dict.fromkeys(report["warnings"])
        )

        state_status = (
            "partial" if report["errors"] else "done"
        )

        owned.update(
            status=state_status,
            finished_at=timezone.now(),
            report=report,
            message=(
                "Некоторые периоды не загружены."
                if report["errors"]
                else ""
            ),
        )

        logger.info(
            "Импорт журналов user_id=%s: "
            "сохранено=%s, пропущено=%s, ошибок=%s",
            user_id,
            report["saved"],
            report["skipped"],
            len(report["errors"]),
        )

    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, JournalSyncError)
            else (
                "Импорт прерван. "
                "Сохранённые журналы остались в БД."
            )
        )

        owned.update(
            status="error",
            finished_at=timezone.now(),
            report=report,
            message=message,
        )

        logger.warning(
            "Импорт журналов остановлен "
            "user_id=%s, тип=%s",
            user_id,
            type(exc).__name__,
        )