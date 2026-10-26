from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request

from .academic_parser import (
    extract_middle_name,
    parse_academic_summary,
)
from .platonus_client import (
    BASE_URL,
    TIMEOUT_SECONDS,
    PlatonusCheck,
    Result,
)


MAX_ACADEMIC_BYTES = 4_000_000


class ProfileCheck(PlatonusCheck):
    def _get_academic_profile(self):
        headers = {
            "Accept": "text/html",
            "Accept-Language": "ru",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/v7/",
            "language": "1",
            "token": self._token,
        }

        if self._sid:
            headers["sid"] = self._sid

        request = Request(
            BASE_URL + "/indcur",
            headers=headers,
            method="GET",
        )

        # Используем текущую сессию: повторный вход не выполняем.
        try:
            with self._opener.open(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                if (
                    response.status != 200
                    or response.headers.get_content_type()
                    not in {"text/html", "application/xhtml+xml"}
                ):
                    return Result(
                        "academic_unexpected_response",
                        "Учебные данные не обновлены: "
                        "неожиданный ответ Platonus.",
                    )

                body = response.read(MAX_ACADEMIC_BYTES + 1)

        except HTTPError as exc:
            code = exc.code
            exc.close()

            return Result(
                "academic_http_error",
                f"Учебные данные не обновлены: HTTP {code}.",
            )

        except (URLError, TimeoutError, OSError, HTTPException):
            return Result(
                "academic_unavailable",
                "Учебные данные не обновлены: "
                "ошибка соединения с Platonus.",
            )

        if len(body) > MAX_ACADEMIC_BYTES:
            return Result(
                "academic_too_large",
                "Учебные данные не обновлены: "
                "ответ слишком большой.",
            )

        try:
            html = body.decode("utf-8-sig")
            return parse_academic_summary(html)

        except (UnicodeError, ValueError):
            return Result(
                "academic_parse_error",
                "Учебные данные не обновлены: "
                "не удалось разобрать учебный план.",
            )
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

        profile = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": text_field("fullName"),
            "gpa": gpa,
            "gpa_source": "student.GPA",
            "middle_name": None,
            "academic": None,
        }

        academic = self._get_academic_profile()

        if isinstance(academic, Result):
            # Ошибка учебного плана не отменяет получение имени и GPA.
            warnings.append(academic.message)

        else:
            full_name = academic.pop("full_name", None)

            profile["middle_name"] = extract_middle_name(
                full_name,
                first_name,
                last_name,
            )

            profile["academic"] = academic

        return {
            "status": "profile_loaded",
            "profile": profile,
            "warnings": warnings,
        }


