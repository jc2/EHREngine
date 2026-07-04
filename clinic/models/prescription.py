from django.core.exceptions import ValidationError
from django.db import models

from .doctor import Doctor
from .medication import Medication
from .patient import Patient


class PrescriptionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    DISCONTINUED = "DISCONTINUED", "Discontinued"


class Prescription(models.Model):
    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="prescriptions", to_field="code"
    )
    medication = models.ForeignKey(
        Medication, on_delete=models.PROTECT, related_name="prescriptions"
    )
    prescriber = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, related_name="prescriptions"
    )
    sig = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField()
    refills_authorized = models.PositiveIntegerField(default=0)
    refills_remaining = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=PrescriptionStatus.choices,
        default=PrescriptionStatus.ACTIVE,
        db_index=True,
    )
    date_written = models.DateField()
    expiration_date = models.DateField()
    pharmacy = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date_written"]

    def __str__(self):
        return f"{self.medication} for {self.patient_id} ({self.refills_remaining} refills left)"

    @property
    def refills_used(self) -> int:
        return self.refills_authorized - self.refills_remaining

    def clean(self):
        if self.pk:
            old_authorized, old_remaining = (
                Prescription.objects.filter(pk=self.pk)
                .values_list("refills_authorized", "refills_remaining")
                .first()
            )
            if old_authorized is not None:
                refills_used = old_authorized - old_remaining
                if self.refills_authorized < refills_used:
                    raise ValidationError(
                        {
                            "refills_authorized": (
                                "Cannot be less than refills already dispensed "
                                f"({refills_used})."
                            )
                        }
                    )

    def save(self, *args, **kwargs):
        if self.pk:
            old_authorized, old_remaining = (
                Prescription.objects.filter(pk=self.pk)
                .values_list("refills_authorized", "refills_remaining")
                .first()
            )
            if self.refills_authorized != old_authorized:
                refills_used = old_authorized - old_remaining
                self.refills_remaining = self.refills_authorized - refills_used
        else:
            if self.refills_remaining > self.refills_authorized:
                self.refills_remaining = self.refills_authorized

        super().save(*args, **kwargs)
