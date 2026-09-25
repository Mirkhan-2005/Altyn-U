from django.urls import path

from .views import health_check, PlatonusVerifyView


app_name = "accounts"

urlpatterns = [
    path(
        "health/",
        health_check,
        name="health",
    ),
    path(
        "platonus/verify/",
        PlatonusVerifyView.as_view(),
        name="platonus-verify",
    ),
]