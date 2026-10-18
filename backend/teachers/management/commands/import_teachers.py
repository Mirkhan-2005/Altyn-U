from django.core.management.base import BaseCommand
from django.db import transaction

from journal.models import JournalLessonRow, JournalSnapshot
from teachers.models import Teacher
from teachers.services import get_or_create_teacher


class Command(BaseCommand):
    help = (
        "Заполнить справочник преподавателей "
        "из сохранённых строк журналов без обращения к Platonus."
    )

    def handle(self, *args, **options):
        linked = 0
        empty = 0
        skipped = 0

        snapshot_ids = (
            JournalSnapshot.objects
            .order_by("pk")
            .values_list("pk", flat=True)
        )

        for snapshot_id in snapshot_ids.iterator(chunk_size=200):
            with transaction.atomic():
                # Используем ту же запись блокировки,
                # что и нормализация журнала.
                snapshot = (
                    JournalSnapshot.objects
                    .select_for_update()
                    .filter(pk=snapshot_id)
                    .first()
                )

                if snapshot is None:
                    continue

                if snapshot.sync_token is not None:
                    skipped += 1
                    continue

                rows = (
                    JournalLessonRow.objects
                    .filter(
                        subject__snapshot_id=snapshot_id,
                        teacher__isnull=True,
                    )
                    .order_by("pk")
                )

                for row in rows.iterator(chunk_size=200):
                    teacher = get_or_create_teacher(
                        row.teacher_label,
                    )

                    if teacher is None:
                        empty += 1
                        continue

                    row.teacher = teacher
                    row.save(update_fields=["teacher"])
                    linked += 1

        self.stdout.write(
            f"Преподавателей в справочнике: "
            f"{Teacher.objects.count()}"
        )
        self.stdout.write(f"Связано строк занятий: {linked}")
        self.stdout.write(f"Строк без подписи: {empty}")
        self.stdout.write(f"Занятых журналов пропущено: {skipped}")

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Некоторые журналы обновляются. "
                    "Повторите команду после завершения синхронизации."
                )
            )