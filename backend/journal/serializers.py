from rest_framework import serializers

from .models import JournalSnapshot


class PeriodSerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2000,
        max_value=2100,
    )
    term = serializers.IntegerField(
        min_value=-20,
        max_value=20,
    )

    def validate_term(self, value):
        if value == 0:
            raise serializers.ValidationError(
                "Период не может быть равен 0."
            )

        return value


class JournalSerializer(serializers.ModelSerializer):
    has_data = serializers.SerializerMethodField()

    class Meta:
        model = JournalSnapshot

        fields = (
            "year",
            "term",
            "has_data",
            "data",
            "last_synced_at",
            "last_sync_attempt_at",
            "sync_status",
            "sync_message",
        )

        read_only_fields = fields

    def get_has_data(self, obj):
        return obj.last_synced_at is not None