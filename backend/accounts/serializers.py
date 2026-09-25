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
    )

    save_platonus_credentials = serializers.BooleanField(
        required=True,
        write_only=True,
    )

    def validate_iin(self, value):
        if not re.fullmatch(r"[0-9]{12}", value):
            raise serializers.ValidationError(
                "ИИН должен содержать ровно 12 цифр."
            )

        return value

    def validate_save_platonus_credentials(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Подтвердите согласие на сохранение подключения Platonus."
            )

        return value


class RegistrationCompleteSerializer(serializers.Serializer):
    registration_token = StrictStringField(
        min_length=43,
        max_length=43,
        trim_whitespace=False,
        write_only=True,
    )

    password = StrictStringField(
        min_length=8,
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )

    password_confirm = StrictStringField(
        min_length=8,
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )

    def validate_registration_token(self, value):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
            raise serializers.ValidationError(
                "Некорректное подтверждение регистрации."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Пароли не совпадают."}
            )

        return attrs