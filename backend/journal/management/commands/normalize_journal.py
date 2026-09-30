import re

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from journal.models import JournalSnapshot
from journal.services.normalization import (
    JournalImportError,
    normalize_journal,
)


class Command(BaseCommand):
    help = (
        "Разбирает сохранённый JSON журнала "
        "в связанные таблицы."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--term",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Проверить данные без записи в БД.",
        )

    def handle(self, *args, **options):
        iin = input("ИИН пользователя Altyn: ").strip()

        if not re.fullmatch(r"[0-9]{12}", iin):
            raise CommandError(
                "ИИН должен содержать 12 цифр."
            )

        try:
            snapshot_id = (
                JournalSnapshot.objects
                .values_list("pk", flat=True)
                .get(
                    user__iin=iin,
                    year=options["year"],
                    term=options["term"],
                )
            )

            counts = normalize_journal(
                snapshot_id,
                dry_run=options["dry_run"],
            )

        except JournalSnapshot.DoesNotExist:
            raise CommandError(
                "Сохранённый журнал этого пользователя "
                "за период не найден."
            ) from None

        except JournalImportError as exc:
            raise CommandError(str(exc)) from None

        except DatabaseError:
            raise CommandError(
                "Не удалось выполнить операцию с БД. "
                "Изменения этого запуска отменены. "
                "Проверьте миграции; если БД занята, "
                "повторите позже."
            ) from None

        if options["dry_run"]:
            title = (
                "Проверка пройдена. "
                "Записи в БД не изменены."
            )
        else:
            title = "Разбор журнала завершён."

        self.stdout.write(
            self.style.SUCCESS(title)
        )

        self.stdout.write(
            f"Дисциплин: {counts['subjects']}"
        )
        self.stdout.write(
            f"Строк занятий: {counts['rows']}"
        )
        self.stdout.write(
            f"Значений строк: {counts['row_values']}"
        )
        self.stdout.write(
            f"Общих показателей: {counts['subject_values']}"
        )