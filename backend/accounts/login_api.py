from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import AccessToken


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
            "ident": request.META.get("REMOTE_ADDR", "unknown"),
        }


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            **serializer.validated_data,
        )

        if user is None or not user.is_active:
            return Response(
                {"detail": "Неверный ИИН или пароль Altyn."},
                status=401,
                headers={"Cache-Control": "no-store"},
            )

        return Response(
            {"access": str(AccessToken.for_user(user))},
            headers={"Cache-Control": "no-store"},
        )