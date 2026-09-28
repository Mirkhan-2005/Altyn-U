from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.views.decorators.debug import sensitive_variables

from accounts.models import PlatonusConnection
from accounts.services.platonus_client import (
    BASE_URL,
    TIMEOUT_SECONDS,
    PlatonusCheck,
    Result,
)

from .parser import JournalError, parse_journal


MAX_HTML = 5_000_000


class JournalSyncError(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code


def fetch_html(client, student_id, year, term):
    query = urlencode({
        "studentID": student_id,
        "year": year,
        "term": term,
    })

    headers = {
        "Accept": "text/html",
        "Accept-Encoding": "identity",
        "Accept-Language": "ru",
        "language": "1",
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/v7/",
        "token": client._token,
    }

    if client._sid:
        headers["sid"] = client._sid

    request = Request(
        BASE_URL + "/current_progress_gradebook_student?" + query,
        headers=headers,
        method="GET",
    )

    try:
        with client._opener.open(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            content_type = response.headers.get_content_type()
            encoding = response.headers.get_content_charset() or "utf-8"
            body = response.read(MAX_HTML + 1)

    except HTTPError as exc:
        code = exc.code
        exc.close()

        raise JournalSyncError(
            f"Platonus не отдал журнал: HTTP {code}."
        ) from None

    except (URLError, TimeoutError, OSError):
        raise JournalSyncError(
            "Не удалось получить журнал из Platonus."
        ) from None

    if len(body) > MAX_HTML:
        raise JournalSyncError(
            "Страница журнала превышает 5 МБ."
        )

    if content_type not in {"text/html", "application/xhtml+xml"}:
        raise JournalSyncError(
            "Platonus вернул неожиданный формат журнала."
        )

    try:
        return body.decode(encoding)
    except (UnicodeError, LookupError):
        raise JournalSyncError(
            "Не удалось прочитать кодировку журнала."
        ) from None


@sensitive_variables()
def download_journal(user, year, term):
    connection = PlatonusConnection.objects.filter(
        user=user,
    ).first()

    if connection is None:
        raise JournalSyncError(
            "Подключение Platonus отсутствует.",
            409,
        )

    try:
        cipher = Fernet(
            settings.PLATONUS_ENCRYPTION_KEY.encode("ascii")
        )

        password = cipher.decrypt(
            connection.encrypted_password.encode("ascii")
        ).decode("utf-8")

    except (InvalidToken, ValueError, UnicodeError, AttributeError):
        raise JournalSyncError(
            "Не удалось расшифровать подключение Platonus.",
            500,
        ) from None

    with PlatonusCheck() as client:
        try:
            login = client.login(user.iin, password)
        finally:
            password = None

        if login.authenticated is not True:
            if login.status == "requires_code":
                raise JournalSyncError(
                    "Platonus запросил код. Требуется повторное подключение.",
                    409,
                )

            if login.status in {
                "authentication_rejected",
                "not_confirmed",
            }:
                raise JournalSyncError(
                    "Platonus не подтвердил вход. Проверьте подключение.",
                    409,
                )

            raise JournalSyncError(
                "Вход в Platonus сейчас не подтверждён. Повторите позже."
            )

        role = client.check_role()

        if role.is_student is not True:
            raise JournalSyncError(
                "Роль студента не подтверждена.",
                403 if role.is_student is False else 503,
            )

        study = client.check_study_status()

        if (
            study.study_status_verified is not True
            or study.active_student is not True
        ):
            raise JournalSyncError(
                "Статус «Обучается» не подтверждён.",
                403 if study.active_student is False else 503,
            )

        # ID получаем из собственной сессии пользователя.
        person = client._request(
            "GET",
            "/rest/api/person/personID",
            token=client._token,
        )

        if isinstance(person, Result):
            raise JournalSyncError(
                "Не удалось определить владельца сессии."
            )

        student_id = person.get("personID")

        if type(student_id) is not int or student_id <= 0:
            raise JournalSyncError(
                "Некорректный ID владельца сессии."
            )

        html = fetch_html(
            client,
            student_id,
            year,
            term,
        )

        try:
            data = parse_journal(
                html,
                year,
                term,
                expected_student_id=student_id,
            )
        except JournalError as exc:
            raise JournalSyncError(str(exc), 502) from None

    warning = (
        ""
        if client.logout_confirmed is True
        else "Platonus не подтвердил завершение сессии."
    )

    return data, warning