import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from django.db import transaction
from django.db.models import F

from journal.models import (
    JournalSnapshot,
    JournalSubject,
    JournalLessonRow,
    JournalRowValue,
    JournalSubjectValue,
)


class JournalImportError(ValueError):
    pass


ROW_COLUMNS = {
    str(week) for week in range(1, 16)
} | {"ТК1", "ТК2"}

SUBJECT_COLUMNS = {
    "ТК1 ОБЩ.",
    "РК1",
    "Р1",
    "ТК2 ОБЩ.",
    "РК2",
    "Р2",
    "Оценка за курсовую работу",
    "Практика",
    "Исследоват. работа",
    "Рейтинг допуска",
    "Итоговый контроль",
    "Итоговая оценка / %",
    "Итоговая оценка / Буквенная",
}

LETTER_COLUMN = "Итоговая оценка / Буквенная"

NUMBER_PATTERN = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


def parse_value(column, position, raw):
    """Сохраняет исходное значение и определяет его тип."""
    if raw is not None and not isinstance(raw, str):
        raise JournalImportError(
            f"Колонка «{column}»: ожидалась строка или null."
        )

    text = raw.strip() if raw is not None else ""
    marker = re.sub(r"\s+", "", text.lower())
    number = None

    if not text:
        kind = "empty"

    elif marker in {"н", "н.п."}:
        # Обозначения сохраняем отдельно от числового нуля.
        kind = "marker"

    elif column == LETTER_COLUMN:
        kind = "text"

    elif NUMBER_PATTERN.fullmatch(text):
        number = Decimal(text)

        if not Decimal("0") <= number <= Decimal("100"):
            raise JournalImportError(
                f"Колонка «{column}»: число вне диапазона 0–100."
            )

        try:
            DecimalValidator(12, 6)(number)
        except ValidationError:
            raise JournalImportError(
                f"Колонка «{column}»: число не помещается "
                "в поле без округления."
            ) from None

        kind = "number"

    else:
        # Неизвестное обозначение сохраняем без изменений.
        # Это не числовая оценка и не ноль.
        kind = "text"

    
    

    return {
        "source_column": column,
        "column_position": position,
        "raw_value": raw,
        "value_kind": kind,
        "numeric_value": number,
    }


def value_signature(value):
    """Сравнивает смысл значений: например, 70 и 70.00 равны."""
    kind = value["value_kind"]

    if kind == "number":
        return kind, value["numeric_value"]

    if kind == "empty":
        return kind, None

    text = value["raw_value"].strip()

    if kind == "marker":
        text = re.sub(r"\s+", "", text.lower())

    return kind, text


