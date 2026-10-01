import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from journal.services.client import JournalSyncError
from journal.services.history import (
    discover_periods,
    import_history,
)


class Command(BaseCommand):
    help = (
        "Получить список периодов "
        "или загрузить все журналы студента"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--list-only",
            action="store_true",
            help="Показать периоды без сохранения журналов.",
        )

        parser.add_argument(
            "--refresh-existing",
            action="store_true",
            help=(
                "Повторно загрузить "
                "и уже сохранённые периоды."
            ),
        )

    def handle(self, *args, **options):
        iin = input(
            "ИИН пользователя Altyn: "
        ).strip()

        if not re.fullmatch(r"[0-9]{12}", iin):
            raise CommandError(
                "Введите ИИН из 12 цифр."
            )

        user = get_user_model().objects.filter(
            iin=iin,
        ).first()

        if user is None:
            raise CommandError(
                "Пользователь Altyn не найден."
            )

        self.stdout.write(
            "Получаем доступные годы и периоды…"
        )

        try:
            if options["list_only"]:
                periods, warnings = discover_periods(user)

                for period in periods:
                    self.stdout.write(
                        f"{period['label']} "
                        f"(year={period['year']}, "
                        f"term={period['term']})"
                    )

                for warning in warnings:
                    self.stdout.write(
                        self.style.WARNING(warning)
                    )

                self.stdout.write(
                    "Это пункты списка Platonus. "
                    "Наличие оценок в каждом периоде "
                    "ещё не проверено."
                )

                return

            result = import_history(
                user,
                refresh_existing=options["refresh_existing"],
                report=self.stdout.write,
            )

        except JournalSyncError as exc:
            raise CommandError(str(exc)) from None

        self.stdout.write(
            f"Периодов: {result['total']}. "
            f"Сохранено: {result['saved']}. "
            f"Уже были в БД: {result['skipped']}. "
            f"Ошибок: {len(result['errors'])}. "
            f"Не проверено: {result['not_attempted']}."
        )

        for warning in result["warnings"]:
            self.stdout.write(
                self.style.WARNING(warning)
            )

        if result["errors"] or result["not_attempted"]:
            raise CommandError(
                "Импорт завершён не полностью. "
                "Успешно сохранённые журналы остались в БД. "
                "Повторный запуск продолжит загрузку недостающих."
            )