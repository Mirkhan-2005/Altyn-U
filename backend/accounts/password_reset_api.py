import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.crypto import salted_hmac

from rest_framework import serializers
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import StrictStringField
from .services.platonus import verify_student
from .throttles import PlatonusVerifyThrottle


DENIED = "Не удалось подтвердить восстановление аккаунта."


class PasswordResetSerializer(serializers.Serializer):
    iin = StrictStringField(
        min_length=12,
        max_length=12,
        trim_whitespace=False,
    )

    platonus_password = StrictStringField(
        max_length=256,
        trim_whitespace=False,
        write_only=True,
    )

    new_password = StrictStringField(
        min_length=8,
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )

    new_password_confirm = StrictStringField(
        min_length=8,
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )

    def validate_iin(self, value):
        if not re.fullmatch(r"[0-9]{12}", value):
            raise serializers.ValidationError(
                "ИИН должен содержать 12 цифр."
            )
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({
                "new_password_confirm": "Пароли не совпадают.",
            })
        return attrs


class PasswordResetIPThrottle(PlatonusVerifyThrottle):
    scope = "password_reset_ip"
    rate = "5/min"


class PasswordResetIINThrottle(PlatonusVerifyThrottle):
    scope = "password_reset_iin"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        data = request.data
        iin = data.get("iin") if isinstance(data, dict) else None

        if (
            not isinstance(iin, str)
            or not re.fullmatch(r"[0-9]{12}", iin)
        ):
            return None

        # Не помещаем сам ИИН в ключ кеша.
        digest = salted_hmac(
            "password-reset-iin",
            iin,
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": digest,
        }


class PasswordResetView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    throttle_classes = [
        PasswordResetIPThrottle,
        PasswordResetIINThrottle,
    ]

    http_method_names = ["post", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(
            request,
            response,
            *args,
            **kwargs,
        )
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Проверяем текущий пароль непосредственно в Platonus.
        try:
            result = verify_student(
                iin=data["iin"],
                password=data["platonus_password"],
            )
        except Exception:
            return Response(
                {
                    "detail": (
                        "Проверка Platonus временно недоступна."
                    )
                },
                status=503,
            )

        if result.status == "requires_code":
            return Response(
                {
                    "detail": (
                        "Platonus требует код подтверждения. "
                        "Восстановление с кодом пока не подключено."
                    )
                },
                status=409,
            )

        if result.status == "rate_limited":
            return Response(
                {
                    "detail": (
                        "Platonus ограничил попытки. "
                        "Повторите позже."
                    )
                },
                status=429,
            )

        verified = (
            result.status == "student_verified"
            and result.authenticated is True
            and result.is_student is True
            and result.study_status_verified is True
            and result.active_student is True
        )

        if not verified:
            return Response(
                {"detail": DENIED},
                status=400,
            )

        User = get_user_model()

        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(iin=data["iin"])
                .first()
            )

            # Форма предназначена для обычных активных аккаунтов.
            if (
                user is None
                or not user.is_active
                or user.is_staff
                or user.is_superuser
            ):
                return Response(
                    {"detail": DENIED},
                    status=400,
                )

            try:
                validate_password(
                    data["new_password"],
                    user=user,
                )
            except DjangoValidationError as error:
                return Response(
                    {"new_password": error.messages},
                    status=400,
                )

            user.set_password(data["new_password"])
            user.save(update_fields=["password"])

        return Response({
            "status": "password_changed",
            "message": (
                "Пароль Altyn изменён. "
                "Войдите с новым паролем."
            ),
        })