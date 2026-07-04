import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .prescription import Prescription


def _refill_public_id():
    return uuid.uuid4().hex


class RefillStatus(models.TextChoices):
    APPROVED = "APPROVED", "Approved"
    NEEDS_PROVIDER_REVIEW = "NEEDS_PROVIDER_REVIEW", "Needs provider review"
    DENIED = "DENIED", "Denied"
    DISPENSED = "DISPENSED", "Dispensed"


class RefillAuthorizationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending authorization"
    AUTHORIZED = "AUTHORIZED", "Authorized"


class RefillRequest(models.Model):
    public_id = models.CharField(
        max_length=32, unique=True, default=_refill_public_id, editable=False
    )
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="refill_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30, choices=RefillStatus.choices, db_index=True
    )
    authorization_status = models.CharField(
        max_length=12,
        choices=RefillAuthorizationStatus.choices,
        default=RefillAuthorizationStatus.PENDING,
        db_index=True,
    )
    decision_reason = models.CharField(max_length=300, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Refill {self.status} for {self.prescription}"

    @classmethod
    def authorization_status_for_decision(
        cls, decision_status: str, *, is_controlled_substance: bool
    ) -> str:
        if decision_status == RefillStatus.DENIED:
            return RefillAuthorizationStatus.PENDING
        if is_controlled_substance:
            return RefillAuthorizationStatus.PENDING
        return RefillAuthorizationStatus.AUTHORIZED

    @property
    def view_url(self):
        return f"/refills/{self.public_id}/"

    def clean(self):
        if not self.pk:
            return

        previous_status = (
            RefillRequest.objects.filter(pk=self.pk)
            .values_list("status", flat=True)
            .first()
        )
        if (
            previous_status == RefillStatus.DISPENSED
            and self.status != RefillStatus.DISPENSED
        ):
            raise ValidationError(
                {"status": "Cannot change status after the refill has been dispensed."}
            )

    def save(self, *args, **kwargs):
        previous_status = None
        previous_auth_status = None

        if self.pk:
            previous = (
                RefillRequest.objects.filter(pk=self.pk)
                .values("status", "authorization_status")
                .first()
            )
            if previous:
                previous_status = previous["status"]
                previous_auth_status = previous["authorization_status"]
        else:
            if (
                self.authorization_status == RefillAuthorizationStatus.AUTHORIZED
                and not self.processed_at
            ):
                self.processed_at = timezone.now()

        if (
            previous_status == RefillStatus.DISPENSED
            and self.status != RefillStatus.DISPENSED
        ):
            raise ValidationError(
                "Cannot change status after the refill has been dispensed."
            )

        if (
            self.authorization_status == RefillAuthorizationStatus.AUTHORIZED
            and previous_auth_status != RefillAuthorizationStatus.AUTHORIZED
        ):
            self.processed_at = timezone.now()
        elif (
            self.authorization_status == RefillAuthorizationStatus.PENDING
            and previous_auth_status == RefillAuthorizationStatus.AUTHORIZED
        ):
            self.processed_at = None

        if self.status == RefillStatus.DISPENSED and not self.processed_at:
            self.processed_at = timezone.now()

        becoming_dispensed = (
            self.status == RefillStatus.DISPENSED
            and previous_status != RefillStatus.DISPENSED
        )

        with transaction.atomic():
            super().save(*args, **kwargs)

            if becoming_dispensed:
                prescription = Prescription.objects.select_for_update().get(
                    pk=self.prescription_id
                )
                if prescription.refills_remaining > 0:
                    prescription.refills_remaining -= 1
                    prescription.save(update_fields=["refills_remaining"])