def build_plan(snapshot):
    """Проверяет весь JSON до изменения записей в БД."""
    data = snapshot.data

    if not isinstance(data, dict):
        raise JournalImportError(
            "Журнал должен быть объектом JSON."
        )

    if (
        type(data.get("year")) is not int
        or type(data.get("term")) is not int
        or data["year"] != snapshot.year
        or data["term"] != snapshot.term
    ):
        raise JournalImportError(
            "Год или период JSON не соответствует записи журнала."
        )

    columns = data.get("columns")

    if (
        not isinstance(columns, list)
        or not all(isinstance(c, str) for c in columns)
        or len(columns) <= 3
        or len(columns) != len(set(columns))
        or columns[:3] != [
            "Дисциплина",
            "Учебный поток",
            "Преподаватель",
        ]
    ):
        raise JournalImportError(
            "Неожиданная структура колонок журнала."
        )

    unknown_columns = (
        set(columns[3:]) - ROW_COLUMNS - SUBJECT_COLUMNS
    )

    if unknown_columns:
        raise JournalImportError(
            "В журнале есть новые колонки. "
            "Нужно расширить импортёр."
        )

    subjects = data.get("subjects")

    if not isinstance(subjects, list) or not subjects:
        raise JournalImportError(
            "В журнале нет дисциплин для разбора."
        )

    plan = []

    counts = {
        "subjects": 0,
        "rows": 0,
        "row_values": 0,
        "subject_values": 0,
    }

    for subject_index, subject in enumerate(subjects):
        if not isinstance(subject, dict):
            raise JournalImportError(
                "Неожиданный формат дисциплины."
            )

        name = subject.get("name")
        rows = subject.get("rows")

        if not isinstance(name, str) or not name.strip():
            raise JournalImportError(
                "У дисциплины отсутствует название."
            )

        if not isinstance(rows, list) or not rows:
            raise JournalImportError(
                f"Дисциплина №{subject_index + 1}: "
                "нет строк занятий."
            )

        prepared_rows = []
        common_values = {}

        for row_index, row in enumerate(rows):
            if (
                not isinstance(row, dict)
                or set(row) != set(columns[1:])
            ):
                raise JournalImportError(
                    "Набор полей строки не совпадает с колонками."
                )

            if not all(
                isinstance(row[column], str)
                for column in columns[1:3]
            ):
                raise JournalImportError(
                    "Поток и подпись преподавателя "
                    "должны быть строками."
                )

            values = []

            for column_position, column in enumerate(
                columns[3:],
                start=3,
            ):
                value = parse_value(
                    column,
                    column_position,
                    row[column],
                )

                if column in ROW_COLUMNS:
                    values.append(value)

                elif row_index == 0:
                    common_values[column] = value

                elif (
                    value_signature(common_values[column])
                    != value_signature(value)
                ):
                    raise JournalImportError(
                        f"Дисциплина №{subject_index + 1}, "
                        f"колонка «{column}»: "
                        "общие значения различаются между строками."
                    )

            prepared_rows.append(
                {
                    "position": row_index,
                    "stream_label": row["Учебный поток"],
                    "teacher_label": row["Преподаватель"],
                    "values": values,
                }
            )

            counts["rows"] += 1
            counts["row_values"] += len(values)

        plan.append(
            {
                "position": subject_index,
                "source_name": name,
                "rows": prepared_rows,
                "values": list(common_values.values()),
            }
        )

        counts["subjects"] += 1
        counts["subject_values"] += len(common_values)

    for source_key, count_key in [
        ("subjects_count", "subjects"),
        ("rows_count", "rows"),
    ]:
        if (
            type(data.get(source_key)) is not int
            or data[source_key] != counts[count_key]
        ):
            raise JournalImportError(
                f"Поле {source_key} не соответствует "
                "содержимому JSON."
            )

    return plan, counts


@transaction.atomic
def normalize_journal(snapshot_id, *, dry_run=False):
    if not dry_run:
        # Получаем блокировку записи до чтения,
        # в том числе при использовании SQLite.
        # Значение sync_status остаётся прежним.
        JournalSnapshot.objects.filter(
            pk=snapshot_id,
        ).update(
            sync_status=F("sync_status"),
        )

    snapshot = (
        JournalSnapshot.objects
        .select_for_update()
        .get(pk=snapshot_id)
    )

    if snapshot.sync_token is not None:
        raise JournalImportError(
            "Журнал занят синхронизацией. "
            "Повторите после её завершения."
        )

    if snapshot.last_synced_at is None:
        raise JournalImportError(
            "У журнала ещё не было успешной загрузки."
        )

    plan, counts = build_plan(snapshot)

    if dry_run:
        return counts

    # Пересоздаём только производные записи выбранного журнала.
    # Сам JournalSnapshot и его исходный JSON не удаляются.
    JournalSubject.objects.filter(
        snapshot=snapshot,
    ).delete()

    for item in plan:
        subject = JournalSubject.objects.create(
            snapshot=snapshot,
            position=item["position"],
            source_name=item["source_name"],
        )

        JournalSubjectValue.objects.bulk_create(
            [
                JournalSubjectValue(
                    subject=subject,
                    **value,
                )
                for value in item["values"]
            ]
        )

        for row in item["rows"]:
            lesson = JournalLessonRow.objects.create(
                subject=subject,
                position=row["position"],
                stream_label=row["stream_label"],
                teacher_label=row["teacher_label"],
            )

            JournalRowValue.objects.bulk_create(
                [
                    JournalRowValue(
                        lesson_row=lesson,
                        **value,
                    )
                    for value in row["values"]
                ]
            )

    return counts