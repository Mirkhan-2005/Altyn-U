import mimetypes
from rest_framework.response import Response
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from journal.models import JournalLessonRow

from .models import Teacher
from .serializers import (
    TeacherQuerySerializer,
    TeacherSerializer,
)

from .statistics import get_teacher_grade_statistics

class TeacherPagination(PageNumberPagination):
    page_size = 15


class TeacherListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = TeacherQuerySerializer(
            data=request.query_params,
        )
        query.is_valid(raise_exception=True)

        search = query.validated_data["search"]

        teachers = Teacher.objects.order_by(
            "display_name",
            "pk",
        )

        if search:
            teachers = teachers.filter(
                Q(display_name__icontains=search)
                | Q(full_name__icontains=search)
            )

        paginator = TeacherPagination()
        page = paginator.paginate_queryset(
            teachers,
            request,
            view=self,
        )

        teacher_ids = [teacher.pk for teacher in page]

        # Один запрос для предметов всех преподавателей
        # текущей страницы.
        subject_pairs = (
            JournalLessonRow.objects
            .filter(teacher_id__in=teacher_ids)
            .order_by()
            .values_list(
                "teacher_id",
                "subject__source_name",
            )
            .distinct()
        )

        subject_sets = {}

        for teacher_id, subject_name in subject_pairs:
            name = subject_name.strip()

            if name:
                subject_sets.setdefault(
                    teacher_id,
                    set(),
                ).add(name)

        subjects_by_teacher = {
            teacher_id: sorted(names, key=str.casefold)
            for teacher_id, names in subject_sets.items()
        }

        serializer = TeacherSerializer(
            page,
            many=True,
            context={
                "subjects_by_teacher": subjects_by_teacher,
                "statistics_by_teacher": (
                    get_teacher_grade_statistics(teacher_ids)
                ),
            },
        )

        response = paginator.get_paginated_response(
            serializer.data,
        )
        response["Cache-Control"] = "private, no-store"

        return response


class TeacherPhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        teacher = get_object_or_404(
            Teacher,
            pk=teacher_id,
        )

        if not teacher.photo:
            raise Http404("Фотография отсутствует.")

        try:
            photo_file = teacher.photo.open("rb")
        except FileNotFoundError:
            raise Http404(
                "Файл фотографии не найден."
            ) from None

        content_type = (
            mimetypes.guess_type(teacher.photo.name)[0]
            or "application/octet-stream"
        )

        response = FileResponse(
            photo_file,
            content_type=content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response
    

class TeacherDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        teacher = get_object_or_404(
            Teacher,
            pk=teacher_id,
        )

        # Только названия предметов и периоды.
        # Имена студентов и их оценки не возвращаем.
        records = (
            JournalLessonRow.objects
            .filter(teacher=teacher)
            .order_by(
                "subject__source_name",
                "-subject__snapshot__year",
                "subject__snapshot__term",
            )
            .values_list(
                "subject__source_name",
                "subject__snapshot__year",
                "subject__snapshot__term",
            )
            .distinct()
        )

        subjects = {}

        for name, year, term in records:
            name = name.strip()

            if name:
                subjects.setdefault(name, set()).add(
                    (year, term)
                )

        teaching = [
            {
                "subject": name,
                "periods": [
                    {
                        "year": year,
                        "term": term,
                    }
                    for year, term in sorted(
                        periods,
                        key=lambda item: (-item[0], item[1]),
                    )
                ],
            }
            for name, periods in sorted(
                subjects.items(),
                key=lambda item: item[0].casefold(),
            )
        ]

        serializer = TeacherSerializer(
            teacher,
            context={
                "subjects_by_teacher": {
                    teacher.pk: [
                        item["subject"]
                        for item in teaching
                    ],
                },
                "statistics_by_teacher": (
                    get_teacher_grade_statistics([teacher.pk])
                ),
            },
        )

        data = dict(serializer.data)
        data["teaching"] = teaching
        data["photo_source_url"] = teacher.photo_source_url

        return Response(
            data,
            headers={
                "Cache-Control": "private, no-store",
            },
        )
    
