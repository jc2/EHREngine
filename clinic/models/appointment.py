import uuid

from django.db import models

from .doctor import Doctor, DoctorSchedule
from .patient import Patient


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


def _appointment_public_id():
    return uuid.uuid4().hex


class Appointment(models.Model):
    public_id = models.CharField(
        max_length=32, unique=True, default=_appointment_public_id, editable=False
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="appointments", to_field="code"
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, related_name="appointments"
    )
    schedule_slot = models.OneToOneField(
        DoctorSchedule, on_delete=models.PROTECT, related_name="appointment"
    )
    status = models.CharField(
        max_length=10,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField()

    class Meta:
        ordering = ["schedule_slot__date", "schedule_slot__start_time"]

    def __str__(self):
        slot = self.schedule_slot
        return (
            f"{self.patient_id} -> Dr. {self.doctor.last_name} "
            f"@ {slot.date} {slot.start_time.strftime('%H:%M')}"
        )

    @property
    def view_url(self):
        return f"/appointments/{self.public_id}/"
