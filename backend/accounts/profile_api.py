from django.http import FileResponse
from django.urls import reverse

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import StudentProfile
from .services.profile_sync import SyncError, sync_profile
from .services.profile_queue import queue_profile


class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True,
    )
    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True,
    )
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            "first_name",
            "last_name",
            "gpa",
            "gpa_source",
            "photo_url",
            "last_synced_at",
            "gpa_updated_at",
            "photo_updated_at",
            "last_sync_attempt_at",
            "sync_status",
            "sync_message",
        )
        read_only_fields = fields

    def get_photo_url(self, obj):
        if not obj.photo:
            return None

        return reverse("accounts:profile-photo")


class ProfileSyncThrottle(UserRateThrottle):
    scope = "profile_sync"
    rate = "5/hour"


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = StudentProfile.objects.get_or_create(
            user=request.user
        )

        return Response(
            ProfileSerializer(profile).data,
            headers={"Cache-Control": "no-store"},
        )


class ProfileSyncView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ProfileSyncThrottle]

    def post(self, request):
        try:
            profile = queue_profile(
                request.user,
                force=True,
            )
        except SyncError as exc:
            return Response(
                {"detail": str(exc)},
                status=exc.status_code,
                headers={"Cache-Control": "no-store"},
            )

        if profile.sync_status == "error":
            return Response(
                {
                    "detail": (
                        profile.sync_message
                        or "Не удалось запустить обновление."
                    ),
                },
                status=503,
                headers={"Cache-Control": "no-store"},
            )

        return Response(
            ProfileSerializer(profile).data,
            status=(
                202
                if profile.sync_status in {"queued", "syncing"}
                else 200
            ),
            headers={"Cache-Control": "no-store"},
        )


class ProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = StudentProfile.objects.filter(
            user=request.user
        ).first()

        if profile is None or not profile.photo:
            raise NotFound("Фотография пока не загружена.")

        try:
            file = profile.photo.open("rb")
        except FileNotFoundError:
            raise NotFound(
                "Фотография отсутствует в хранилище."
            )

        extension = profile.photo.name[
            profile.photo.name.rfind("."):
        ]

        response = FileResponse(
            file,
            filename=f"photo{extension}",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response