from decimal import Decimal, InvalidOperation

from .platonus_client import PlatonusCheck, Result


class ProfileCheck(PlatonusCheck):
    def get_profile(self):
        if self._closed or not self._token:
            return Result(
                "not_authenticated",
                "Сначала выполните вход в Platonus.",
            )

        role = self._role_result or self.check_role()

        if role.is_student is not True:
            return Result(
                "profile_unavailable",
                "Роль студента не подтверждена.",
            )

        # Получаем ID владельца текущей сессии.
        person = self._request(
            "GET",
            "/rest/api/person/personID",
            token=self._token,
        )

        if isinstance(person, Result):
            return person

        person_id = person.get("personID")

        if type(person_id) is not int or person_id <= 0:
            return Result(
                "unexpected_person_id",
                "Не удалось определить владельца сессии.",
            )

        # Запрашиваем профиль только этого пользователя.
        data = self._request(
            "GET",
            f"/rest/student/studentInfo/{person_id}/ru",
            token=self._token,
        )

        if isinstance(data, Result):
            return data

        student = data.get("student")

        if not isinstance(student, dict):
            return Result(
                "unexpected_profile",
                "В ответе отсутствует объект student.",
            )

        if (
            type(student.get("personID")) is not int
            or student["personID"] != person_id
        ):
            return Result(
                "profile_identity_mismatch",
                "Профиль не соответствует владельцу сессии.",
            )

        def text_field(key):
            value = student.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

            return None

        first_name = text_field("firstname")

        if first_name is None:
            return Result(
                "unexpected_profile",
                "Поле firstname отсутствует или имеет другой формат.",
            )

        warnings = []

        # Название поля фамилии проверяем этим запуском.
        last_name = text_field("lastname")

        if last_name is None:
            warnings.append(
                "Поле lastname отсутствует или пустое. "
                "Нужно уточнить название поля фамилии."
            )

        gpa = None
        raw_gpa = student.get("GPA")

        if (
            type(raw_gpa) in (str, int, float)
            and len(str(raw_gpa)) <= 32
        ):
            try:
                number = Decimal(str(raw_gpa))

                if (
                    number.is_finite()
                    and Decimal("0") <= number <= Decimal("4")
                ):
                    gpa = str(number)

            except InvalidOperation:
                pass

        if gpa is None:
            warnings.append(
                "GPA отсутствует или не является числом от 0 до 4."
            )

        return {
            "status": "profile_loaded",
            "profile": {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": text_field("fullName"),
                "gpa": gpa,
                "gpa_source": "student.GPA",
            },
            "warnings": warnings,
        }


