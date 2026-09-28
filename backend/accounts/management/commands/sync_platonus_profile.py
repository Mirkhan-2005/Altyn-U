import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.profile_api import ProfileSerializer
from accounts.services.profile_sync import SyncError, sync_profile


class Command(BaseCommand):
    help = "Обновить профиль через сохранённое подключение Platonus"

    def handle(self, *args, **options):
        iin = input(
            "ИИН зарегистрированного пользователя Altyn: "
        ).strip()

        user = get_user_model().objects.filter(iin=iin).first()

        if user is None:
            raise CommandError("Пользователь Altyn не найден.")

        self.stdout.write("Обновляем профиль из Platonus…")

        try:
            profile = sync_profile(user)
        except SyncError as exc:
            raise CommandError(str(exc)) from None

        self.stdout.write(
            json.dumps(
                ProfileSerializer(profile).data,
                ensure_ascii=False,
                indent=2,
            )
        )