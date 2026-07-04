import pytest
from django.core.exceptions import ValidationError

from mcp_server.tools.availability import check_provider_availability
from mcp_server.tools.catalog import list_insurance_payers, list_medical_specialties
from mcp_server.tools.escalations import check_pending_escalation, report_human_escalation
from mcp_server.tools.insurance import verify_insurance_eligibility
from mcp_server.tools.patients import identify_patient
from mcp_server.tools.refills import check_refill_status, request_medication_refill
from mcp_server.tools.scheduling import schedule_appointment

from clinic.models import EscalationStatus, HumanEscalation, Medication, Prescription, RefillRequest

from tests.mcp_helpers import mcp_dump


@pytest.mark.django_db
class TestListInsurancePayers:
    def test_returns_active_payers(self, bcbs, aetna):
        result = mcp_dump(list_insurance_payers())

        assert result["total"] == 2
        codes = {p["code"] for p in result["payers"]}
        assert codes == {"BCBS", "AETNA"}

    def test_empty_when_no_payers(self):
        result = mcp_dump(list_insurance_payers())

        assert result["total"] == 0
        assert result["payers"] == []


@pytest.mark.django_db
class TestListMedicalSpecialties:
    def test_returns_specialties_with_doctor_count(self, cardiology, dermatology, doctor_wilson, doctor_chen):
        result = mcp_dump(list_medical_specialties())

        assert result["total"] == 2
        by_code = {s["code"]: s for s in result["specialties"]}
        assert by_code["CARDIOLOGY"]["active_doctors"] == 2
        assert by_code["DERMATOLOGY"]["active_doctors"] == 0

    def test_empty_when_no_specialties(self):
        result = mcp_dump(list_medical_specialties())

        assert result["total"] == 0
        assert result["specialties"] == []


@pytest.mark.django_db
class TestVerifyInsuranceEligibility:
    def test_eligible_patient(self, patient_insurance_ppo, bcbs):
        result = mcp_dump(verify_insurance_eligibility("PAT-001", "BCBS"))

        assert result["eligible"] is True
        assert result["insurance_type"] == "PPO"
        assert result["member_id"] == "MBR-123456"
        assert result["payer"]["name"] == "BlueCross BlueShield"

    def test_eligible_by_payer_id(self, patient_insurance_ppo, bcbs):
        result = mcp_dump(verify_insurance_eligibility("PAT-001", str(bcbs.pk)))

        assert result["eligible"] is True

    def test_unknown_payer(self, bcbs):
        result = mcp_dump(verify_insurance_eligibility("PAT-001", "UNKNOWN"))

        assert result["eligible"] is False
        assert "not found" in result["reason"]

    def test_no_policy(self, bcbs):
        result = mcp_dump(verify_insurance_eligibility("PAT-999", "BCBS"))

        assert result["eligible"] is False
        assert "no active insurance" in result["reason"]


@pytest.mark.django_db
class TestCheckProviderAvailability:
    def test_returns_open_slots(self, schedule_slot, future_date):
        result = mcp_dump(check_provider_availability("CARDIOLOGY", future_date.isoformat()))

        assert result["total_available"] == 1
        slot = result["available_slots"][0]
        assert slot["doctor_name"] == "Dr. James Wilson"
        assert slot["start_time"] == "09:00"

    def test_by_specialty_name(self, schedule_slot, future_date):
        result = mcp_dump(check_provider_availability("Cardiology", future_date.isoformat()))

        assert result["total_available"] == 1

    def test_unknown_specialty(self, future_date):
        result = mcp_dump(check_provider_availability("FAKE", future_date.isoformat()))

        assert result["total_available"] == 0
        assert "error" in result

    def test_invalid_date_format(self, cardiology):
        result = mcp_dump(check_provider_availability("CARDIOLOGY", "not-a-date"))

        assert result["total_available"] == 0
        assert "error" in result


