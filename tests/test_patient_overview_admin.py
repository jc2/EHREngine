from datetime import date, time, timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from clinic.models import (
    Appointment,
    HumanEscalation,
    Medication,
    Prescription,
    RefillRequest,
    RefillStatus,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    User.objects.create_superuser("boss", "boss@example.com", "pw12345")
    client.force_login(User.objects.get(username="boss"))
    return client


@pytest.fixture
def medication():
    return Medication.objects.create(name="Lisinopril", strength="10mg", form="TABLET")


@pytest.fixture
def prescription(patient_001, medication, doctor_wilson):
    return Prescription.objects.create(
        patient=patient_001,
        medication=medication,
        prescriber=doctor_wilson,
        sig="Take one daily",
        quantity=30,
        refills_authorized=3,
        refills_remaining=3,
        date_written=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )


@pytest.fixture
def appointment(patient_001, doctor_wilson, schedule_slot):
    return Appointment.objects.create(
        patient=patient_001,
        doctor=doctor_wilson,
        schedule_slot=schedule_slot,
        notes="Follow-up",
    )


@pytest.fixture
def refill(prescription):
    return RefillRequest.objects.create(
        prescription=prescription, status=RefillStatus.APPROVED
    )


def test_overview_requires_login(client):
    url = reverse("admin:clinic_patient_overview")
    response = client.get(url)
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_overview_lists_associated_records(
    admin_client, patient_001, appointment, refill, human_escalation_new
):
    url = reverse("admin:clinic_patient_overview")
    response = admin_client.get(url, {"patient": patient_001.pk})
    assert response.status_code == 200
    assert response.context["patient"].pk == patient_001.pk
    assert response.context["appointment_count"] == 1
    assert response.context["refill_count"] == 1
    assert response.context["escalation_count"] == 1
    # Patient identifiers available for the copy button
    content = response.content.decode()
    assert patient_001.identification_number in content
    assert patient_001.phone_number in content


def test_overview_unknown_patient(admin_client):
    url = reverse("admin:clinic_patient_overview")
    response = admin_client.get(url, {"patient": "NOPE"})
    assert response.status_code == 200
    assert response.context.get("patient") is None


def test_clear_all_deletes_associated_records(
    admin_client, patient_001, appointment, refill, human_escalation_new
):
    clear_url = reverse("admin:clinic_patient_overview_clear")
    response = admin_client.post(clear_url, {"patient": patient_001.pk})
    assert response.status_code == 302

    assert not Appointment.objects.filter(patient=patient_001).exists()
    assert not RefillRequest.objects.filter(prescription__patient=patient_001).exists()
    assert not HumanEscalation.objects.filter(patient=patient_001).exists()
    # Patient itself is preserved
    patient_001.refresh_from_db()
    assert patient_001.pk == "PAT-001"


def test_clear_all_rejects_get(admin_client, patient_001):
    clear_url = reverse("admin:clinic_patient_overview_clear")
    response = admin_client.get(clear_url, {"patient": patient_001.pk})
    assert response.status_code == 302
    assert reverse("admin:clinic_patient_overview") in response["Location"]
