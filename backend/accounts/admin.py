from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import StudentProfile

from django import forms
from django.utils import timezone


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
        "student_full_name",
        "user",
        "student_status",
        "faculty",
        "course",
        "gpa",
        "sync_status",
        "last_synced_at",
    )

    list_filter = (
        "student_status",
        "sync_status",
    )

    list_select_related = ("user",)

    search_fields = (
        "user__iin",
        "user__first_name",
        "user__last_name",
    )

    readonly_fields = (
        "user",
        "gpa",
        "gpa_source",
        "sync_status",
        "sync_message",
        "last_synced_at",
        "last_sync_attempt_at",
        "gpa_updated_at",
        "photo_updated_at",
    )

    fields = readonly_fields + SMARTGATE_PROFILE_FIELDS

    actions = None

    @admin.display(description="ID Altyn", ordering="user_id")
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
        # Обновляем только отредактированные поля.
        # Фото, GPA и результаты синхронизации не перезаписываем.
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