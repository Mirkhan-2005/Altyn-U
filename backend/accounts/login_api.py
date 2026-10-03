import logging

from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import AccessToken

from journal.services.import_queue import queue_journal_import

from .services.profile_queue import queue_profile
from .services.profile_sync import SyncError


logger = logging.getLogger(__name__)


class LoginSerializer(serializers.Serializer):
    iin = serializers.RegexField(
        regex=r"\A[0-9]{12}\Z",
        max_length=12,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
    )


class LoginThrottle(SimpleRateThrottle):
    scope = "altyn_login"
    rate = "5/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.META.get(
                "REMOTE_ADDR",
                "unknown",
            ),
        }


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            **serializer.validated_data,
        )

        if user is None or not user.is_active:
            return Response(
                {
                    "detail": "Неверный ИИН или пароль Altyn.",
                },
                status=401,
                headers={"Cache-Control": "no-store"},
            )

        # Если профиль ещё не загружен, ставим его в очередь.
        try:
            queue_profile(user)
        except SyncError:
            pass
        except Exception as exc:
            logger.error(
                "Не удалось подготовить загрузку профиля "
                "user_id=%s, тип=%s",
                user.pk,
                type(exc).__name__,
            )

        # Если профиль уже готов, запускаем импорт журналов.
        # Иначе его запустит задача загрузки профиля.
        try:
            queue_journal_import(user)
        except Exception as exc:
            logger.error(
                "Не удалось подготовить импорт журналов "
                "user_id=%s, тип=%s",
                user.pk,
                type(exc).__name__,
            )

        return Response(
            {
                "access": str(AccessToken.for_user(user)),
            },
            headers={"Cache-Control": "no-store"},
        )