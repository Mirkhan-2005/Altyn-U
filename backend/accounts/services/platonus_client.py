"""Проверка входа, роли и статуса обучения в Platonus ЕНУ. Python 3.10+.

Запуск в терминале: python platonus_check.py
ИИН вводится обычным текстом; пароль и код вводятся скрыто.
Используйте для своей учётной записи или по запросу её владельца.

Основание: https://edu.enu.kz/jscripts/login.js и публичный код /v7/
(main.ad6af26df0ee7dbb.js, personType2, studentState, getStudentState;
публичный код повторно проверен 20.09.2026).
Это внутренний интерфейс сайта, он может измениться. Пользователь подтвердил
успешный вход и проверку роли предыдущей версией; новый запрос статуса обучения
ещё требует проверки на реальном аккаунте. Пароли, токены, cookies и полные ответы сервера
не записываются в файлы и не выводятся. Одна попытка входа и не более
одной попытки ввода кода; автоматических повторов нет.

authenticated=True подтверждает вход; is_student=True — текущую роль студента.
Проверяется роль активной сессии, а не перечень всех доступных пользователю ролей.
active_student=True — роль студента и статус STUDENT (1) подтверждены сервером.
active_student=False — получен другой известный статус обучения.
active_student=None — статус не проверен или не удалось его подтвердить.
Академический отпуск выводится отдельно и не считается статусом STUDENT;
решение о допуске таких пользователей на сайт принимается отдельно.
Статус запрашивается только для personID, возвращённого текущей сессией.
Код завершения 0 означает подтверждённый active_student=True.
Для сайта нужны ограничение попыток и одноразовое подтверждение на backend.
"""

from __future__ import annotations

import getpass
import http.cookiejar
import json
import re
import socket
import sys
import warnings
from dataclasses import asdict, dataclass, replace
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


BASE_URL = "https://edu.enu.kz"
TIMEOUT_SECONDS = 25
MAX_RESPONSE_BYTES = 1_000_000
# personType2 из публичного кода Platonus /v7/.
PERSON_TYPES = {
    0: ("none", "Роль не выбрана"),
    1: ("student", "Студент"),
    2: ("tutor", "Преподаватель"),
    3: ("employee", "Сотрудник"),
    38: ("user", "Пользователь"),
    41: ("applicant", "Абитуриент"),
}
# studentState из того же публичного кода Platonus /v7/.
STUDY_STATES = {
    1: ("studying", "Обучается"),
    2: ("applicant", "Абитуриент"),
    3: ("deducted", "Отчислен"),
    4: ("graduated", "Выпускник"),
    5: ("academic_leave", "Академический отпуск"),
}


@dataclass(frozen=True)
class Result:
    status: str
    message: str
    authenticated: bool = False
    active_student: bool | None = None
    person_type: int | None = None
    role: str | None = None
    is_student: bool | None = None
    role_check_error: str | None = None
    study_status_verified: bool = False
    study_status_code: int | None = None
    study_status: str | None = None
    study_status_name: str | None = None
    study_check_error: str | None = None


