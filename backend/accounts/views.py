from rest_framework.parsers import JSONParser
from rest_framework.views import APIView

from rest_framework.exceptions import APIException

from .serializers import RegistrationCompleteSerializer
from .services.registration import (
    issue_registration,
    complete_registration,
)
from .throttles import RegistrationCompleteThrottle

from .serializers import PlatonusVerifySerializer
from .services.platonus import verify_student
from .throttles import PlatonusVerifyThrottle
from django.contrib.auth import get_user_model
from django.db import DatabaseError

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    User = get_user_model()

    try:
        # Проверяем доступ к таблице.
        # Отсутствие пользователей не считается ошибкой.
        User.objects.exists()
    except DatabaseError:
        return Response(
            {
                "status": "error",
                "message": "База данных недоступна.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "ok",
            "database": "connected",
        }
    )

class PlatonusVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    throttle_classes = [PlatonusVerifyThrottle]

    def post(self, request):
        serializer = PlatonusVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = verify_student(
                iin=serializer.validated_data["iin"],
                password=serializer.validated_data["platonus_password"],
            )
        except Exception:
            # Не возвращаем traceback или параметры внешнего запроса.
            return Response(
                {
                    "status": "verification_error",
                    "message": (
                        "Не удалось выполнить проверку Platonus. "
                        "Попробуйте позже."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        student_verified = (
            result.status == "student_verified"
            and result.authenticated is True
            and result.is_student is True
            and result.study_status_verified is True
            and result.active_student is True
        )

        if student_verified:
            try:
                token = issue_registration(
                    iin=serializer.validated_data["iin"],
                    platonus_password=serializer.validated_data[
                        "platonus_password"
                    ],
                )
            except APIException:
                raise
            except Exception:
                return Response(
                    {
                        "message": (
                            "Не удалось подготовить регистрацию. "
                            "Попробуйте позже."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            response = Response(
                {
                    "status": "student_verified",
                    "message": (
                        "Студент подтверждён. "
                        "Создайте пароль для Altyn."
                    ),
                    "registration_token": token,
                    "expires_in": 600,
                }
            )

            response["Cache-Control"] = "no-store"

            return response

        if result.status == "requires_code":
            return Response(
                {
                    "status": "requires_code",
                    "message": (
                        "Platonus запросил код из письма. "
                        "Подтверждение кодом на сайте Altyn "
                        "пока не подключено."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if result.status == "rate_limited":
            return Response(
                {
                    "status": "rate_limited",
                    "message": (
                        "Platonus ограничил попытки. "
                        "Повторите проверку позже."
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if (
            result.is_student is False
            or result.active_student is False
        ):
            return Response(
                {
                    "status": "student_not_eligible",
                    "message": (
                        "Регистрация доступна студентам "
                        "со статусом «Обучается»."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if result.status in {
            "not_confirmed",
            "authentication_rejected",
            "request_rejected",
            "invalid_input",
        }:
            return Response(
                {
                    "status": "not_confirmed",
                    "message": (
                        "Вход в Platonus не подтверждён. "
                        "Проверьте данные или попробуйте позже."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "verification_unavailable",
                "message": (
                    "Не удалось подтвердить роль или статус обучения. "
                    "Попробуйте позже."
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    

class RegistrationCompleteView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    throttle_classes = [RegistrationCompleteThrottle]

    def post(self, request):
        serializer = RegistrationCompleteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            complete_registration(
                token=serializer.validated_data[
                    "registration_token"
                ],
                password=serializer.validated_data["password"],
            )
        except APIException:
            raise
        except Exception:
            return Response(
                {
                    "message": (
                        "Не удалось завершить регистрацию. "
                        "Попробуйте позже."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response = Response(
            {
                "status": "registered",
                "message": (
                    "Аккаунт Altyn создан. "
                    "Теперь можно перейти ко входу."
                ),
            },
            status=status.HTTP_201_CREATED,
        )

        response["Cache-Control"] = "no-store"

        return response