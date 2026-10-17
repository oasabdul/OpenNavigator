from __future__ import annotations

import uuid

from django.db import models


class TripPlanRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    context = models.JSONField()

    class Meta:
        db_table = "trip_plans"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Trip plan {self.id}"
