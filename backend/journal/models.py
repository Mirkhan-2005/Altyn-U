from django.conf import settings
from django.db import models


class JournalSnapshot(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journals",
    )
    year = models.PositiveSmallIntegerField()
    term = models.SmallIntegerField()

    data = models.JSONField(default=dict, blank=True)

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_sync_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    sync_status = models.CharField(
        max_length=16,
        default="pending",
    )
    sync_message = models.TextField(blank=True)

    # Защищает от одновременной записи нескольких обновлений.
    sync_token = models.UUIDField(
        null=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "year", "term"],
                name="unique_journal_user_period",
            ),
        ]
        ordering = ["-year", "term"]