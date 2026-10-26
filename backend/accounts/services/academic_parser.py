import re

from bs4 import BeautifulSoup


def _text(element):
    return " ".join(element.get_text(" ", strip=True).split())


def extract_middle_name(full_name, first_name, last_name):
    """Извлекает отчество при точном совпадении фамилии и имени."""
    values = (full_name, first_name, last_name)

    if any(
        not isinstance(value, str) or not value.strip()
        for value in values
    ):
        return None

    full_name, first_name, last_name = (
        " ".join(value.split()) for value in values
    )

    prefix = f"{last_name} {first_name} "

    if not full_name.startswith(prefix):
        return None

    return full_name[len(prefix):].strip() or None


def parse_academic_summary(html):
    """Разбирает сводку над таблицей индивидуального учебного плана."""
    soup = BeautifulSoup(html, "html.parser")

    headings = [
        tag
        for tag in soup.find_all("h4")
        if _text(tag) == "Индивидуальный учебный план"
    ]

    if len(headings) != 1:
        raise ValueError(
            "Не найдена однозначная сводка учебного плана."
        )

    summary = headings[0].find_next_sibling()

    if (
        summary is None
        or summary.name != "div"
        or "col-md-12" not in summary.get("class", [])
    ):
        raise ValueError(
            "Изменилась разметка сводки учебного плана."
        )

    labels = []

    # Читаем только блок сводки, без таблицы прошлых курсов.
    for block in summary.find_all("div", recursive=False):
        if "form-group" not in block.get("class", []):
            continue

        condition = (
            block.get("ng-if", "")
            .replace(" ", "")
            .lower()
        )

        # Пропускаем скрытые блоки и неизвестные условия.
        if condition not in {"", "true", "!false"}:
            continue

        label = block.find("label", recursive=False)

        if label is not None:
            labels.append(_text(label))

    def value(prefix, required=False):
        values = {
            text[len(prefix):].strip()
            for text in labels
            if text.startswith(prefix + " ")
        }
        values.discard("")

        if len(values) > 1:
            raise ValueError(
                f"Несколько разных значений: {prefix}."
            )

        if not values:
            if required:
                raise ValueError(
                    f"Отсутствует поле: {prefix}."
                )
            return None

        return values.pop()

    def named_code(prefix, required=False):
        raw = value(prefix, required=required)

        if raw is None:
            return None, None

        match = re.fullmatch(
            r"(.+?)\s*\(([A-Za-zА-Яа-я0-9.-]+)\)",
            raw,
        )

        if match is None:
            raise ValueError(
                f"Не распознан код поля: {prefix}."
            )

        return match.group(1).strip(), match.group(2)

    course = value("Курс", required=True)

    if re.fullmatch(r"[1-9][0-9]?", course) is None:
        raise ValueError("Некорректный курс.")

    program, program_code = named_code(
        "Образовательная программа",
        required=True,
    )

    group, group_code = named_code(
        "Группа образовательных программ"
    )

    years = set()

    for text in labels:
        match = re.fullmatch(
            r"(\d{4})\s*[-–—]\s*(\d{4})\s+учебный год",
            text,
        )

        if match:
            start, end = map(int, match.groups())

            if end != start + 1:
                raise ValueError("Некорректный учебный год.")

            years.add(f"{start}-{end}")

    if len(years) > 1:
        raise ValueError(
            "В сводке указано несколько учебных лет."
        )

    return {
        "full_name": value("Обучающийся"),
        "course": int(course),
        "degree": value("Академическая степень"),
        "education_program": program,
        "education_program_code": program_code,
        "education_program_group": group,
        "education_program_group_code": group_code,
        "study_form": value("Форма обучения"),
        "study_language": value("Язык обучения"),
        "academic_year": next(iter(years), None),
    }