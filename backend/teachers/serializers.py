from rest_framework import serializers

from .models import Teacher


class TeacherQuerySerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        default="",
    )


class TeacherSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = (
            "id",
            "display_name",
            "full_name",
            "subjects",
            "photo_url",
            "photo_updated_at",
        )

    def get_subjects(self, obj):
        return self.context["subjects_by_teacher"].get(
            obj.pk,
            [],
        )

    def get_photo_url(self, obj):
        if not obj.photo:
            return None

        return f"/api/teachers/{obj.pk}/photo/"