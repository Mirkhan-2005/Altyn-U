from django.urls import path
from .password_reset_api import PasswordResetView
from .views import (
    health_check,
    PlatonusVerifyView,
    RegistrationCompleteView,
)
from .login_api import LoginView
from .profile_api import (
    ProfileView,
    ProfileSyncView,
    ProfilePhotoView,
)

from .ranking_api import StudentRankingView


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
    path(
        "register/complete/",
        RegistrationCompleteView.as_view(),
        name="register-complete",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),
    path(
        "profile/sync/",
        ProfileSyncView.as_view(),
        name="profile-sync",
    ),
    path(
        "profile/photo/",
        ProfilePhotoView.as_view(),
        name="profile-photo",
    ),
    path(
        "password/reset/",
        PasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "ranking/",
        StudentRankingView.as_view(),
        name="student-ranking",
    ),
]