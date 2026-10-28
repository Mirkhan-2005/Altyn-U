from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import StudentProfile

from django import forms
from django.utils import timezone

from pathlib import PurePosixPath

from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils.html import format_html



User = get_user_model()


class AltynUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("iin",)


class AltynUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class AltynUserAdmin(UserAdmin):
    add_form = AltynUserCreationForm
    form = AltynUserChangeForm

    list_display = (
        "id",
        "iin",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "iin",
        "first_name",
        "last_name",
        "email",
    )

    ordering = ("iin",)

    fieldsets = (
        (
            "Аккаунт",
            {
                "fields": (
                    "iin",
                    "password",
                ),
            },
        ),
        (
            "Личные данные",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                ),
            },
        ),
        (
            "Доступ",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Даты",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                ),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "iin",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = ("last_login", "date_joined")

        # ИИН уже созданного аккаунта связан с данными Platonus.
        if obj is not None:
            return fields + ("iin",)

        return fields


SMARTGATE_PROFILE_FIELDS = (
    "middle_name",
    "faculty",
    "course",
    "student_status",
    "smartgate_consent_at",
    "smartgate_consent_version",
    "smartgate_consent_reference",
    "smartgate_consent_revoked_at",
)


class StudentProfileAdminForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = SMARTGATE_PROFILE_FIELDS

    def clean(self):
        cleaned = super().clean()

        consent_at = cleaned.get("smartgate_consent_at")
        version = cleaned.get("smartgate_consent_version")
        reference = cleaned.get("smartgate_consent_reference")
        revoked_at = cleaned.get("smartgate_consent_revoked_at")

        now = timezone.now()

        if consent_at:
            if consent_at > now:
                self.add_error(
                    "smartgate_consent_at",
                    "Дата согласия не может быть в будущем.",
                )

            if not version:
                self.add_error(
                    "smartgate_consent_version",
                    "Укажите версию текста полученного согласия.",
                )

            if not reference:
                self.add_error(
                    "smartgate_consent_reference",
                    "Укажите номер документа или записи согласия.",
                )

        elif version or reference or revoked_at:
            self.add_error(
                "smartgate_consent_at",
                "Укажите дату получения согласия.",
            )

        if revoked_at:
            if revoked_at > now:
                self.add_error(
                    "smartgate_consent_revoked_at",
                    "Дата отзыва не может быть в будущем.",
                )

            if consent_at and revoked_at < consent_at:
                self.add_error(
                    "smartgate_consent_revoked_at",
                    "Дата отзыва не может быть раньше согласия.",
                )

        return cleaned


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    form = StudentProfileAdminForm

    list_display = (
        "altyn_id",
        "photo_thumbnail",
        "student_full_name",
        "student_status",
        "faculty",
        "course",
        "gpa",
        "sync_status",
        "last_synced_at",
    )

    list_display_links = (
        "altyn_id",
        "student_full_name",
    )

    list_filter = (
        "student_status",
        "sync_status",
        "course",
    )

    list_select_related = ("user",)
    list_per_page = 25
    ordering = ("-user_id",)

    search_fields = (
        "=user__id",
        "user__iin",
        "user__first_name",
        "user__last_name",
        "middle_name",
        "education_program",
    )

    search_help_text = (
        "Поиск по ID Altyn, ИИН, ФИО "
        "или образовательной программе."
    )

    readonly_fields = (
        "altyn_id",
        "student_full_name",
        "photo_preview",
        "user",
        "gpa",
        "gpa_source",
        "degree",
        "education_program",
        "education_program_code",
        "education_program_group",
        "education_program_group_code",
        "study_form",
        "study_language",
        "academic_year",
        "academic_updated_at",
        "sync_status",
        "sync_message",
        "last_synced_at",
        "last_sync_attempt_at",
        "gpa_updated_at",
        "photo_updated_at",
    )

    fieldsets = (
        (
            "Студент",
            {
                "fields": (
                    "photo_preview",
                    ("altyn_id", "student_full_name"),
                    "user",
                    "middle_name",
                    "student_status",
                ),
            },
        ),
        (
            "Учебные данные",
            {
                "fields": (
                    ("faculty", "course"),
                    ("gpa", "degree"),
                    "education_program",
                    "education_program_code",
                    "education_program_group",
                    "education_program_group_code",
                    "study_form",
                    ("study_language", "academic_year"),
                    "academic_updated_at",
                ),
            },
        ),
        (
            "Синхронизация с Platonus",
            {
                "classes": ("collapse",),
                "fields": (
                    "sync_status",
                    "sync_message",
                    "last_synced_at",
                    "last_sync_attempt_at",
                    "photo_updated_at",
                    "gpa_updated_at",
                    "gpa_source",
                ),
            },
        ),
        (
            "Сведения о согласии SmartGate",
            {
                "classes": ("collapse",),
                "fields": (
                    "smartgate_consent_at",
                    "smartgate_consent_version",
                    "smartgate_consent_reference",
                    "smartgate_consent_revoked_at",
                ),
            },
        ),
    )

    actions = None

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/photo/",
                self.admin_site.admin_view(self.photo_view),
                name="accounts_studentprofile_photo",
            ),
        ]

        return custom_urls + super().get_urls()

    def photo_view(self, request, object_id):
        profile = self.get_object(request, str(object_id))

        if profile is None:
            raise Http404("Профиль не найден.")

        if not self.has_view_permission(request, profile):
            raise PermissionDenied

        if not profile.photo:
            raise Http404("Фотография отсутствует.")

        extension = PurePosixPath(
            profile.photo.name
        ).suffix.lower()

        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(extension)

        if content_type is None:
            raise Http404("Формат фотографии не поддерживается.")

        try:
            photo_file = profile.photo.storage.open(
                profile.photo.name,
                "rb",
            )
        except FileNotFoundError:
            raise Http404("Файл фотографии не найден.") from None

        response = FileResponse(
            photo_file,
            content_type=content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response

    def render_photo(self, obj, *, large=False):
        if obj is None or not obj.pk or not obj.photo:
            return "Фото отсутствует"

        url = reverse(
            f"{self.admin_site.name}:accounts_studentprofile_photo",
            args=[obj.pk],
        )

        if large:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">'
                '<img src="{}" alt="Фотография студента" '
                'style="width:160px;height:200px;'
                'object-fit:contain;border-radius:10px;'
                'border:1px solid var(--hairline-color);">'
                "</a>",
                url,
                url,
            )

        return format_html(
            '<img src="{}" alt="Фото" loading="lazy" '
            'width="44" height="56" '
            'style="object-fit:cover;border-radius:6px;">',
            url,
        )

    @admin.display(description="Фото")
    def photo_thumbnail(self, obj):
        return self.render_photo(obj)

    @admin.display(description="Фотография")
    def photo_preview(self, obj):
        return self.render_photo(obj, large=True)

    @admin.display(
        description="ID Altyn",
        ordering="user_id",
    )
    def altyn_id(self, obj):
        return obj.user_id

    @admin.display(
        description="ФИО",
        ordering="user__last_name",
    )
    def student_full_name(self, obj):
        name = " ".join(
            part
            for part in (
                obj.user.last_name,
                obj.user.first_name,
                obj.middle_name,
            )
            if part
        )

        return name or "Не загружено"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Сохраняем только вручную отредактированные поля.
        # Фоновая синхронизация отдельно обновляет фото и GPA.
        changed_fields = [
            name
            for name in form.changed_data
            if name in SMARTGATE_PROFILE_FIELDS
        ]

        if changed_fields:
            obj.save(update_fields=changed_fields)


admin.site.site_header = "Altyn — администрирование"
admin.site.site_title = "Altyn Admin"
admin.site.index_title = "Управление сайтом"