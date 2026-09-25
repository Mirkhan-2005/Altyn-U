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