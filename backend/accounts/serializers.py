import re

from rest_framework import serializers


class StrictStringField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(
                "Значение должно быть строкой."
            )

        return super().to_internal_value(data)


class PlatonusVerifySerializer(serializers.Serializer):
    iin = StrictStringField(
        min_length=12,
        max_length=12,
        trim_whitespace=False,
    )

    platonus_password = StrictStringField(
        max_length=256,
        trim_whitespace=False,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_iin(self, value):
        if not re.fullmatch(r"[0-9]{12}", value):
            raise serializers.ValidationError(
                "ИИН должен содержать ровно 12 цифр."
            )

        return value