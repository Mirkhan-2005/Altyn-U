from django.conf import settings
from django.db import models


class JournalSnapshot(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journals",
    )
    year = models.PositiveSmallIntegerField()
    term = models.SmallIntegerField()

    data = models.JSONField(default=dict, blank=True)

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_sync_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    sync_status = models.CharField(
        max_length=16,
        default="pending",
    )
    sync_message = models.TextField(blank=True)

    # Защищает от одновременной записи нескольких обновлений.
    sync_token = models.UUIDField(
        null=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "year", "term"],
                name="unique_journal_user_period",
            ),
        ]
        ordering = ["-year", "term"]

class JournalSubject(models.Model):
    snapshot = models.ForeignKey(
        JournalSnapshot,
        on_delete=models.CASCADE,
        related_name="subjects",
        verbose_name="Журнал",
    )

    # Позиция внутри исходного JSON, начиная с 0.
    # Это не идентификатор дисциплины в Platonus.
    position = models.PositiveIntegerField(
        verbose_name="Порядок в журнале",
    )

    source_name = models.TextField(
        verbose_name="Название из Platonus",
    )

    class Meta:
        verbose_name = "Дисциплина студента"
        verbose_name_plural = "Дисциплины студентов"

        ordering = ["snapshot_id", "position"]

        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "position"],
                name="unique_subject_snapshot_position",
            ),
        ]

    def __str__(self):
        return self.source_name


class JournalLessonRow(models.Model):
    subject = models.ForeignKey(
        JournalSubject,
        on_delete=models.CASCADE,
        related_name="lesson_rows",
        verbose_name="Дисциплина студента",
    )

    position = models.PositiveIntegerField(
        verbose_name="Порядок строки",
    )

    stream_label = models.TextField(
        verbose_name="Учебный поток из Platonus",
        blank=True,
    )

    teacher_label = models.TextField(
        verbose_name="Подпись преподавателя из Platonus",
        blank=True,
    )

    class Meta:
        verbose_name = "Строка занятий"
        verbose_name_plural = "Строки занятий"

        ordering = ["subject_id", "position"]

        constraints = [
            models.UniqueConstraint(
                fields=["subject", "position"],
                name="unique_lesson_subject_position",
            ),
        ]

    def __str__(self):
        return (
            f"{self.subject.source_name} — "
            f"{self.stream_label or 'Поток не указан'}"
        )


class JournalValueBase(models.Model):
    class ValueKind(models.TextChoices):
        NUMBER = "number", "Число"
        EMPTY = "empty", "Пусто"
        MARKER = "marker", "Обозначение"
        TEXT = "text", "Текст"

    # Пока используем точное название колонки из источника:
    # "1", "ТК1", "РК1", "Итоговая оценка / %" и т. д.
    source_column = models.CharField(
        verbose_name="Колонка из Platonus",
        max_length=255,
    )

    column_position = models.PositiveIntegerField(
        verbose_name="Порядок колонки",
    )

    # Сохраняем исходное представление:
    # None, "", "0", "70.00", "н", "н.п.", "C+".
    raw_value = models.TextField(
        verbose_name="Исходное значение",
        null=True,
        blank=True,
    )

    value_kind = models.CharField(
        verbose_name="Тип значения",
        max_length=16,
        choices=ValueKind.choices,
    )

    # Заполняется только для числовых значений.
    # Исходная точность и запись остаются в raw_value.
    numeric_value = models.DecimalField(
        verbose_name="Числовое значение",
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        display_value = (
            self.raw_value
            if self.raw_value not in (None, "")
            else "пусто"
        )

        return f"{self.source_column}: {display_value}"


class JournalRowValue(JournalValueBase):
    lesson_row = models.ForeignKey(
        JournalLessonRow,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name="Строка занятий",
    )

    class Meta:
        verbose_name = "Значение строки занятий"
        verbose_name_plural = "Значения строк занятий"

        ordering = ["lesson_row_id", "column_position"]

        constraints = [
            models.UniqueConstraint(
                fields=["lesson_row", "source_column"],
                name="unique_row_value_column",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        value_kind="number",
                        numeric_value__isnull=False,
                    )
                    | models.Q(
                        value_kind__in=["empty", "marker", "text"],
                        numeric_value__isnull=True,
                    )
                ),
                name="valid_row_value_kind_number",
            ),
        ]


class JournalSubjectValue(JournalValueBase):
    subject = models.ForeignKey(
        JournalSubject,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name="Дисциплина студента",
    )

    class Meta:
        verbose_name = "Общий показатель дисциплины"
        verbose_name_plural = "Общие показатели дисциплин"

        ordering = ["subject_id", "column_position"]

        constraints = [
            models.UniqueConstraint(
                fields=["subject", "source_column"],
                name="unique_subject_value_column",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        value_kind="number",
                        numeric_value__isnull=False,
                    )
                    | models.Q(
                        value_kind__in=["empty", "marker", "text"],
                        numeric_value__isnull=True,
                    )
                ),
                name="valid_subject_value_kind_number",
            ),
        ]