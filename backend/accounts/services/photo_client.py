import base64
import binascii
import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

from PIL import Image, UnidentifiedImageError

from .platonus_client import BASE_URL, TIMEOUT_SECONDS, Result
from .profile_client import ProfileCheck


MAX_PHOTO_BYTES = 5_000_000
MAX_PHOTO_RESPONSE_BYTES = 7_000_000
MAX_PHOTO_PIXELS = 16_000_000


class PhotoCheck(ProfileCheck):
    def get_photo(self):
        if self._closed or not self._token:
            return Result(
                "not_authenticated",
                "Сначала выполните вход в Platonus.",
            )

        role = self._role_result or self.check_role()

        if role.is_student is not True:
            return Result(
                "photo_unavailable",
                "Роль студента не подтверждена.",
            )

        headers = {
            "Accept": "text/plain, */*",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/v7/",
            "language": "1",
            "token": self._token,
        }

        if self._sid:
            headers["sid"] = self._sid

        request = Request(
            BASE_URL + "/rest/img/profilePicture",
            headers=headers,
            method="GET",
        )

        # Используем ту же сессию, в которой выполнен вход.
        try:
            with self._opener.open(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                body = response.read(
                    MAX_PHOTO_RESPONSE_BYTES + 1
                )

        except HTTPError as exc:
            code = exc.code
            exc.close()

            return Result(
                "photo_http_error",
                f"Фотография не получена. HTTP {code}.",
            )

        except (URLError, TimeoutError, OSError):
            return Result(
                "photo_unavailable",
                "Не удалось загрузить фотографию из Platonus.",
            )

        if len(body) > MAX_PHOTO_RESPONSE_BYTES:
            return Result(
                "photo_too_large",
                "Ответ с фотографией превышает допустимый размер.",
            )

        # Преобразуем Base64 в байты изображения.
        try:
            text = body.decode("utf-8").strip()

            if not text or text == "null":
                return Result(
                    "photo_missing",
                    "Platonus вернул пустую фотографию.",
                )

            # Поддерживаем также строку в JSON-кавычках.
            if text.startswith('"'):
                text = json.loads(text)

                if not isinstance(text, str):
                    raise ValueError()

            # Поддерживаем data:image/...;base64,...
            if text.startswith("data:"):
                prefix, text = text.split(",", 1)

                if (
                    not prefix.startswith("data:image/")
                    or not prefix.endswith(";base64")
                ):
                    raise ValueError()

            image_bytes = base64.b64decode(
                "".join(text.split()),
                validate=True,
            )

        except (ValueError, UnicodeError, binascii.Error):
            return Result(
                "unexpected_photo",
                "Ответ Platonus не удалось прочитать как Base64-фотографию.",
            )

        if not image_bytes:
            return Result(
                "photo_missing",
                "Platonus вернул пустую фотографию.",
            )

        if len(image_bytes) > MAX_PHOTO_BYTES:
            return Result(
                "photo_too_large",
                "Размер фотографии превышает 5 МБ.",
            )

        # Проверяем формат изображения и определяем расширение.
        try:
            with Image.open(BytesIO(image_bytes)) as picture:
                extension = {
                    "JPEG": ".jpg",
                    "PNG": ".png",
                    "WEBP": ".webp",
                }.get(picture.format)

                if extension is None:
                    return Result(
                        "unsupported_photo",
                        "Формат фотографии не поддерживается.",
                    )

                if picture.width * picture.height > MAX_PHOTO_PIXELS:
                    return Result(
                        "photo_too_large",
                        "Разрешение фотографии слишком большое.",
                    )

                picture.verify()

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            SyntaxError,
            Image.DecompressionBombError,
        ):
            return Result(
                "invalid_photo",
                "Не удалось подтвердить формат файла фотографии.",
            )

        return image_bytes, extension


