from pathlib import Path
from uuid import uuid4

from django.db import models


def teacher_photo_path(instance, filename):
    extension = Path(filename).suffix.lower()

    return f"teacher_photos/{uuid4().hex}{extension}"


class Teacher(models.Model):
    display_name = models.CharField(
        "Имя для отображения",
        max_length=255,
    )

    normalized_name = models.CharField(
        "Ключ подписи из Platonus",
        max_length=255,
        unique=True,
        editable=False,
    )

    full_name = models.CharField(
        "Полное ФИО",
        max_length=255,
        blank=True,
        help_text="Заполняйте, если полное имя подтверждено.",
    )

    photo = models.ImageField(
        "Фотография",
        upload_to=teacher_photo_path,
        blank=True,
    )

    photo_source_url = models.URLField(
        "Источник фотографии",
        max_length=2048,
        blank=True,
        help_text=(
            "Ссылка на страницу или PDF сайта ЕНУ. "
            "На этом этапе файл по ссылке автоматически не скачивается."
        ),
    )

    photo_updated_at = models.DateTimeField(
        "Фотография обновлена",
        null=True,
        blank=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        "Создан",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"
        ordering = ["display_name", "id"]

    def __str__(self):
        return self.full_name or self.display_name