@pytest.mark.django_db
class TestIdentifyPatient:
    def test_finds_patient(self, patient_001):
        result = mcp_dump(identify_patient("John Smith", "555-0101", "ID-100001"))

        assert result["success"] is True
        assert result["patient_code"] == "PAT-001"
        assert result["patient_name"] == "John Smith"
        assert result["pending_appointments"] == []
        assert result["pending_refill_requests"] == []
        assert result["pending_escalations"] == []
        assert result["insurance_policies"] == []

    def test_phone_formatting_ignored(self, patient_001):
        result = mcp_dump(identify_patient("John Smith", "(555) 010-1", "ID-100001"))

        assert result["success"] is True
        assert result["patient_code"] == "PAT-001"

    def test_no_match(self, patient_001):
        result = mcp_dump(identify_patient("Jane Doe", "555-9999", "ID-999999"))

        assert result["success"] is False
        assert "No patient found" in result["error"]

    def test_lists_pending_context(
        self,
        patient_001,
        patient_insurance_ppo,
        schedule_slot,
        doctor_wilson,
        future_date,
        human_escalation_new,
        prescription,
    ):
        from clinic.models import Appointment, RefillRequest

        appt = Appointment.objects.create(
            patient=patient_001,
            doctor=doctor_wilson,
            schedule_slot=schedule_slot,
            status="SCHEDULED",
            notes="Follow-up visit",
        )
        RefillRequest.objects.create(
            prescription=prescription,
            status="APPROVED",
            authorization_status="AUTHORIZED",
            decision_reason="Refill approved.",
        )

        result = mcp_dump(identify_patient("John Smith", "555-0101", "ID-100001"))

        assert result["success"] is True
        assert len(result["pending_appointments"]) == 1
        assert result["pending_appointments"][0]["public_id"] == appt.public_id
        assert result["pending_appointments"][0]["detail_page_url"] == (
            f"http://localhost:8010/appointments/{appt.public_id}/"
        )
        assert result["pending_appointments"][0]["doctor_name"] == "Dr. James Wilson"

        assert len(result["pending_refill_requests"]) == 1
        assert result["pending_refill_requests"][0]["status"] == "APPROVED"

        assert len(result["pending_escalations"]) == 1
        assert result["pending_escalations"][0]["escalation_id"] == (
            human_escalation_new.public_id
        )

        assert len(result["insurance_policies"]) == 1
        assert result["insurance_policies"][0]["payer_name"] == "BlueCross BlueShield"
        assert result["insurance_policies"][0]["payer_code"] == "BCBS"
        assert result["insurance_policies"][0]["insurance_type"] == "PPO"


@pytest.mark.django_db
class TestScheduleAppointment:
    def test_books_appointment(self, schedule_slot, doctor_wilson, future_date, patient_001):
        result = mcp_dump(schedule_appointment(
            patient_id="PAT-001",
            doctor_id=str(doctor_wilson.pk),
            date=future_date.isoformat(),
            time="09:00",
            notes="Annual checkup, persistent cough for 2 weeks",
        ))

        assert result["success"] is True
        appt = result["appointment"]
        assert appt["patient_id"] == "PAT-001"
        assert appt["doctor_name"] == "Dr. James Wilson"
        assert appt["status"] == "SCHEDULED"
        assert appt["start_time"] == "09:00"
        assert appt["end_time"] == "09:30"
        assert appt["public_id"]
        assert appt["detail_page_url"] == (
            f"http://localhost:8010/appointments/{appt['public_id']}/"
        )
        assert appt["notes"] == "Annual checkup, persistent cough for 2 weeks"

    def test_requires_notes(self, schedule_slot, doctor_wilson, future_date, patient_001):
        result = mcp_dump(schedule_appointment(
            patient_id="PAT-001",
            doctor_id=str(doctor_wilson.pk),
            date=future_date.isoformat(),
            time="09:00",
            notes="",
        ))

        assert result["success"] is False
        assert "notes is required" in result["error"]

    def test_rejects_unknown_patient(self, schedule_slot, doctor_wilson, future_date):
        result = mcp_dump(schedule_appointment(
            "PAT-999", str(doctor_wilson.pk), future_date.isoformat(), "09:00",
            notes="Follow-up visit",
        ))

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_rejects_double_booking(self, schedule_slot, doctor_wilson, future_date, patient_001, patient_002):
        schedule_appointment(
            "PAT-001", str(doctor_wilson.pk), future_date.isoformat(), "09:00",
            notes="Checkup",
        )
        result = mcp_dump(schedule_appointment(
            "PAT-002", str(doctor_wilson.pk), future_date.isoformat(), "09:00",
            notes="Follow-up",
        ))

        assert result["success"] is False
        assert "already booked" in result["error"]

    def test_rejects_unknown_doctor(self, future_date, patient_001):
        result = mcp_dump(schedule_appointment(
            "PAT-001", "99999", future_date.isoformat(), "09:00",
            notes="Checkup",
        ))

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_rejects_invalid_date(self, doctor_wilson, patient_001):
        result = mcp_dump(schedule_appointment(
            "PAT-001", str(doctor_wilson.pk), "bad-date", "09:00",
            notes="Checkup",
        ))

        assert result["success"] is False
        assert "Invalid date" in result["error"]

    def test_rejects_missing_slot(self, doctor_wilson, future_date, patient_001):
        result = mcp_dump(schedule_appointment(
            "PAT-001", str(doctor_wilson.pk), future_date.isoformat(), "15:00",
            notes="Checkup",
        ))

        assert result["success"] is False
        assert "No schedule slot" in result["error"]


