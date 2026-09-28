from datetime import timedelta
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from ..models import JournalSnapshot
from .client import JournalSyncError, download_journal


def sync_journal(user, year, term):
    if not user.is_active:
        raise JournalSyncError(
            "Аккаунт Altyn отключён.",
            403,
        )

    if (
        type(year) is not int
        or not 2000 <= year <= 2100
        or type(term) is not int
        or term == 0
        or abs(term) > 20
    ):
        raise JournalSyncError(
            "Некорректный год или период.",
            400,
        )

    journal, _ = JournalSnapshot.objects.get_or_create(
        user=user,
        year=year,
        term=term,
    )

    now = timezone.now()
    token = uuid4()

    # Не запускаем повторное обновление того же журнала.
    # После зависшего процесса разрешаем новую попытку через 5 минут.
    claimed = JournalSnapshot.objects.filter(
        pk=journal.pk,
    ).filter(
        Q(sync_token__isnull=True)
        | Q(
            last_sync_attempt_at__lt=now - timedelta(minutes=5)
        )
    ).update(
        sync_token=token,
        last_sync_attempt_at=now,
        sync_status="syncing",
        sync_message="",
    )

    if claimed != 1:
        raise JournalSyncError(
            "Этот журнал уже обновляется. Подождите.",
            409,
        )

    owned = JournalSnapshot.objects.filter(
        pk=journal.pk,
        sync_token=token,
    )

    try:
        data, warning = download_journal(
            user,
            year,
            term,
        )

        saved = owned.update(
            data=data,
            last_synced_at=timezone.now(),
            sync_status="partial" if warning else "synced",
            sync_message=warning,
            sync_token=None,
        )

        if saved != 1:
            raise JournalSyncError(
                "Началось другое обновление. Перечитайте журнал.",
                409,
            )

    except Exception as exc:
        error = (
            exc
            if isinstance(exc, JournalSyncError)
            else JournalSyncError(
                "Не удалось обновить журнал. Повторите позже."
            )
        )

        # Старые data и last_synced_at не изменяем.
        owned.update(
            sync_status="error",
            sync_message=str(error),
            sync_token=None,
        )

        raise error from None

    journal.refresh_from_db()

    return journal