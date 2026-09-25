from .platonus_client import PlatonusCheck


def verify_student(iin: str, password: str):
    with PlatonusCheck() as checker:
        result = checker.login(iin, password)

        if result.authenticated is not True:
            return result

        result = checker.check_role()

        if result.is_student is not True:
            return result

        return checker.check_study_status()