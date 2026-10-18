from django.urls import path

from .views import (
    TeacherDetailView,
    TeacherListView,
    TeacherPhotoView,
)


app_name = "teachers"

urlpatterns = [
    path(
        "",
        TeacherListView.as_view(),
        name="list",
    ),
    path(
        "<int:teacher_id>/",
        TeacherDetailView.as_view(),
        name="detail",
    ),
    path(
        "<int:teacher_id>/photo/",
        TeacherPhotoView.as_view(),
        name="photo",
    ),
]