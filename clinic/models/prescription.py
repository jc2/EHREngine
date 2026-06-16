from django.db import models

from .doctor import Doctor
from .medication import Medication


class PrescriptionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    DISCONTINUED = "DISCONTINUED", "Discontinued"


class Prescription(models.Model):
    patient_id = models.CharField(max_length=100, db_index=True)
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
