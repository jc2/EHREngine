from django.db import models


class MedicationForm(models.TextChoices):
    TABLET = "TABLET", "Tablet"
    CAPSULE = "CAPSULE", "Capsule"
    LIQUID = "LIQUID", "Liquid"
    INJECTION = "INJECTION", "Injection"
    INHALER = "INHALER", "Inhaler"


class Medication(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    strength = models.CharField(max_length=100)
    form = models.CharField(
        max_length=20,
        choices=MedicationForm.choices,
        default=MedicationForm.TABLET,
    )
    is_controlled_substance = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} {self.strength}"