@pytest.mark.django_db
class TestReportHumanEscalation:
    def test_reports_with_patient_id(self, patient_001):
        result = mcp_dump(report_human_escalation(
            reported_name="John Smith",
            reported_phone="555-0101",
            reported_identification_number="ID-100001",
            initial_intent="Refill blood pressure medication",
            failure_reason="Prescription requires provider review",
            patient_id="PAT-001",
            agent_notes="Patient asked for urgent refill",
        ))

        assert result["success"] is True
        assert result["status"] == "NEW"
        assert result["detail_page_url"].startswith("http://localhost:8010/escalations/")
        escalation = HumanEscalation.objects.get(public_id=result["escalation_id"])
        assert escalation.patient_id == "PAT-001"
        assert escalation.agent_notes == "Patient asked for urgent refill"
        assert result["detail_page_url"] == f"http://localhost:8010{escalation.view_url}"

    def test_reports_without_patient_id(self):
        result = mcp_dump(report_human_escalation(
            reported_name="Unknown Person",
            reported_phone="555-9999",
            reported_identification_number="ID-999999",
            initial_intent="Book an appointment",
            failure_reason="Could not identify patient in the system",
        ))

        assert result["success"] is True
        escalation = HumanEscalation.objects.get(public_id=result["escalation_id"])
        assert escalation.patient is None
        assert escalation.reported_name == "Unknown Person"

    def test_requires_demographics_and_context(self):
        result = mcp_dump(report_human_escalation(
            reported_name="",
            reported_phone="555-0101",
            reported_identification_number="ID-100001",
            initial_intent="Book appointment",
            failure_reason="Failed",
        ))

        assert result["success"] is False
        assert "reported_name is required" in result["error"]

    def test_rejects_unknown_patient(self, patient_001):
        result = mcp_dump(report_human_escalation(
            reported_name="John Smith",
            reported_phone="555-0101",
            reported_identification_number="ID-100001",
            initial_intent="Book appointment",
            failure_reason="Failed",
            patient_id="PAT-999",
        ))

        assert result["success"] is False
        assert "not found" in result["error"]


@pytest.mark.django_db
class TestCheckPendingEscalation:
    def test_no_pending_cases(self, patient_001):
        result = mcp_dump(check_pending_escalation("PAT-001"))

        assert result["has_pending"] is False
        assert result["pending_count"] == 0
        assert result["cases"] == []

    def test_finds_pending_by_patient_id(self, human_escalation_new):
        result = mcp_dump(check_pending_escalation("PAT-001"))

        assert result["has_pending"] is True
        assert result["pending_count"] == 1
        assert result["cases"][0]["escalation_id"] == human_escalation_new.public_id
        assert result["cases"][0]["initial_intent"] == human_escalation_new.initial_intent
        assert result["cases"][0]["detail_page_url"] == (
            f"http://localhost:8010{human_escalation_new.view_url}"
        )

    def test_ignores_resolved_cases(self, human_escalation_new):
        human_escalation_new.status = EscalationStatus.RESOLVED
        human_escalation_new.save()

        result = mcp_dump(check_pending_escalation("PAT-001"))

        assert result["has_pending"] is False
        assert result["pending_count"] == 0

    def test_requires_patient_id(self):
        result = mcp_dump(check_pending_escalation(""))

        assert result["has_pending"] is False
        assert "patient_id is required" in result["error"]

    def test_rejects_unknown_patient(self):
        result = mcp_dump(check_pending_escalation("PAT-999"))

        assert result["has_pending"] is False
        assert "not found" in result["error"]


@pytest.fixture
def controlled_medication():
    return Medication.objects.create(
        name="Oxycodone",
        strength="5mg",
        form="TABLET",
        is_controlled_substance=True,
    )


@pytest.fixture
def medication():
    return Medication.objects.create(
        name="Lisinopril",
        strength="10mg",
        form="TABLET",
        is_controlled_substance=False,
    )


@pytest.fixture
def prescription(patient_001, medication, doctor_wilson):
    from datetime import date, timedelta

    return Prescription.objects.create(
        patient=patient_001,
        medication=medication,
        prescriber=doctor_wilson,
        sig="Take one daily",
        quantity=30,
        refills_authorized=3,
        refills_remaining=2,
        status="ACTIVE",
        date_written=date.today() - timedelta(days=30),
        expiration_date=date.today() + timedelta(days=335),
    )


