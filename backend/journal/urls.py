from django.urls import path

from .auto_api import JournalAutoSyncView
from .views import JournalView, JournalSyncView


app_name = "journal"

urlpatterns = [
    path(
        "",
        JournalView.as_view(),
        name="detail",
    ),
    path(
        "sync/",
        JournalSyncView.as_view(),
        name="sync",
    ),
    path(
        "auto-sync/",
        JournalAutoSyncView.as_view(),
        name="auto-sync",
    ),
]