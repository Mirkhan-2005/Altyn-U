from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import StudentProfile


class RankingQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        max_value=1000000,
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=50,
    )
    course = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=99,
    )
    program = serializers.CharField(
        required=False,
        max_length=32,
    )


class RankingStudentSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user_id")
    rank = serializers.IntegerField()
    full_name = serializers.CharField()
    course = serializers.IntegerField(allow_null=True)
    education_program = serializers.CharField()
    education_program_code = serializers.CharField()
    gpa = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        coerce_to_string=True,
    )
    gpa_updated_at = serializers.DateTimeField(allow_null=True)
    is_me = serializers.BooleanField()


class RankingThrottle(UserRateThrottle):
    scope = "student_ranking"
    rate = "60/min"


class StudentRankingView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [RankingThrottle]
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(
            request, response, *args, **kwargs
        )
        response["Cache-Control"] = "private, no-store"
        return response

    def get(self, request):
        query = RankingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        # Один запрос: только поля, необходимые для рейтинга.
        # Подходит для текущего объёма — порядка сотни студентов.
        students = list(
            StudentProfile.objects.filter(
                user__is_active=True,
                user__is_staff=False,
                user__is_superuser=False,
                student_status="active",
                gpa__isnull=False,
            )
            .order_by("-gpa", "user_id")
            .values(
                "user_id",
                "user__first_name",
                "user__last_name",
                "middle_name",
                "course",
                "education_program",
                "education_program_code",
                "gpa",
                "gpa_updated_at",
            )
        )

        # Варианты фильтров для будущих выпадающих списков.
        courses = sorted({
            row["course"]
            for row in students
            if row["course"] is not None
        })

        programs = {}

        for row in students:
            code = row["education_program_code"]

            if code:
                programs.setdefault(
                    code,
                    row["education_program"] or code,
                )

        course = params.get("course")
        program = params.get("program")

        filtered = [
            row
            for row in students
            if (course is None or row["course"] == course)
            and (
                program is None
                or row["education_program_code"] == program
            )
        ]

        # Места рассчитываем до разбиения на страницы.
        # Одинаковый GPA: места 1, 2, 2, 4.
        previous_gpa = None
        rank = 0
        my_result = None

        for position, row in enumerate(filtered, start=1):
            if row["gpa"] != previous_gpa:
                rank = position
                previous_gpa = row["gpa"]

            row["rank"] = rank

            row["full_name"] = " ".join(
                part.strip()
                for part in (
                    row["user__last_name"],
                    row["user__first_name"],
                    row["middle_name"],
                )
                if part and part.strip()
            ) or "ФИО не загружено"

            row["is_me"] = row["user_id"] == request.user.pk

            if row["is_me"]:
                my_result = row

        count = len(filtered)
        page = params["page"]
        page_size = params["page_size"]

        total_pages = max(
            1,
            (count + page_size - 1) // page_size,
        )

        if page > total_pages:
            raise NotFound("Такой страницы рейтинга нет.")

        start = (page - 1) * page_size

        return Response({
            "count": count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next_page": (
                page + 1 if page < total_pages else None
            ),
            "previous_page": (
                page - 1 if page > 1 else None
            ),
            "filters": {
                "course": course,
                "program": program,
            },
            "available_filters": {
                "courses": courses,
                "programs": [
                    {
                        "code": code,
                        "name": programs[code],
                    }
                    for code in sorted(programs)
                ],
            },
            "my_result": (
                RankingStudentSerializer(my_result).data
                if my_result is not None
                else None
            ),
            "results": RankingStudentSerializer(
                filtered[start:start + page_size],
                many=True,
            ).data,
        })