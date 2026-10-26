import getpass
import json

from accounts.services.platonus_client import Result, hidden_input
from accounts.services.profile_client import ProfileCheck


def main():
    print("Проверка учебных данных Platonus.")
    print("ИИН, пароль и код вводятся скрыто.")

    iin = hidden_input("ИИН: ").strip()
    password = hidden_input("Пароль Platonus: ")

    with ProfileCheck() as client:
        try:
            login = client.login(iin, password)
        finally:
            iin = None
            password = None

        if login.status == "requires_code":
            code = hidden_input("Код из письма: ").strip()

            try:
                login = client.verify_code(code)
            finally:
                code = None

        if login.authenticated is not True:
            print(f"Вход не подтверждён: {login.status}")
            print(login.message)
            return 1

        print("Вход подтверждён. Получаем профиль и учебный план…")

        result = client.get_profile()

        if isinstance(result, Result):
            print(f"Профиль не получен: {result.status}")
            print(result.message)
            return 1

        profile = result["profile"]

        output = {
            "status": result["status"],
            "middle_name_found": bool(profile.get("middle_name")),
            "academic": profile.get("academic"),
            "warnings": result.get("warnings", []),
        }

    # Здесь сессия уже закрыта через контекстный менеджер.
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if client.logout_confirmed is not True:
        print("Platonus не подтвердил завершение сессии.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nПроверка отменена.")
    except getpass.GetPassWarning:
        print("Запусти проверку в обычном терминале со скрытым вводом.")
    except Exception as error:
        # Не выводим содержимое запросов и учётные данные.
        print(f"Проверка прервана. Тип ошибки: {type(error).__name__}")
        raise SystemExit(1)