import uuid

import django.db.models.deletion
from django.db import migrations, models


def _appointment_public_id():
    return uuid.uuid4().hex


def _refill_public_id():
    return uuid.uuid4().hex


PATIENT_SEED = {
    "PAT-001": ("John", "Smith", "555-0101", "ID-100001"),
    "PAT-002": ("Maria", "Garcia", "555-0102", "ID-100002"),
    "PAT-003": ("Robert", "Johnson", "555-0103", "ID-100003"),
    "PAT-004": ("Emily", "Davis", "555-0104", "ID-100004"),
    "PAT-005": ("Michael", "Wilson", "555-0105", "ID-100005"),
    "PAT-006": ("Sarah", "Martinez", "555-0106", "ID-100006"),
    "PAT-007": ("David", "Anderson", "555-0107", "ID-100007"),
    "PAT-008": ("Jessica", "Taylor", "555-0108", "ID-100008"),
    "PAT-009": ("Christopher", "Thomas", "555-0109", "ID-100009"),
    "PAT-010": ("Amanda", "Moore", "555-0110", "ID-100010"),
}


def create_patients_from_existing(apps, schema_editor):
    Patient = apps.get_model("clinic", "Patient")
    patient_ids = set()

    for model_name in ("PatientInsurance", "Prescription", "Appointment"):
        Model = apps.get_model("clinic", model_name)
        patient_ids.update(
            pid for pid in Model.objects.values_list("legacy_patient_id", flat=True).distinct() if pid
        )

    for idx, code in enumerate(sorted(patient_ids), start=1):
        if code in PATIENT_SEED:
            first, last, phone, id_num = PATIENT_SEED[code]
        else:
            first, last = "Unknown", f"Patient {idx}"
            phone = f"555-{idx:04d}"
            id_num = f"LEGACY-{code.replace('-', '')}"

        Patient.objects.get_or_create(
            code=code,
            defaults={
                "first_name": first,
                "last_name": last,
                "phone_number": phone,
                "identification_number": id_num,
            },
        )


def backfill_public_ids(apps, schema_editor):
    for model_name in ("Appointment", "RefillRequest"):
        Model = apps.get_model("clinic", model_name)
        for obj in Model.objects.filter(public_id__isnull=True):
            obj.public_id = uuid.uuid4().hex
            obj.save(update_fields=["public_id"])


def link_patient_foreign_keys(apps, schema_editor):
    Patient = apps.get_model("clinic", "Patient")

    for model_name in ("PatientInsurance", "Prescription", "Appointment"):
        Model = apps.get_model("clinic", model_name)
        for obj in Model.objects.all():
            patient = Patient.objects.get(code=obj.legacy_patient_id)
            obj.patient = patient
            obj.save(update_fields=["patient"])


def backfill_appointment_notes(apps, schema_editor):
    Appointment = apps.get_model("clinic", "Appointment")
    Appointment.objects.filter(notes="").update(notes="Legacy appointment — reasons not recorded.")


class Migration(migrations.Migration):

    dependencies = [
        ("clinic", "0003_billingrule"),
    ]

    operations = [
        migrations.CreateModel(
            name="Patient",
            fields=[
                (
                    "code",
                    models.CharField(max_length=20, primary_key=True, serialize=False),
                ),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("phone_number", models.CharField(db_index=True, max_length=20)),
                (
                    "identification_number",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.RenameField(
            model_name="appointment",
            old_name="patient_id",
            new_name="legacy_patient_id",
        ),
        migrations.RenameField(
            model_name="prescription",
            old_name="patient_id",
            new_name="legacy_patient_id",
        ),
        migrations.RenameField(
            model_name="patientinsurance",
            old_name="patient_id",
            new_name="legacy_patient_id",
        ),
        migrations.RunPython(create_patients_from_existing, migrations.RunPython.noop),
        migrations.AddField(
            model_name="appointment",
            name="public_id",
            field=models.CharField(max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="refillrequest",
            name="public_id",
            field=models.CharField(max_length=32, null=True),
        ),
        migrations.RunPython(backfill_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="public_id",
            field=models.CharField(
                default=_appointment_public_id,
                editable=False,
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="refillrequest",
            name="public_id",
            field=models.CharField(
                default=_refill_public_id,
                editable=False,
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="patient",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.AddField(
            model_name="prescription",
            name="patient",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="prescriptions",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.AddField(
            model_name="patientinsurance",
            name="patient",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="insurance_policies",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.RunPython(link_patient_foreign_keys, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="appointment",
            name="legacy_patient_id",
        ),
        migrations.RemoveField(
            model_name="prescription",
            name="legacy_patient_id",
        ),
        migrations.RemoveField(
            model_name="patientinsurance",
            name="legacy_patient_id",
        ),
        migrations.AlterField(
            model_name="appointment",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.AlterField(
            model_name="prescription",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="prescriptions",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.AlterField(
            model_name="patientinsurance",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="insurance_policies",
                to="clinic.patient",
                to_field="code",
            ),
        ),
        migrations.RunPython(backfill_appointment_notes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="notes",
            field=models.TextField(),
        ),
    ]
