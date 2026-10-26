from django.contrib import admin
from django.urls import include, path

from accounts.smartgate_api import (
    SmartGateConnectionView,
    SmartGateStudentDetailView,
)

from accounts.smartgate_api import (
    SmartGateConnectionView,
    SmartGateStudentDetailView,
    SmartGateStudentPhotoView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/journal/", include("journal.urls")),
    path("api/teachers/", include("teachers.urls")),

    path(
        "api/integrations/smartgate/connection",
        SmartGateConnectionView.as_view(),
        name="smartgate-connection",
    ),

    path(
        "api/integrations/smartgate/students/<int:student_id>",
        SmartGateStudentDetailView.as_view(),
        name="smartgate-student-detail",
    ),
    path(
        "api/integrations/smartgate/students/<int:student_id>/photo",
        SmartGateStudentPhotoView.as_view(),
        name="smartgate-student-photo",
    ),
]