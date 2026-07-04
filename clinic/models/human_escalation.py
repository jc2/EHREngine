import uuid

from django.db import models
from django.utils import timezone

from .patient import Patient


def _escalation_public_id():
    return uuid.uuid4().hex


class EscalationStatus(models.TextChoices):
    NEW = "NEW", "New"
    RESOLVED = "RESOLVED", "Resolved"


class HumanEscalation(models.Model):
    public_id = models.CharField(
        max_length=32, unique=True, default=_escalation_public_id, editable=False
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="escalations",
        to_field="code",
        null=True,
        blank=True,
    )
    reported_name = models.CharField(max_length=200)
    reported_phone = models.CharField(max_length=20, db_index=True)
    reported_identification_number = models.CharField(max_length=50, db_index=True)
    initial_intent = models.TextField()
    failure_reason = models.TextField()
    agent_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=EscalationStatus.choices,
        default=EscalationStatus.NEW,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Escalation {self.public_id} ({self.status})"

    @property
    def view_url(self):
        return f"/escalations/{self.public_id}/"

    def save(self, *args, **kwargs):
        if self.pk:
            previous_status = (
                HumanEscalation.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
        else:
            previous_status = None

        if self.status == EscalationStatus.RESOLVED and previous_status != EscalationStatus.RESOLVED:
            self.resolved_at = timezone.now()
        elif self.status == EscalationStatus.NEW and previous_status == EscalationStatus.RESOLVED:
            self.resolved_at = None

        super().save(*args, **kwargs)
