import logging
from uuid import uuid4

from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import StudentProfile
from .smartgate_auth import (
    IsSmartGateService,
    SmartGateAuthentication,
)

import hashlib
from pathlib import Path

from django.http import HttpResponse
from django.urls import reverse


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


MAX_SMARTGATE_PHOTO_BYTES = 5_000_000


class SmartGatePhotoUnavailable(APIException):
    status_code = 503
    default_detail = "Фотография временно недоступна."
    default_code = "photo_unavailable"


def get_smartgate_profile(student_id):
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

    return profile


def get_smartgate_status(profile):
    if profile.student_status == "blocked":
        return "blocked"

    if (
        not profile.user.is_active
        or profile.student_status != "active"
    ):
        return "inactive"

    return "active"


def read_smartgate_photo(profile):
    if not profile.photo:
        return None

    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(Path(profile.photo.name).suffix.lower())

    if content_type is None:
        raise SmartGatePhotoUnavailable()

    try:
        with profile.photo.open("rb") as photo:
            content = photo.read(MAX_SMARTGATE_PHOTO_BYTES + 1)

    except FileNotFoundError:
        return None

    except OSError:
        raise SmartGatePhotoUnavailable() from None

    if not content or len(content) > MAX_SMARTGATE_PHOTO_BYTES:
        raise SmartGatePhotoUnavailable()

    # Версия зависит от байтов фотографии, а не даты синхронизации.
    version = hashlib.sha256(content).hexdigest()

    return content, content_type, version


class SmartGateStudentDetailView(SmartGateBaseView):
    def get(self, request, student_id):
        profile = get_smartgate_profile(student_id)
        user = profile.user
        student_status = get_smartgate_status(profile)

        # Статус блокировки передаём, но фотографию не выдаём.
        photo = (
            read_smartgate_photo(profile)
            if student_status == "active"
            else None
        )

        photo_url = None
        photo_version = None

        if photo is not None:
            photo_version = photo[2]

            photo_url = (
                reverse(
                    "smartgate-student-photo",
                    kwargs={"student_id": user.pk},
                )
                + f"?version={photo_version}"
            )

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
                "photo_url": photo_url,
                "photo_version": photo_version,
                "photo_updated_at": profile.photo_updated_at,
            },
            content_type="application/json; charset=utf-8",
        )


class SmartGateStudentPhotoView(SmartGateBaseView):
    def get(self, request, student_id):
        profile = get_smartgate_profile(student_id)

        if get_smartgate_status(profile) != "active":
            raise NotFound("Фотография недоступна.")

        photo = read_smartgate_photo(profile)

        if photo is None:
            raise NotFound("Фотография недоступна.")

        content, content_type, version = photo

        requested_version = request.query_params.get("version")

        # Между получением JSON и скачиванием фото могло обновиться.
        if (
            requested_version is not None
            and requested_version != version
        ):
            return Response(
                {
                    "detail": (
                        "Фотография изменилась. "
                        "Повторно получите данные студента."
                    ),
                },
                status=409,
            )

        response = HttpResponse(
            content,
            content_type=content_type,
        )

        response["X-Content-Type-Options"] = "nosniff"
        response["X-Photo-Version"] = version
        response["ETag"] = f'"{version}"'

        return response
    


class SmartGateStudentListView(SmartGateBaseView):
    """Список студентов для полного обхода и импорта."""

    PAGE_SIZE = 50

    def get(self, request):
        raw_after_id = request.query_params.get("after_id", "0")

        if (
            not raw_after_id.isascii()
            or not raw_after_id.isdecimal()
            or len(raw_after_id) > 19
        ):
            return Response(
                {"detail": "after_id должен быть целым неотрицательным числом."},
                status=400,
            )

        after_id = int(raw_after_id)

        if after_id > 9223372036854775807:
            return Response(
                {"detail": "Недопустимое значение after_id."},
                status=400,
            )

        # Берём профили студентов, а не всех пользователей сайта.
        # Дополнительная запись позволяет определить наличие следующей страницы.
        profiles = list(
            StudentProfile.objects
            .select_related("user")
            .filter(user_id__gt=after_id)
            .order_by("user_id")[:self.PAGE_SIZE + 1]
        )

        has_more = len(profiles) > self.PAGE_SIZE
        page = profiles[:self.PAGE_SIZE]
        results = []

        for profile in page:
            status = get_smartgate_status(profile)

            results.append({
                "id": str(profile.user_id),
                "first_name": profile.user.first_name,
                "last_name": profile.user.last_name,
                "middle_name": profile.middle_name or None,
                "faculty": profile.faculty or None,
                "course": profile.course,
                "student_status": status,
                "access_allowed": status == "active",
            })

        return Response(
            {
                "results": results,
                "next_after_id": (
                    str(page[-1].user_id) if has_more else None
                ),
            },
            content_type="application/json; charset=utf-8",
        )