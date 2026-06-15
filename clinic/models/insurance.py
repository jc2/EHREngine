from datetime import date

from django.db import models


class InsuranceType(models.TextChoices):
    HMO = "HMO", "HMO - Health Maintenance Organization"
    PPO = "PPO", "PPO - Preferred Provider Organization"


class InsurancePayer(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class PatientInsurance(models.Model):
    patient_id = models.CharField(max_length=100, db_index=True)
    payer = models.ForeignKey(
        InsurancePayer, on_delete=models.PROTECT, related_name="patient_policies"
    )
    insurance_type = models.CharField(max_length=3, choices=InsuranceType.choices)
    member_id = models.CharField(max_length=50)
    enrollment_start = models.DateField()
    enrollment_end = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-enrollment_start"]

    def __str__(self):
        return f"{self.patient_id} -> {self.payer.name} ({self.insurance_type})"

    def is_active_on(self, check_date=None):
        check_date = check_date or date.today()
        if check_date < self.enrollment_start:
            return False
        if self.enrollment_end and check_date > self.enrollment_end:
            return False
        return True
