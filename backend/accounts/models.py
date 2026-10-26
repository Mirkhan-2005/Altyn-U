from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
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



        # Дополнительные сведения о студенте.
    middle_name = models.CharField(
        verbose_name="Отчество",
        max_length=150,
        blank=True,
        default="",
    )

    faculty = models.CharField(
        verbose_name="Факультет",
        max_length=255,
        blank=True,
        default="",
    )

    course = models.PositiveSmallIntegerField(
        verbose_name="Курс",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    degree = models.CharField(
        verbose_name="Академическая степень",
        max_length=150,
        blank=True,
        default="",
    )

    education_program = models.CharField(
        verbose_name="Образовательная программа",
        max_length=500,
        blank=True,
        default="",
    )

    education_program_code = models.CharField(
        verbose_name="Код образовательной программы",
        max_length=32,
        blank=True,
        default="",
    )

    education_program_group = models.CharField(
        verbose_name="Группа образовательных программ",
        max_length=500,
        blank=True,
        default="",
    )

    education_program_group_code = models.CharField(
        verbose_name="Код группы образовательных программ",
        max_length=32,
        blank=True,
        default="",
    )

    study_form = models.CharField(
        verbose_name="Форма обучения",
        max_length=255,
        blank=True,
        default="",
    )

    study_language = models.CharField(
        verbose_name="Язык обучения",
        max_length=100,
        blank=True,
        default="",
    )

    academic_year = models.CharField(
        verbose_name="Учебный год",
        max_length=9,
        blank=True,
        default="",
    )

    academic_updated_at = models.DateTimeField(
        verbose_name="Дата обновления учебных данных",
        null=True,
        blank=True,
    )

    # Управляемый статус студента в Altyn.
    student_status = models.CharField(
        verbose_name="Статус студента",
        max_length=16,
        choices=[
            ("active", "Активен"),
            ("inactive", "Неактивен"),
            ("blocked", "Заблокирован"),
        ],
        default="active",
    )

    # Отдельное согласие для интеграции со SmartGate.
    smartgate_consent_at = models.DateTimeField(
        verbose_name="Дата согласия на SmartGate",
        null=True,
        blank=True,
    )

    smartgate_consent_version = models.CharField(
        verbose_name="Версия текста согласия SmartGate",
        max_length=64,
        blank=True,
        default="",
    )

    smartgate_consent_reference = models.CharField(
        verbose_name="Идентификатор подтверждения согласия",
        max_length=255,
        blank=True,
        default="",
        help_text="Номер документа или записи, подтверждающей согласие.",
    )

    smartgate_consent_revoked_at = models.DateTimeField(
        verbose_name="Дата отзыва согласия SmartGate",
        null=True,
        blank=True,
    )