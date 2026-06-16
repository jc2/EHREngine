from django.db import models

from .prescription import Prescription


class RefillStatus(models.TextChoices):
    APPROVED = "APPROVED", "Approved"
    NEEDS_PROVIDER_REVIEW = "NEEDS_PROVIDER_REVIEW", "Needs provider review"
    DENIED = "DENIED", "Denied"


class RefillRequest(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="refill_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30, choices=RefillStatus.choices, db_index=True
    )
    decision_reason = models.CharField(max_length=300, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Refill {self.status} for {self.prescription}"
