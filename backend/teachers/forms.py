from pathlib import Path

from django import forms

from .models import Teacher


MAX_PHOTO_BYTES = 5_000_000
MAX_PHOTO_PIXELS = 16_000_000

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class TeacherAdminForm(forms.ModelForm):
    photo = forms.ImageField(
        label="Загрузить фотографию",
        required=False,
        widget=forms.FileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
        help_text=(
            "JPG, PNG или WebP. До 5 МБ и 16 мегапикселей. "
            "Если не выбирать файл, текущая фотография сохранится."
        ),
    )

    remove_photo = forms.BooleanField(
        label="Убрать текущую фотографию",
        required=False,
    )

    class Meta:
        model = Teacher
        fields = (
            "display_name",
            "full_name",
            "photo",
            "photo_source_url",
        )

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")

        # При редактировании без нового файла
        # Django сохраняет существующее значение.
        if "photo" not in self.files:
            return photo

        if photo.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError(
                "Фотография должна быть не больше 5 МБ."
            )

        extension = Path(photo.name).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                "Допустимы файлы JPG, PNG и WebP."
            )

        # ImageField уже проверил изображение через Pillow.
        picture = photo.image

        if picture.format not in ALLOWED_FORMATS:
            raise forms.ValidationError(
                "Формат изображения не поддерживается."
            )

        if picture.width * picture.height > MAX_PHOTO_PIXELS:
            raise forms.ValidationError(
                "Разрешение фотографии превышает 16 мегапикселей."
            )

        return photo

    def clean(self):
        cleaned = super().clean()

        if (
            cleaned.get("remove_photo")
            and "photo" in self.files
        ):
            raise forms.ValidationError(
                "Выберите одно действие: загрузить новую "
                "фотографию или убрать текущую."
            )

        return cleaned