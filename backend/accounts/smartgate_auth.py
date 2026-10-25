import hashlib
import hmac
import re
from dataclasses import dataclass

from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
)
from rest_framework.permissions import BasePermission

from config.settings import config


@dataclass(frozen=True)
class SmartGateService:
    """Сервис SmartGate, а не пользователь сайта."""

    name: str = "smartgate"
    is_authenticated: bool = True
    is_staff: bool = False
    is_superuser: bool = False


class SmartGateAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if not config("SMARTGATE_ENABLED", default=False, cast=bool):
            raise NotFound()

        if not request.is_secure():
            raise PermissionDenied("Для SmartGate требуется HTTPS.")

        header = get_authorization_header(request)

        if not header:
            return None

        if len(header) > 1024:
            raise AuthenticationFailed("Некорректная авторизация.")

        parts = header.split()

        if len(parts) != 2 or parts[0].lower() != b"smartgate":
            raise AuthenticationFailed(
                "Используйте Authorization: SmartGate <token>."
            )

        token = parts[1]

        if not 32 <= len(token) <= 512:
            raise AuthenticationFailed("Неверный сервисный токен.")

        expected_hash = config(
            "SMARTGATE_TOKEN_SHA256",
            default="",
        ).strip()

        # Без корректной настройки доступ остаётся закрытым.
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise AuthenticationFailed(
                "Сервисная авторизация не настроена."
            )

        actual_hash = hashlib.sha256(token).hexdigest()

        if not hmac.compare_digest(actual_hash, expected_hash):
            raise AuthenticationFailed("Неверный сервисный токен.")

        # Сам токен не сохраняем в request.auth.
        return SmartGateService(), None

    def authenticate_header(self, request):
        return "SmartGate"


class IsSmartGateService(BasePermission):
    message = "Доступ разрешён только сервису SmartGate."

    def has_permission(self, request, view):
        return isinstance(request.user, SmartGateService)