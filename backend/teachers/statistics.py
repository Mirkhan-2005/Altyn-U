from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

from journal.models import JournalRowValue


def empty_statistics():
    return {
        "average_score": None,
        "students_count": 0,
        "observations_count": 0,
    }


def _mean(values):
    return sum(values, Decimal("0")) / len(values)


def get_teacher_grade_statistics(teacher_ids):
    result = {
        teacher_id: empty_statistics()
        for teacher_id in teacher_ids
    }

    if not result:
        return result

    current_year = settings.ALTYN_CURRENT_YEAR
    current_term = settings.ALTYN_CURRENT_TERM

    if (
        type(current_year) is not int
        or not 2000 <= current_year <= 2100
        or type(current_term) is not int
        or current_term not in (1, 2)
    ):
        raise ImproperlyConfigured(
            "Для автоматической статистики задайте "
            "ALTYN_CURRENT_YEAR от 2000 до 2100 "
            "и ALTYN_CURRENT_TERM равным 1 или 2."
        )

    # Только обычные периоды, предшествующие текущему.
    eligible = (
        Q(lesson_row__subject__snapshot__year__lt=current_year)
        | Q(
            lesson_row__subject__snapshot__year=current_year,
            lesson_row__subject__snapshot__term__lt=current_term,
        )
    )

    values = (
        JournalRowValue.objects
        .filter(
            eligible,
            lesson_row__subject__snapshot__year__gte=2000,
            lesson_row__subject__snapshot__term__in=(1, 2),
            source_column__in=("ТК1", "ТК2"),
            lesson_row__teacher_id__in=result,
            lesson_row__subject__snapshot__last_synced_at__isnull=False,
            lesson_row__subject__snapshot__user__is_active=True,
            value_kind="number",
            numeric_value__gte=0,
            numeric_value__lte=100,
        )
        .order_by()
        .values_list(
            "lesson_row__teacher_id",
            "lesson_row__subject__snapshot__user_id",
            "lesson_row__subject__snapshot__year",
            "lesson_row__subject__snapshot__term",
            "lesson_row__subject__source_name",
            "lesson_row_id",
            "numeric_value",
        )
    )

    # 1. Усредняем доступные ТК строки за прошлый период.
    rows = defaultdict(list)

    for teacher, student, year, term, subject, row, value in values.iterator():
        key = (
            teacher,
            student,
            year,
            term,
            subject.strip(),
            row,
        )

        rows[key].append(value)

    # 2. Объединяем строки одного предмета и периода.
    observations = defaultdict(list)

    for key, grades in rows.items():
        observations[key[:-1]].append(_mean(grades))

    # 3. Объединяем предметы и периоды каждого студента.
    students = defaultdict(list)

    for (teacher, student, year, term, subject), grades in observations.items():
        students[(teacher, student)].append(_mean(grades))
        result[teacher]["observations_count"] += 1

    # 4. Каждый студент имеет одинаковый вес.
    teachers = defaultdict(list)

    for (teacher, student), grades in students.items():
        teachers[teacher].append(_mean(grades))

    for teacher, grades in teachers.items():
        result[teacher] = {
            "average_score": str(
                _mean(grades).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            ),
            "students_count": len(grades),
            "observations_count": result[teacher]["observations_count"],
        }

    return result