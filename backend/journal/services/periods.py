import re

from bs4 import BeautifulSoup

from .parser import JournalError


def parse_periods(html, *, expected_student_id, expected_year=None):
    """Читает списки формы, даже если таблицы оценок пока нет."""
    soup = BeautifulSoup(html, "html.parser")

    forms = soup.find_all(
        "form",
        action="current_progress_gradebook_student",
    )

    if len(forms) != 1:
        raise JournalError(
            "Форма выбора периода не найдена или неоднозначна."
        )

    form = forms[0]

    owners = form.find_all(
        "input",
        attrs={"name": "studentID"},
    )

    owner = (
        owners[0].get("value", "")
        if len(owners) == 1
        else ""
    )

    if (
        not re.fullmatch(r"[0-9]+", owner)
        or int(owner) != expected_student_id
    ):
        raise JournalError(
            "Список периодов не соответствует студенту."
        )

    def read_options(name):
        selects = form.find_all(
            "select",
            attrs={"name": name},
        )

        if len(selects) != 1:
            raise JournalError(
                f"Не найден однозначный список {name}."
            )

        choices = []
        selected = []

        for option in selects[0].find_all("option"):
            raw = option.get("value", "")

            if option.has_attr("disabled") or raw == "":
                continue

            if not re.fullmatch(r"-?[0-9]+", raw):
                raise JournalError(
                    f"Неизвестное значение в списке {name}."
                )

            value = int(raw)

            valid = (
                2000 <= value <= 2100
                if name == "year"
                else value != 0 and abs(value) <= 20
            )

            if not valid or any(
                item["value"] == value
                for item in choices
            ):
                raise JournalError(
                    f"Некорректный список {name}."
                )

            choices.append({
                "value": value,
                "label": option.get_text(" ", strip=True),
            })

            if option.has_attr("selected"):
                selected.append(value)

        if not choices or len(selected) != 1:
            raise JournalError(
                f"Не удалось подтвердить выбранный {name}."
            )

        return choices, selected[0]

    years, selected_year = read_options("year")
    terms, selected_term = read_options("term")

    if (
        expected_year is not None
        and selected_year != expected_year
    ):
        raise JournalError(
            "Platonus вернул другой учебный год."
        )

    return {
        "years": years,
        "terms": terms,
        "selected_year": selected_year,
        "selected_term": selected_term,
    }