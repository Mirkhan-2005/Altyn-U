from datetime import timedelta
from uuid import uuid4

from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone

from ..models import JournalSnapshot
from .client import JournalSyncError, download_journal
from .normalization import JournalImportError, normalize_journal


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

    token = uuid4()

    try:
        journal, _ = JournalSnapshot.objects.get_or_create(
            user=user,
            year=year,
            term=term,
        )

        now = timezone.now()

        # Разрешаем новую попытку, если журнал свободен
        # или предыдущая попытка зависла больше 5 минут назад.
        claimed = (
            JournalSnapshot.objects
            .filter(pk=journal.pk)
            .filter(
                Q(sync_token__isnull=True)
                | Q(
                    last_sync_attempt_at__lt=(
                        now - timedelta(minutes=5)
                    )
                )
            )
            .update(
                sync_token=token,
                last_sync_attempt_at=now,
                sync_status="syncing",
                sync_message="",
            )
        )

    except DatabaseError:
        raise JournalSyncError(
            "Не удалось начать обновление журнала. "
            "База данных недоступна или занята.",
            503,
        ) from None

    if claimed != 1:
        raise JournalSyncError(
            "Этот журнал уже обновляется. Подождите.",
            409,
        )

    # Изменять состояние может только владелец этого token.
    owned = JournalSnapshot.objects.filter(
        pk=journal.pk,
        sync_token=token,
    )

    try:
        # Сетевой запрос выполняется до транзакции сохранения.
        data, warning = download_journal(
            user,
            year,
            term,
        )

        warning = warning or ""

        with transaction.atomic():
            # Проверяем, что попытка всё ещё владеет журналом.
            # UPDATE также удерживает блокировку записи
            # до завершения транзакции.
            saved = owned.update(
                data=data,
                last_synced_at=timezone.now(),
                sync_status="partial" if warning else "synced",
                sync_message=warning,
                sync_token=None,
            )

            if saved != 1:
                raise JournalSyncError(
                    "Началось другое обновление. "
                    "Перечитайте журнал.",
                    409,
                )

            # Функция читает новый JSON из той же транзакции
            # и перестраивает связанные записи.
            #
            # sync_token уже None внутри нашей транзакции,
            # поэтому normalize_journal допускает разбор.
            # Для других запросов освобождение журнала
            # вступит в силу после успешного commit.
            normalize_journal(journal.pk)

            # Получаем именно сохранённую этой попыткой версию,
            # пока блокировка записи ещё удерживается.
            journal.refresh_from_db()

    except Exception as exc:
        # Сюда попадаем уже после отката транзакции,
        # если ошибка возникла во время сохранения.
        if isinstance(exc, JournalSyncError):
            error = exc

        elif isinstance(exc, JournalImportError):
            error = JournalSyncError(
                "Полученный журнал не прошёл проверку. "
                f"{exc} "
                "Сохранённые ранее оценки не изменены.",
                502,
            )

        elif isinstance(exc, DatabaseError):
            error = JournalSyncError(
                "Не удалось сохранить журнал в БД. "
                "Повторите позже.",
                503,
            )

        else:
            error = JournalSyncError(
                "Не удалось обновить журнал. Повторите позже."
            )

        try:
            # JSON и last_synced_at здесь не меняем.
            # Если token уже принадлежит другой попытке,
            # запрос ничего не изменит.
            owned.update(
                sync_status="error",
                sync_message=str(error),
                sync_token=None,
            )

        except DatabaseError:
            # При недоступной БД освободить token не удалось.
            # Новую попытку разрешит существующий тайм-аут.
            raise JournalSyncError(
                "База данных недоступна или занята. "
                "Не удалось завершить обновление. "
                "Повторите попытку позже; блокировка "
                "может сохраняться до 5 минут.",
                503,
            ) from None

        raise error from None

    return journal