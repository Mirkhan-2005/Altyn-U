from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import PendingRegistration


class Command(BaseCommand):
    help = "Удаляет просроченные незавершённые регистрации."

    def handle(self, *args, **options):
        deleted, _ = PendingRegistration.objects.filter(
            expires_at__lte=timezone.now(),
        ).delete()

        self.stdout.write(
            f"Удалено записей: {deleted}"
        )