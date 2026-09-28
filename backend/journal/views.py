from django.shortcuts import get_object_or_404

from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import JournalSnapshot
from .serializers import JournalSerializer, PeriodSerializer
from .services.client import JournalSyncError
from .services.sync import sync_journal


class JournalSyncThrottle(UserRateThrottle):
    scope = "journal_sync"
    rate = "5/hour"


class JournalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = PeriodSerializer(
            data=request.query_params,
        )
        period.is_valid(raise_exception=True)

        journal = get_object_or_404(
            JournalSnapshot,
            user=request.user,
            **period.validated_data,
        )

        return Response(
            JournalSerializer(journal).data,
            headers={"Cache-Control": "no-store"},
        )


class JournalSyncView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    throttle_classes = [JournalSyncThrottle]

    def post(self, request):
        period = PeriodSerializer(
            data=request.data,
        )
        period.is_valid(raise_exception=True)

        try:
            journal = sync_journal(
                request.user,
                **period.validated_data,
            )
        except JournalSyncError as exc:
            return Response(
                {"detail": str(exc)},
                status=exc.status_code,
                headers={"Cache-Control": "no-store"},
            )

        return Response(
            JournalSerializer(journal).data,
            headers={"Cache-Control": "no-store"},
        )