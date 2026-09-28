import re

from bs4 import BeautifulSoup


class JournalError(Exception):
    pass


def expand_rows(rows):
    """Разворачивает rowspan/colspan без сдвига колонок."""
    if not rows or len(rows) > 2000:
        raise JournalError("Неожиданное количество строк таблицы.")

    grid = [{} for _ in rows]

    for r, row in enumerate(rows):
        c = 0

        for cell in row.find_all(["td", "th"], recursive=False):
            while c in grid[r]:
                c += 1

            try:
                height = int(cell.get("rowspan", 1))
                width = int(cell.get("colspan", 1))
            except (TypeError, ValueError):
                raise JournalError(
                    "Некорректные размеры объединённой ячейки."
                )

            if not (
                1 <= height <= len(rows) - r
                and 1 <= width <= 80 - c
            ):
                raise JournalError(
                    "Размеры таблицы не поддерживаются."
                )

            value = " ".join(
                cell.get_text(" ", strip=True).split()
            )

            for rr in range(r, r + height):
                for cc in range(c, c + width):
                    if cc in grid[rr]:
                        raise JournalError(
                            "Объединённые ячейки пересекаются."
                        )

                    grid[rr][cc] = value

            c += width

    width = max(len(row) for row in grid)

    if not width or any(
        set(row) != set(range(width))
        for row in grid
    ):
        raise JournalError(
            "В таблице пропущены ячейки. Разбор остановлен."
        )

    return [
        [row[c] for c in range(width)]
        for row in grid
    ]


def parse_journal(
    html,
    year,
    term,
    expected_student_id=None,
):
    soup = BeautifulSoup(html, "html.parser")

    form = soup.find(
        "form",
        action="current_progress_gradebook_student",
    )

    if form is None:
        raise JournalError(
            "Форма журнала не найдена. "
            "Возможно, получена страница входа."
        )

    owner = form.find(
        "input",
        attrs={"name": "studentID"},
    )
    owner_id = owner.get("value", "") if owner else ""

    if not re.fullmatch(r"[0-9]+", owner_id):
        raise JournalError("В журнале не указан ID студента.")

    if (
        expected_student_id is not None
        and int(owner_id) != expected_student_id
    ):
        raise JournalError(
            "Журнал не соответствует владельцу сессии."
        )

    def options(name, expected):
        select = form.find(
            "select",
            attrs={"name": name},
        )

        if select is None:
            raise JournalError(f"Не найден список {name}.")

        selected = select.select("option[selected]")

        if (
            len(selected) != 1
            or selected[0].get("value") != str(expected)
        ):
            raise JournalError(
                f"Получен другой учебный год или период: {name}."
            )

        return [
            {
                "value": option.get("value"),
                "label": option.get_text(" ", strip=True),
            }
            for option in select.find_all("option")
        ]

    years = options("year", year)
    terms = options("term", term)

    tables = [
        table
        for table in soup.find_all("table")
        if table.select_one("thead")
        and table.select_one("tr.subject")
    ]

    if len(tables) != 1:
        raise JournalError(
            "Таблица с дисциплинами не найдена или неоднозначна."
        )

    table = tables[0]

    head = expand_rows(
        table.find("thead").find_all(
            "tr",
            recursive=False,
        )
    )

    # Объединяем двухуровневые заголовки.
    # Например: "Итоговая оценка / %".
    columns = [
        " / ".join(
            dict.fromkeys(
                row[c]
                for row in head
                if row[c]
            )
        )
        for c in range(len(head[0]))
    ]

    if columns[:3] != [
        "Дисциплина",
        "Учебный поток",
        "Преподаватель",
    ]:
        raise JournalError("Заголовки журнала изменились.")

    if len(set(columns)) != len(columns):
        raise JournalError(
            "Найдены повторяющиеся заголовки колонок."
        )

    if not all(
        str(week) in columns
        for week in range(1, 16)
    ):
        raise JournalError(
            "Не найдены все недельные колонки."
        )

    body = table.find("tbody")

    if body is None:
        raise JournalError("Строки журнала не найдены.")

    rows = body.find_all("tr", recursive=False)
    grid = expand_rows(rows)

    if len(grid[0]) != len(columns):
        raise JournalError(
            "Число колонок не совпадает с заголовками."
        )

    subjects = []

    for tag, values in zip(rows, grid):
        classes = tag.get("class", [])

        if "subject" in classes:
            subjects.append({
                "name": values[0],
                "rows": [],
            })
        elif "subject_study_groups" not in classes:
            raise JournalError(
                "Неизвестный тип строки журнала."
            )

        if (
            not subjects
            or values[0] != subjects[-1]["name"]
        ):
            raise JournalError(
                "Нарушена группировка дисциплин."
            )

        subjects[-1]["rows"].append({
            column: value if value != "" else None
            for column, value in zip(
                columns[1:],
                values[1:],
            )
        })

    return {
        "year": year,
        "academic_year": f"{year}–{year + 1}",
        "term": term,
        "available_years": years,
        "available_terms": terms,
        "columns": columns,
        "subjects_count": len(subjects),
        "rows_count": len(grid),
        "subjects": subjects,
    }