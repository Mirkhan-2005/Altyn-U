import re
import unicodedata

from .models import Teacher


EMPTY_LABELS = {
    "",
    "-",
    "—",
    "–",
    "нет",
    "не указан",
    "не указано",
}


def normalize_teacher_label(label):
    """Возвращает отображаемую подпись и ключ для поиска."""
    if not isinstance(label, str):
        raise ValueError("Подпись преподавателя должна быть строкой.")

    text = unicodedata.normalize("NFC", label)
    display_name = " ".join(text.split())

    if display_name.casefold() in EMPTY_LABELS:
        return "", ""

    # Отличия в регистре, пробелах и точках не создают дубликаты.
    # Казахские и русские буквы не заменяем друг на друга.
    normalized_name = re.sub(
        r"[\s.]+",
        "",
        display_name.casefold(),
    )

    if not normalized_name:
        return "", ""

    if len(display_name) > 255 or len(normalized_name) > 255:
        raise ValueError(
            "Подпись преподавателя превышает 255 символов."
        )

    return display_name, normalized_name


def get_or_create_teacher(label):
    display_name, normalized_name = normalize_teacher_label(label)

    if not normalized_name:
        return None

    teacher, _ = Teacher.objects.get_or_create(
        normalized_name=normalized_name,
        defaults={
            "display_name": display_name,
        },
    )

    return teacher