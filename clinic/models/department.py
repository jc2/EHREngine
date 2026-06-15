from django.db import models


class MedicalDepartment(models.TextChoices):
    CARDIOLOGY = "CARDIOLOGY", "Cardiology"
    DERMATOLOGY = "DERMATOLOGY", "Dermatology"
    GENERAL_PRACTICE = "GENERAL_PRACTICE", "General Practice"
    PEDIATRICS = "PEDIATRICS", "Pediatrics"
    ORTHOPEDICS = "ORTHOPEDICS", "Orthopedics"
    NEUROLOGY = "NEUROLOGY", "Neurology"
    GYNECOLOGY = "GYNECOLOGY", "Gynecology"
    OPHTHALMOLOGY = "OPHTHALMOLOGY", "Ophthalmology"
