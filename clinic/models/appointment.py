from django.db import models

from .doctor import Doctor, DoctorSchedule


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


class Appointment(models.Model):
    patient_id = models.CharField(max_length=100, db_index=True)
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
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["schedule_slot__date", "schedule_slot__start_time"]

    def __str__(self):
        slot = self.schedule_slot
        return (
            f"{self.patient_id} -> Dr. {self.doctor.last_name} "
            f"@ {slot.date} {slot.start_time.strftime('%H:%M')}"
        )
