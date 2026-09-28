from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None

    iin = models.CharField(
        verbose_name="ИИН",
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"\A[0-9]{12}\Z",
                message="ИИН должен содержать ровно 12 цифр.",
            )
        ],
    )

    USERNAME_FIELD = "iin"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.iin
    

class PendingRegistration(models.Model):
    token_digest = models.CharField(max_length=64, unique=True)
    iin = models.CharField(max_length=12)

    encrypted_password = models.TextField(editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    consent_at = models.DateTimeField()
    consent_version = models.CharField(max_length=32)


class PlatonusConnection(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platonus_connection",
    )

    encrypted_password = models.TextField(editable=False)

    consent_at = models.DateTimeField()
    consent_version = models.CharField(max_length=32)

    last_verified_at = models.DateTimeField()


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )
    gpa_source = models.CharField(max_length=64, blank=True)

    photo = models.ImageField(
        upload_to="student_photos/",
        blank=True,
    )

    last_synced_at = models.DateTimeField(null=True, blank=True)
    gpa_updated_at = models.DateTimeField(null=True, blank=True)
    photo_updated_at = models.DateTimeField(null=True, blank=True)
    last_sync_attempt_at = models.DateTimeField(null=True, blank=True)

    sync_status = models.CharField(max_length=16, default="pending")
    sync_message = models.TextField(blank=True)