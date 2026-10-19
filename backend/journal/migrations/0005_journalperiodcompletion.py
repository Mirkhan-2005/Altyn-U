import django.core.validators

from django.db import migrations, models


def seed_existing_periods(apps, schema_editor):
    Snapshot = apps.get_model("journal", "JournalSnapshot")
    Completion = apps.get_model(
        "journal",
        "JournalPeriodCompletion",
    )

    alias = schema_editor.connection.alias

    periods = (
        Snapshot.objects.using(alias)
        .filter(
            year__gte=2000,
            year__lte=2100,
            term__gte=-20,
            term__lte=20,
        )
        .exclude(term=0)
        .order_by()
        .values_list("year", "term")
        .distinct()
    )

    for year, term in periods.iterator():
        Completion.objects.using(alias).get_or_create(
            year=year,
            term=term,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0004_journallessonrow_teacher"),
    ]

    operations = [
        migrations.CreateModel(
            name="JournalPeriodCompletion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "year",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(2000),
                            django.core.validators.MaxValueValidator(2100),
                        ],
                        verbose_name="Начало учебного года",
                    ),
                ),
                (
                    "term",
                    models.SmallIntegerField(
                        help_text="Код периода Platonus; 0 не допускается.",
                        validators=[
                            django.core.validators.MinValueValidator(-20),
                            django.core.validators.MaxValueValidator(20),
                        ],
                        verbose_name="Академический период",
                    ),
                ),
                (
                    "tk1_completed",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Включить сохранённые ТК1 этого периода "
                            "в средний балл преподавателей."
                        ),
                        verbose_name="ТК1 завершён",
                    ),
                ),
                (
                    "tk2_completed",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Включить сохранённые ТК2 этого периода "
                            "в средний балл преподавателей."
                        ),
                        verbose_name="ТК2 завершён",
                    ),
                ),
            ],
            options={
                "verbose_name": "Завершение ТК по периоду",
                "verbose_name_plural": "Завершение ТК по периодам",
                "ordering": ["-year", "term"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("year", "term"),
                        name="unique_journal_period_completion",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            year__gte=2000,
                            year__lte=2100,
                        ),
                        name="valid_completion_year",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(term__gte=-20, term__lte=20)
                            & ~models.Q(term=0)
                        ),
                        name="valid_completion_term",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            seed_existing_periods,
            migrations.RunPython.noop,
        ),
    ]