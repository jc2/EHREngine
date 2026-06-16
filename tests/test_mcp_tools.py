import pytest

from mcp_server.tools.availability import check_provider_availability
from mcp_server.tools.catalog import list_insurance_payers, list_medical_specialties
from mcp_server.tools.insurance import verify_insurance_eligibility
from mcp_server.tools.scheduling import schedule_appointment


@pytest.mark.django_db
class TestListInsurancePayers:
    def test_returns_active_payers(self, bcbs, aetna):
        result = list_insurance_payers()

        assert result["total"] == 2
        codes = {p["code"] for p in result["payers"]}
        assert codes == {"BCBS", "AETNA"}

    def test_empty_when_no_payers(self):
        result = list_insurance_payers()

        assert result["total"] == 0
        assert result["payers"] == []


@pytest.mark.django_db
class TestListMedicalSpecialties:
    def test_returns_specialties_with_doctor_count(self, cardiology, dermatology, doctor_wilson, doctor_chen):
        result = list_medical_specialties()

        assert result["total"] == 2
        by_code = {s["code"]: s for s in result["specialties"]}
        assert by_code["CARDIOLOGY"]["active_doctors"] == 2
        assert by_code["DERMATOLOGY"]["active_doctors"] == 0

    def test_empty_when_no_specialties(self):
        result = list_medical_specialties()

        assert result["total"] == 0
        assert result["specialties"] == []


@pytest.mark.django_db
class TestVerifyInsuranceEligibility:
    def test_eligible_patient(self, patient_insurance_ppo, bcbs):
        result = verify_insurance_eligibility("PAT-001", "BCBS")

        assert result["eligible"] is True
        assert result["insurance_type"] == "PPO"
        assert result["member_id"] == "MBR-123456"
        assert result["payer"]["name"] == "BlueCross BlueShield"

    def test_eligible_by_payer_id(self, patient_insurance_ppo, bcbs):
        result = verify_insurance_eligibility("PAT-001", str(bcbs.pk))

        assert result["eligible"] is True

    def test_unknown_payer(self, bcbs):
        result = verify_insurance_eligibility("PAT-001", "UNKNOWN")

        assert result["eligible"] is False
        assert "not found" in result["reason"]

    def test_no_policy(self, bcbs):
        result = verify_insurance_eligibility("PAT-999", "BCBS")

        assert result["eligible"] is False
        assert "no active insurance" in result["reason"]


@pytest.mark.django_db
class TestCheckProviderAvailability:
    def test_returns_open_slots(self, schedule_slot, future_date):
        result = check_provider_availability("CARDIOLOGY", future_date.isoformat())

        assert result["total_available"] == 1
        slot = result["available_slots"][0]
        assert slot["doctor_name"] == "Dr. James Wilson"
        assert slot["start_time"] == "09:00"

    def test_by_specialty_name(self, schedule_slot, future_date):
        result = check_provider_availability("Cardiology", future_date.isoformat())

        assert result["total_available"] == 1

    def test_unknown_specialty(self, future_date):
        result = check_provider_availability("FAKE", future_date.isoformat())

        assert result["total_available"] == 0
        assert "error" in result

    def test_invalid_date_format(self, cardiology):
        result = check_provider_availability("CARDIOLOGY", "not-a-date")

        assert result["total_available"] == 0
        assert "error" in result


@pytest.mark.django_db
class TestScheduleAppointment:
    def test_books_appointment(self, schedule_slot, doctor_wilson, future_date):
        result = schedule_appointment(
            patient_id="PAT-001",
            doctor_id=str(doctor_wilson.pk),
            date=future_date.isoformat(),
            time="09:00",
        )

        assert result["success"] is True
        appt = result["appointment"]
        assert appt["patient_id"] == "PAT-001"
        assert appt["doctor_name"] == "Dr. James Wilson"
        assert appt["status"] == "SCHEDULED"
        assert appt["start_time"] == "09:00"
        assert appt["end_time"] == "09:30"

    def test_rejects_double_booking(self, schedule_slot, doctor_wilson, future_date):
        schedule_appointment("PAT-001", str(doctor_wilson.pk), future_date.isoformat(), "09:00")
        result = schedule_appointment("PAT-002", str(doctor_wilson.pk), future_date.isoformat(), "09:00")

        assert result["success"] is False
        assert "already booked" in result["error"]

    def test_rejects_unknown_doctor(self, future_date):
        result = schedule_appointment("PAT-001", "99999", future_date.isoformat(), "09:00")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_rejects_invalid_date(self, doctor_wilson):
        result = schedule_appointment("PAT-001", str(doctor_wilson.pk), "bad-date", "09:00")

        assert result["success"] is False
        assert "Invalid date" in result["error"]

    def test_rejects_missing_slot(self, doctor_wilson, future_date):
        result = schedule_appointment("PAT-001", str(doctor_wilson.pk), future_date.isoformat(), "15:00")

        assert result["success"] is False
        assert "No schedule slot" in result["error"]
