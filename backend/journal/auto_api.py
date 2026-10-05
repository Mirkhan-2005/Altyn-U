from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import StudentProfile

from .models import JournalImportState, JournalSnapshot
from .serializers import JournalSerializer, PeriodSerializer
from .services.import_queue import (
    import_active,
    is_current,
    is_fresh,
    queue_journal_import,
)


def page_state(user, year, term):
    now = timezone.now()
    current = is_current(year, term)

    journal = JournalSnapshot.objects.filter(
        user=user,
        year=year,
        term=term,
    ).first()

    if journal is None:
        # Несохранённый объект нужен только для ответа API.
        journal = JournalSnapshot(
            user=user,
            year=year,
            term=term,
        )

    state = JournalImportState.objects.filter(
        user=user,
    ).first()

    report = state.report if state else {}

    missing = journal.last_synced_at is None

    needs_data = (
        missing
        or (current and not is_fresh(journal, now))
    )

    pending = bool(
        journal.sync_token
        and journal.last_sync_attempt_at
        and journal.last_sync_attempt_at
        > now - timedelta(minutes=5)
    )

    relevant = (
        current or not report.get("current_only", False)
    )

    period_error = next(
        (
            item.get("message", "")
            for item in report.get("errors", [])
            if (
                item.get("year"),
                item.get("term"),
            ) == (year, term)
        ),
        "",
    )

    if needs_data and relevant and not period_error:
        pending = pending or import_active(state, now)

    # У нового пользователя сначала загружается профиль.
    if missing:
        pending = pending or StudentProfile.objects.filter(
            user=user,
            sync_status__in=["queued", "syncing"],
            last_sync_attempt_at__gt=(
                now - timedelta(minutes=10)
            ),
        ).exists()

    message = ""

    if needs_data and not pending:
        message = period_error

        if not message and state and relevant:
            message = state.message

        if not message and missing:
            message = (
                "Журнал пока не загружен. "
                "Можно обновить его вручную."
            )

    result = dict(JournalSerializer(journal).data)

    result.update(
        is_current=current,
        refresh_pending=bool(pending),
        auto_message=message,
    )

    return result


class JournalAutoSyncView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request):
        data = request.query_params

        # Без фильтров открываем настроенный текущий период.
        if not data:
            data = {
                "year": settings.ALTYN_CURRENT_YEAR,
                "term": settings.ALTYN_CURRENT_TERM,
            }

        serializer = PeriodSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(
            page_state(
                request.user,
                **serializer.validated_data,
            ),
            headers={"Cache-Control": "no-store"},
        )

    def post(self, request):
        serializer = PeriodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        period = serializer.validated_data

        if is_current(**period):
            queue_journal_import(
                request.user,
                current_only=True,
            )

        return Response(
            page_state(request.user, **period),
            headers={"Cache-Control": "no-store"},
        )