class NoRedirects(HTTPRedirectHandler):
    """Не пересылаем пароль или токен на другой адрес при редиректе."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PlatonusCheck:
    def __init__(self):
        self._cookies = http.cookiejar.CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookies), NoRedirects())
        self._token = None
        self._sid = None
        self._challenge = None
        self._login_attempted = False
        self._code_attempted = False
        self._closed = False
        self._role_result: Result | None = None
        self.logout_confirmed: bool | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _post(self, path, payload, token=None):
        return self._request("POST", path, payload, token)

    def _request(self, method, path, payload=None, token=None):
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json",
            "language": "1",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
            "Accept-Language": "ru",
        }
        if token:
            headers["token"] = token
            if self._sid:
                headers["sid"] = self._sid
        request = Request(
            BASE_URL + path,
            data=json.dumps(payload).encode("utf-8") if method == "POST" else None,
            headers=headers,
            method=method,
        )
        try:
            with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    return Result("unexpected_response", "Неожиданный ответ Platonus.")
                if path == "/rest/api/logout/":
                    return {}
                data = json.loads(body)
                if not isinstance(data, dict):
                    return Result("unexpected_response", "Неожиданный формат ответа.")
                return data
        except HTTPError as exc:
            status_code = exc.code
            exc.close()
            if status_code == 429:
                return Result(
                    "rate_limited", "Platonus ограничил попытки. Повторите позже."
                )
            if status_code == 401:
                return Result(
                    "authentication_rejected", "Platonus отклонил авторизацию."
                )
            if status_code == 403:
                return Result(
                    "access_denied",
                    "Platonus запретил запрос; это не доказывает отсутствие аккаунта.",
                )
            if 300 <= status_code < 400:
                return Result(
                    "redirect_blocked",
                    "Platonus изменил адрес входа. Нужна проверка интеграции.",
                )
            if status_code >= 500:
                return Result("unavailable", "Сервис Platonus временно недоступен.")
            return Result(
                "request_rejected", "Запрос отклонён. Учётная запись не подтверждена."
            )
        except (URLError, TimeoutError, socket.timeout, OSError):
            return Result(
                "unavailable", "Не удалось безопасно подключиться к Platonus."
            )
        except (ValueError, UnicodeError):
            return Result(
                "unexpected_response",
                "Platonus вернул неожиданный ответ; вход не подтверждён.",
            )

    def _interpret(self, data, *, allow_challenge):
        if isinstance(data, Result):
            return data
        status = data.get("login_status")
        if status == "success":
            token = data.get("auth_token")
            if (
                not isinstance(token, str)
                or not token.strip()
                or "\r" in token
                or "\n" in token
            ):
                return Result(
                    "unexpected_response",
                    "Ответ не содержит ожидаемого подтверждения сессии.",
                )
            self._token = token
            sid = data.get("sid")
            if (
                type(sid) in (str, int)
                and "\r" not in str(sid)
                and "\n" not in str(sid)
            ):
                self._sid = str(sid)
            self._challenge = None
            return Result(
                "authenticated",
                "Вход подтверждён. Роль ещё не проверена.",
                authenticated=True,
            )
        if status == "verificationCode" and allow_challenge:
            challenge = data.get("challengeId")
            if (
                data.get("verifyStatus") == "EMAIL_SENT"
                and isinstance(challenge, str)
                and challenge
            ):
                self._challenge = challenge
                return Result(
                    "requires_code",
                    "Platonus запросил код из письма. Вход ещё не завершён.",
                )
            return Result(
                "verification_unavailable", "Не удалось начать подтверждение кодом."
            )
        if data.get("verifyStatus") == "ATTEMPT_COUNT_LIMIT":
            return Result("rate_limited", "Platonus ограничил попытки подтверждения.")
        # Не угадываем значения недокументированных ошибок и не выводим
        # произвольный response.message, который может содержать личные данные.
        return Result(
            "not_confirmed",
            "Вход не подтверждён. Это не означает, что аккаунта не существует.",
        )

    def login(self, iin: str, password: str) -> Result:
        if self._closed or self._login_attempted:
            return Result(
                "attempt_used", "Для этой проверки попытка входа уже завершена."
            )
        if not re.fullmatch(r"[0-9]{12}", iin) or not password:
            return Result("invalid_input", "Нужны ИИН из 12 цифр и непустой пароль.")
        self._login_attempted = True
        # Структура взята из loginWithoutEds() официальной страницы входа.
        payload = {
            "login": None,
            "iin": iin,
            "icNumber": iin,
            "password": password,
            "authForDeductedStudentsAndGraduates": "false",
        }
        try:
            return self._interpret(
                self._post("/rest/api/login", payload), allow_challenge=True
            )
        finally:
            payload.clear()

    def verify_code(self, code: str) -> Result:
        if self._closed or not self._challenge or self._code_attempted:
            return Result(
                "no_pending_challenge", "Нет доступного запроса на подтверждение."
            )
        if not re.fullmatch(r"[0-9]{6}", code):
            return Result("invalid_input", "Код должен содержать 6 цифр.")
        self._code_attempted = True
        challenge, self._challenge = self._challenge, None
        return self._interpret(
            self._post(
                "/rest/api/verifyCode", {"challengeId": challenge, "code": code}
            ),
            allow_challenge=False,
        )

    def check_role(self) -> Result:
        """Один запрос текущей роли; не читает профиль, оценки и статус обучения."""
        self._role_result = self._check_role()
        return self._role_result

    def _check_role(self) -> Result:
        if self._closed or not self._token:
            return Result("not_authenticated", "Сначала выполните вход в Platonus.")
        data = self._request("GET", "/rest/api/person/personType", token=self._token)
        if isinstance(data, Result):
            return Result(
                "role_unverified",
                "Вход был подтверждён, но получить роль не удалось.",
                authenticated=True,
                role_check_error=data.status,
            )
        person_type = data.get("personType")
        # Не принимаем True за 1 и не угадываем изменившийся формат ответа.
        if (
            type(person_type) is not int
            or person_type not in PERSON_TYPES
            or person_type == 0
        ):
            return Result(
                "role_unverified",
                "Вход подтверждён, но роль не распознана.",
                authenticated=True,
                person_type=person_type if type(person_type) is int else None,
                role_check_error="unexpected_role",
            )
        role, label = PERSON_TYPES[person_type]
        return Result(
            "role_verified",
            f"Текущая роль: {label}. Статус обучения не проверялся.",
            authenticated=True,
            person_type=person_type,
            role=role,
            is_student=person_type == 1,
        )

    def check_study_status(self) -> Result:
        """Проверяет статус только владельца текущей сессии с ролью студента."""
        if self._closed or not self._token:
            return Result("not_authenticated", "Сначала выполните вход в Platonus.")
        role_result = self._role_result or self.check_role()
        if role_result.is_student is not True:
            return replace(
                role_result,
                message=role_result.message
                + " Проверка статуса обучения пропущена: роль студента не подтверждена.",
            )

        def unverified(error):
            return replace(
                role_result,
                status="study_status_unverified",
                message="Вход и роль студента подтверждены, но статус обучения установить не удалось.",
                study_check_error=error,
            )

        # Получаем ID от сервера для текущей сессии, а не из введённого ИИН.
        person = self._request("GET", "/rest/api/person/personID", token=self._token)
        if isinstance(person, Result):
            return unverified("person_id_" + person.status)
        person_id = person.get("personID")
        if type(person_id) is not int or person_id <= 0:
            return unverified("unexpected_person_id")
        data = self._request(
            "GET",
            f"/rest/student/studentState/{person_id}",
            token=self._token,
        )
        if isinstance(data, Result):
            return unverified(data.status)
        # isStudent здесь — числовой код статуса (1–5), а не булево поле.
        state = data.get("isStudent")
        if type(state) is not int or state not in STUDY_STATES:
            return unverified("unexpected_study_status")
        name, label = STUDY_STATES[state]
        return replace(
            role_result,
            status="student_verified" if state == 1 else "study_status_verified",
            message=f"Текущая роль: Студент. Статус обучения: {label}.",
            active_student=state == 1,
            study_status_verified=True,
            study_status_code=state,
            study_status=name,
            study_status_name=label,
        )

    def close(self):
        if self._closed:
            return
        try:
            if self._token:
                outcome = self._post("/rest/api/logout/", {}, token=self._token)
                self.logout_confirmed = not isinstance(outcome, Result)
        finally:
            self._token = None
            self._sid = None
            self._challenge = None
            self._role_result = None
            self._cookies.clear()
            self._closed = True


def hidden_input(prompt):
    # Если терминал не умеет скрывать ввод, останавливаемся вместо отображения секрета.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main():
    if not sys.stdin.isatty():
        print("Запустите скрипт в обычном терминале VS Code / PowerShell.")
        return 2
    print("\nПроверка входа в Platonus ЕНУ — https://edu.enu.kz")
    print("После каждого ввода нажимайте Enter. Для отмены нажмите Ctrl+C.")
    try:
        print("\nШАГ 1. Введите свой ИИН: 12 цифр без пробелов.")
        iin = input("Ваш ИИН: ").strip()
        while not re.fullmatch(r"[0-9]{12}", iin):
            print("В ИИН должно быть ровно 12 цифр. Проверьте ввод.")
            iin = input("Ваш ИИН: ").strip()

        print("\nШАГ 2. Введите пароль, с которым вы входите в Platonus.")
        print("При вводе пароля НЕ видны ни символы, ни звёздочки — это нормально.")
        print("Напечатайте пароль и нажмите Enter.")
        password = hidden_input("Ваш пароль Platonus: ")
        while not password:
            print("Вы не ввели пароль. Напечатайте его и нажмите Enter.")
            password = hidden_input("Ваш пароль Platonus: ")

        print("\nПроверяем данные в Platonus. Подождите ответа…", flush=True)
        with PlatonusCheck() as checker:
            try:
                result = checker.login(iin, password)
            finally:
                password = None
                iin = None
            if result.status == "requires_code":
                print("\nШАГ 3. Platonus запросил дополнительное подтверждение.")
                print("Откройте свою почту и найдите письмо с кодом от Platonus.")
                print("Введите 6 цифр из письма и нажмите Enter. Ввод кода скрыт.")
                code = hidden_input("Код подтверждения: ").strip()
                try:
                    result = checker.verify_code(code)
                finally:
                    code = None
            if result.authenticated:
                print("Вход подтверждён. Проверяем текущую роль…", flush=True)
                result = checker.check_role()
            if result.is_student is True:
                print(
                    "Роль студента подтверждена. Проверяем статус обучения…", flush=True
                )
                result = checker.check_study_status()
        output = asdict(result)
        output["logout_confirmed"] = checker.logout_confirmed
        print("\nРезультат: " + result.message)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if checker.logout_confirmed is False:
            print(
                "Сервер не подтвердил завершение сессии; локальные данные сессии удалены."
            )
        return 0 if result.active_student is True else 1
    except (KeyboardInterrupt, EOFError):
        print("\nПроверка отменена.")
        return 2
    except getpass.GetPassWarning:
        print(
            "Терминал не поддерживает скрытый ввод. Используйте PowerShell или терминал VS Code."
        )
        return 2
    except Exception:
        # Не печатаем traceback: он может содержать параметры запроса.
        print("Проверка прервана из-за неожиданной ошибки; вход не подтверждён.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
