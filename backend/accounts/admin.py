from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import StudentProfile


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


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "gpa",
        "sync_status",
        "last_synced_at",
    )

    list_filter = ("sync_status",)
    list_select_related = ("user",)

    search_fields = (
        "user__iin",
        "user__first_name",
        "user__last_name",
    )

    fields = (
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

    readonly_fields = fields
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.site_header = "Altyn — администрирование"
admin.site.site_title = "Altyn Admin"
admin.site.index_title = "Управление сайтом"