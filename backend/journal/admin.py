import json

from django.contrib import admin
from django.utils.html import format_html

from .models import JournalSnapshot


@admin.register(JournalSnapshot)
class JournalSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "year",
        "term",
        "sync_status",
        "last_synced_at",
    )

    list_filter = (
        "year",
        "term",
        "sync_status",
    )

    search_fields = (
        "user__iin",
        "user__first_name",
        "user__last_name",
    )

    list_select_related = ("user",)
    ordering = ("-year", "term")
    list_per_page = 30

    fields = (
        "user",
        "year",
        "term",
        "sync_status",
        "sync_message",
        "last_synced_at",
        "last_sync_attempt_at",
        "journal_data",
    )

    readonly_fields = fields
    actions = None

    @admin.display(description="Сохранённый журнал")
    def journal_data(self, obj):
        text = json.dumps(
            obj.data,
            ensure_ascii=False,
            indent=2,
        )

        return format_html(
            '<pre style="white-space: pre-wrap; '
            'overflow-wrap: anywhere; max-width: 1000px;">{}</pre>',
            text,
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False