@pytest.mark.django_db
class TestCheckRefillStatus:
    def test_authorized_refill(self, prescription, patient_insurance_ppo):
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="APPROVED",
            authorization_status="AUTHORIZED",
            decision_reason="Refill approved.",
        )

        result = mcp_dump(check_refill_status("PAT-001", refill.public_id))

        assert result["success"] is True
        assert result["is_authorized"] is True
        assert result["authorization_status"] == "AUTHORIZED"
        assert result["status"] == "APPROVED"
        assert result["detail_page_url"] == f"http://localhost:8010{refill.view_url}"

    def test_pending_refill(self, prescription, controlled_medication, doctor_wilson, patient_insurance_ppo):
        from datetime import date, timedelta

        controlled_rx = Prescription.objects.create(
            patient=prescription.patient,
            medication=controlled_medication,
            prescriber=doctor_wilson,
            sig="Take one daily",
            quantity=30,
            refills_authorized=1,
            refills_remaining=1,
            status="ACTIVE",
            date_written=date.today() - timedelta(days=30),
            expiration_date=date.today() + timedelta(days=335),
        )
        refill = RefillRequest.objects.create(
            prescription=controlled_rx,
            status="NEEDS_PROVIDER_REVIEW",
            authorization_status="PENDING",
            decision_reason="Controlled substance requires provider authorization.",
        )

        result = mcp_dump(check_refill_status("PAT-001", refill.public_id))

        assert result["success"] is True
        assert result["is_authorized"] is False
        assert result["authorization_status"] == "PENDING"
        assert result["status"] == "NEEDS_PROVIDER_REVIEW"

    def test_denied_refill_not_authorized(self, prescription, patient_insurance_ppo):
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="DENIED",
            authorization_status="PENDING",
            decision_reason="Prescription discontinued by provider.",
        )

        result = mcp_dump(check_refill_status("PAT-001", refill.public_id))

        assert result["success"] is True
        assert result["is_authorized"] is False
        assert result["status"] == "DENIED"

    def test_requires_refill_id(self, patient_insurance_ppo):
        result = mcp_dump(check_refill_status("PAT-001", ""))

        assert result["success"] is False
        assert "refill_id is required" in result["error"]

    def test_rejects_unknown_refill(self, patient_insurance_ppo):
        result = mcp_dump(check_refill_status("PAT-001", "doesnotexist"))

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_end_to_end_after_request(self, prescription, patient_insurance_ppo):
        created = mcp_dump(request_medication_refill("PAT-001", str(prescription.pk)))

        result = mcp_dump(check_refill_status("PAT-001", created["public_id"]))

        assert result["success"] is True
        assert result["is_authorized"] is True
        assert result["refill_id"] == created["public_id"]


@pytest.mark.django_db
class TestPrescriptionRefills:
    def test_increasing_authorized_updates_remaining(self, prescription):
        prescription.refills_authorized = 5
        prescription.save()

        prescription.refresh_from_db()
        assert prescription.refills_used == 1
        assert prescription.refills_remaining == 4

    def test_cannot_reduce_authorized_below_dispensed(self, prescription):
        import pytest
        from django.core.exceptions import ValidationError

        from clinic.admin import PrescriptionAdminForm

        prescription.refills_authorized = 0

        with pytest.raises(ValidationError):
            prescription.full_clean()

        form = PrescriptionAdminForm(
            data={
                "patient": prescription.patient_id,
                "medication": prescription.medication_id,
                "prescriber": prescription.prescriber_id,
                "sig": prescription.sig,
                "quantity": prescription.quantity,
                "refills_authorized": 0,
                "refills_remaining": prescription.refills_remaining,
                "status": prescription.status,
                "date_written": prescription.date_written.isoformat(),
                "expiration_date": prescription.expiration_date.isoformat(),
                "pharmacy": prescription.pharmacy,
            },
            instance=prescription,
        )
        assert not form.is_valid()
        assert "refills_authorized" in form.errors

    def test_mcp_refill_does_not_decrement_until_dispensed(self, prescription, patient_insurance_ppo):
        created = mcp_dump(request_medication_refill("PAT-001", str(prescription.pk)))

        prescription.refresh_from_db()
        assert prescription.refills_remaining == 2
        assert created["detail_page_url"] == (
            f"http://localhost:8010/refills/{created['public_id']}/"
        )

        refill = RefillRequest.objects.get(public_id=created["public_id"])
        refill.status = "DISPENSED"
        refill.save()

        prescription.refresh_from_db()
        assert prescription.refills_remaining == 1
        assert prescription.refills_used == 2

    def test_dispensed_status_is_terminal(self, prescription, patient_insurance_ppo):
        created = mcp_dump(request_medication_refill("PAT-001", str(prescription.pk)))
        refill = RefillRequest.objects.get(public_id=created["public_id"])

        refill.status = "DISPENSED"
        refill.save()

        refill.status = "APPROVED"
        with pytest.raises(ValidationError):
            refill.save()

    def test_non_controlled_needs_review_is_auto_authorized(self, prescription, patient_insurance_ppo):
        prescription.refills_remaining = 0
        prescription.save()

        created = mcp_dump(request_medication_refill("PAT-001", str(prescription.pk)))

        assert created["status"] == "NEEDS_PROVIDER_REVIEW"
        refill = RefillRequest.objects.get(public_id=created["public_id"])
        assert refill.authorization_status == "AUTHORIZED"

