from datetime import date, time, timedelta

import pytest

from clinic.models import (
    Doctor,
    DoctorSchedule,
    EscalationStatus,
    HumanEscalation,
    InsurancePayer,
    MedicalDepartment,
    Patient,
    PatientInsurance,
)


@pytest.fixture
def cardiology():
    return MedicalDepartment.objects.create(
        code="CARDIOLOGY", name="Cardiology", is_active=True
    )


@pytest.fixture
def dermatology():
    return MedicalDepartment.objects.create(
        code="DERMATOLOGY", name="Dermatology", is_active=True
    )


@pytest.fixture
def bcbs():
    return InsurancePayer.objects.create(
        name="BlueCross BlueShield", code="BCBS", is_active=True
    )


@pytest.fixture
def aetna():
    return InsurancePayer.objects.create(
        name="Aetna", code="AETNA", is_active=True
    )


@pytest.fixture
def patient_001():
    return Patient.objects.create(
        code="PAT-001",
        first_name="John",
        last_name="Smith",
        phone_number="555-0101",
        identification_number="ID-100001",
    )


@pytest.fixture
def patient_002():
    return Patient.objects.create(
        code="PAT-002",
        first_name="Maria",
        last_name="Garcia",
        phone_number="555-0102",
        identification_number="ID-100002",
    )


@pytest.fixture
def doctor_wilson(cardiology):
    return Doctor.objects.create(
        first_name="James",
        last_name="Wilson",
        specialty=cardiology,
        license_number="MD-0001",
        is_active=True,
    )


@pytest.fixture
def doctor_chen(cardiology):
    return Doctor.objects.create(
        first_name="Sarah",
        last_name="Chen",
        specialty=cardiology,
        license_number="MD-0002",
        is_active=True,
    )


@pytest.fixture
def future_date():
    d = date.today() + timedelta(days=3)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


@pytest.fixture
def schedule_slot(doctor_wilson, future_date):
    return DoctorSchedule.objects.create(
        doctor=doctor_wilson,
        date=future_date,
        start_time=time(9, 0),
        end_time=time(9, 30),
    )


@pytest.fixture
def patient_insurance_ppo(patient_001, bcbs):
    return PatientInsurance.objects.create(
        patient=patient_001,
        payer=bcbs,
        insurance_type="PPO",
        member_id="MBR-123456",
        enrollment_start=date.today() - timedelta(days=180),
        enrollment_end=None,
    )


@pytest.fixture
def human_escalation_new(patient_001):
    return HumanEscalation.objects.create(
        patient=patient_001,
        reported_name="John Smith",
        reported_phone="555-0101",
        reported_identification_number="ID-100001",
        initial_intent="Schedule cardiology appointment",
        failure_reason="No available slots in the requested timeframe",
        status=EscalationStatus.NEW,
    )
