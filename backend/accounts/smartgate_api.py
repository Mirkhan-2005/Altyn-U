from rest_framework.response import Response
from rest_framework.views import APIView

from .smartgate_auth import (
    IsSmartGateService,
    SmartGateAuthentication,
)


class SmartGateConnectionView(APIView):
    authentication_classes = [SmartGateAuthentication]
    permission_classes = [IsSmartGateService]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        response = Response({
            "status": "ok",
            "service": "altyn",
            "integration": "smartgate",
            "message": "Сервисный токен принят.",
        })
        response["Cache-Control"] = "no-store"
        return response