from datetime import date, time, timedelta

import pytest

from clinic.models import (
    Doctor,
    DoctorSchedule,
    InsurancePayer,
    MedicalDepartment,
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
def patient_insurance_ppo(bcbs):
    return PatientInsurance.objects.create(
        patient_id="PAT-001",
        payer=bcbs,
        insurance_type="PPO",
        member_id="MBR-123456",
        enrollment_start=date.today() - timedelta(days=180),
        enrollment_end=None,
    )
