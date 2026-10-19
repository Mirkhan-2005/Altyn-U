from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q

from journal.models import (
    JournalPeriodCompletion,
    JournalRowValue,
)


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

    periods = (
        JournalPeriodCompletion.objects
        .filter(
            Q(tk1_completed=True)
            | Q(tk2_completed=True)
        )
        .values_list(
            "year",
            "term",
            "tk1_completed",
            "tk2_completed",
        )
    )

    # Пока не найден закрытый ТК, выборка остаётся пустой.
    eligible = Q(pk__in=[])

    for year, term, first, second in periods:
        columns = []

        if first:
            columns.append("ТК1")

        if second:
            columns.append("ТК2")

        eligible |= Q(
            lesson_row__subject__snapshot__year=year,
            lesson_row__subject__snapshot__term=term,
            source_column__in=columns,
        )

    values = (
        JournalRowValue.objects
        .filter(
            eligible,
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

    # 1. Собираем завершённые ТК каждой строки занятий.
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