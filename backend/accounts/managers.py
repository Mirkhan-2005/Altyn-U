import re

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, iin, password=None, **extra_fields):
        if not isinstance(iin, str):
            raise ValueError("ИИН должен передаваться строкой.")

        if not re.fullmatch(r"[0-9]{12}", iin):
            raise ValueError("ИИН должен содержать ровно 12 цифр.")

        if "email" in extra_fields:
            extra_fields["email"] = self.normalize_email(
                extra_fields["email"]
            )

        user = self.model(iin=iin, **extra_fields)

        # Django сохраняет хеш пароля.
        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, iin, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У администратора is_staff должен быть True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "У администратора is_superuser должен быть True."
            )

        if extra_fields.get("is_active") is not True:
            raise ValueError("Администратор должен быть активен.")

        if not password:
            raise ValueError("Укажите пароль администратора.")

        return self.create_user(iin, password, **extra_fields)