import mimetypes

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .forms import TeacherAdminForm
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    form = TeacherAdminForm

    list_display = (
        "photo_preview",
        "display_name",
        "full_name",
        "lesson_rows_count",
        "photo_updated_at",
    )

    list_display_links = ("display_name",)

    search_fields = (
        "display_name",
        "full_name",
        "normalized_name",
    )

    readonly_fields = (
        "photo_preview",
        "normalized_name",
        "photo_updated_at",
        "created_at",
    )

    fields = (
        "display_name",
        "full_name",
        "normalized_name",
        "photo_preview",
        "photo",
        "remove_photo",
        "photo_source_url",
        "photo_updated_at",
        "created_at",
    )

    ordering = ("display_name", "id")
    list_per_page = 30

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                linked_rows_count=Count("lesson_rows"),
            )
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:teacher_id>/photo/",
                self.admin_site.admin_view(self.photo_view),
                name="teachers_teacher_photo",
            ),
        ]

        return custom_urls + super().get_urls()

    def photo_view(self, request, teacher_id):
        teacher = get_object_or_404(
            Teacher,
            pk=teacher_id,
        )

        if not self.has_view_permission(request, teacher):
            raise PermissionDenied

        if not teacher.photo:
            raise Http404("Фотография отсутствует.")

        try:
            photo_file = teacher.photo.open("rb")
        except FileNotFoundError:
            raise Http404("Файл фотографии не найден.") from None

        content_type = (
            mimetypes.guess_type(teacher.photo.name)[0]
            or "application/octet-stream"
        )

        response = FileResponse(
            photo_file,
            content_type=content_type,
        )

        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response

    @admin.display(description="Фото")
    def photo_preview(self, obj):
        if not obj or not obj.pk or not obj.photo:
            return "Нет фото"

        url = reverse(
            "admin:teachers_teacher_photo",
            args=[obj.pk],
        )

        return format_html(
            '<img src="{}" alt="{}" width="64" height="80" '
            'style="object-fit:cover;border-radius:8px;">',
            url,
            obj.full_name or obj.display_name,
        )

    @admin.display(
        description="Строк занятий",
        ordering="linked_rows_count",
    )
    def lesson_rows_count(self, obj):
        return obj.linked_rows_count

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("remove_photo"):
            obj.photo = ""
            obj.photo_source_url = ""
            obj.photo_updated_at = None

        elif "photo" in request.FILES:
            obj.photo_updated_at = timezone.now()

        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False