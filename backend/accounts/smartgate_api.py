import logging
from uuid import uuid4

from django.utils import timezone

from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import StudentProfile
from .smartgate_auth import (
    IsSmartGateService,
    SmartGateAuthentication,
)


# Отдельный журнал в вывод контейнера.
# Токены, ФИО, ИИН и содержимое ответов сюда не записываем.
audit_logger = logging.getLogger("altyn.smartgate.audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    audit_logger.addHandler(handler)


class SmartGateReadThrottle(SimpleRateThrottle):
    rate = "60/min"

    def get_cache_key(self, request, view):
        # Общий лимит для сервисного клиента SmartGate.
        return "smartgate:read:service:v1"


class SmartGateBaseView(APIView):
    authentication_classes = [SmartGateAuthentication]
    permission_classes = [IsSmartGateService]
    throttle_classes = [SmartGateReadThrottle]
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(
            request, response, *args, **kwargs
        )

        request_id = uuid4().hex

        response["Cache-Control"] = "private, no-store"
        response["X-Request-ID"] = request_id

        audit_logger.info(
            "request_id=%s operation=%s method=%s status=%s",
            request_id,
            self.__class__.__name__,
            request.method,
            response.status_code,
        )

        return response


class SmartGateConnectionView(SmartGateBaseView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "altyn",
                "integration": "smartgate",
                "message": "Сервисный токен принят.",
            },
            content_type="application/json; charset=utf-8",
        )


class SmartGateStudentDetailView(SmartGateBaseView):
    def get(self, request, student_id):
        if not 1 <= student_id <= 9223372036854775807:
            raise NotFound("Студент недоступен.")

        profile = (
            StudentProfile.objects
            .select_related("user")
            .filter(user_id=student_id)
            .first()
        )

        if profile is None:
            raise NotFound("Студент недоступен.")

        # Передача данных разрешена только при наличии
        # заполненного и не отозванного согласия.
        consent_valid = (
            profile.smartgate_consent_at is not None
            and profile.smartgate_consent_at <= timezone.now()
            and bool(profile.smartgate_consent_version.strip())
            and bool(profile.smartgate_consent_reference.strip())
            and profile.smartgate_consent_revoked_at is None
        )

        if not consent_valid:
            raise NotFound("Студент недоступен.")

        user = profile.user

        if profile.student_status == "blocked":
            student_status = "blocked"
        elif (
            not user.is_active
            or profile.student_status != "active"
        ):
            student_status = "inactive"
        else:
            student_status = "active"

        return Response(
            {
                "id": str(user.pk),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "middle_name": profile.middle_name or None,
                "faculty": profile.faculty or None,
                "course": profile.course,
                "student_status": student_status,
                "access_allowed": student_status == "active",
            },
            content_type="application/json; charset=utf-8",
        )