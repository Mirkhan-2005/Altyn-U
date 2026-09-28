from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from journal.models import JournalSnapshot
from journal.services.client import JournalSyncError
from journal.services.sync import sync_journal


class Command(BaseCommand):
    help = "Обновить журнал или прочитать его из БД"

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
            "--cached",
            action="store_true",
        )

    def handle(self, *args, **options):
        iin = input("ИИН пользователя Altyn: ").strip()

        user = get_user_model().objects.filter(
            iin=iin,
        ).first()

        if user is None:
            raise CommandError(
                "Пользователь Altyn не найден."
            )

        year = options["year"]
        term = options["term"]

        if options["cached"]:
            journal = JournalSnapshot.objects.filter(
                user=user,
                year=year,
                term=term,
            ).first()

            if journal is None:
                raise CommandError(
                    "Журнал ещё не сохранён."
                )

        else:
            self.stdout.write(
                "Получаем журнал из Platonus…"
            )

            try:
                journal = sync_journal(
                    user,
                    year,
                    term,
                )
            except JournalSyncError as exc:
                raise CommandError(str(exc)) from None

        self.stdout.write(
            f"Статус: {journal.sync_status}"
        )
        self.stdout.write(
            f"Дисциплин: {journal.data.get('subjects_count', 0)}"
        )
        self.stdout.write(
            f"Строк занятий: {journal.data.get('rows_count', 0)}"
        )
        self.stdout.write(
            f"Сохранено: {journal.last_synced_at}"
        )

        if journal.sync_message:
            self.stdout.write(journal.sync_message)