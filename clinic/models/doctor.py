from django.db import models

from .department import MedicalDepartment


class Doctor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=30, choices=MedicalDepartment.choices)
    license_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} ({self.get_specialty_display()})"


class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="schedules"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = [("doctor", "date", "start_time")]

    def __str__(self):
        return (
            f"{self.doctor.last_name} | "
            f"{self.date} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
        )
