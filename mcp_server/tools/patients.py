from datetime import date

from django.db import models

from mcp_server.schemas.responses import (
    IdentifyPatientResult,
    PatientInsuranceSummary,
    PendingAppointmentSummary,
    PendingEscalationCase,
    PendingRefillRequestSummary,
)
from mcp_server.tools.normalize import (
    normalize_identification_number,
    normalize_name,
    normalize_phone,
)
from mcp_server.tools.urls import absolute_view_url


def _patient_context(patient) -> dict:
    from clinic.models import (
        Appointment,
        EscalationStatus,
        HumanEscalation,
        PatientInsurance,
        RefillRequest,
    )

    pending_appointments = [
        PendingAppointmentSummary(
            public_id=appt.public_id,
            detail_page_url=absolute_view_url(appt.view_url),
            date=appt.schedule_slot.date.isoformat(),
            start_time=appt.schedule_slot.start_time.strftime("%H:%M"),
            end_time=appt.schedule_slot.end_time.strftime("%H:%M"),
            doctor_name=f"Dr. {appt.doctor.first_name} {appt.doctor.last_name}",
            specialty=appt.doctor.specialty.name,
            status=appt.status,
        )
        for appt in Appointment.objects.filter(
            patient=patient, status="SCHEDULED"
        ).select_related("doctor", "doctor__specialty", "schedule_slot")
    ]

    pending_refill_requests = [
        PendingRefillRequestSummary(
            public_id=refill.public_id,
            detail_page_url=absolute_view_url(refill.view_url),
            medication=str(refill.prescription.medication),
            status=refill.status,
            authorization_status=refill.authorization_status,
            requested_at=refill.requested_at.isoformat(),
        )
        for refill in RefillRequest.objects.filter(
            prescription__patient=patient,
        )
        .exclude(status__in=["DISPENSED", "DENIED"])
        .select_related("prescription__medication")
    ]

    pending_escalations = [
        PendingEscalationCase(
            escalation_id=escalation.public_id,
            initial_intent=escalation.initial_intent,
            created_at=escalation.created_at.isoformat(),
            detail_page_url=absolute_view_url(escalation.view_url),
        )
        for escalation in HumanEscalation.objects.filter(
            patient=patient,
            status=EscalationStatus.NEW,
        )
    ]

    today = date.today()
    insurance_policies = [
        PatientInsuranceSummary(
            payer_name=policy.payer.name,
            payer_code=policy.payer.code,
            insurance_type=policy.insurance_type,
            member_id=policy.member_id,
        )
        for policy in PatientInsurance.objects.filter(
            patient=patient,
            enrollment_start__lte=today,
        )
        .filter(
            models.Q(enrollment_end__isnull=True) | models.Q(enrollment_end__gte=today)
        )
        .select_related("payer")
    ]

    return {
        "pending_appointments": pending_appointments,
        "pending_refill_requests": pending_refill_requests,
        "pending_escalations": pending_escalations,
        "insurance_policies": insurance_policies,
    }


def identify_patient(name: str, phone_number: str, identification_number: str) -> IdentifyPatientResult:
    """Identify a patient by demographic data and return their patient code.

    Use this tool at the start of a workflow when the patient is not yet known
    by code (e.g. "PAT-001"). All three fields must match a single patient record.

    Args:
        name: Patient full name (e.g. "Maria Garcia"). Case-insensitive.
        phone_number: Patient phone number. Formatting is ignored (dashes, spaces).
        identification_number: Government or clinic ID number. Case-insensitive.

    Returns:
        A dict with:
        - success (bool): Whether a matching patient was found.
        - patient_code (str): The patient code (e.g. "PAT-001") if found.
        - patient_name (str): Full name of the matched patient.
        - pending_appointments (list): Scheduled appointments not yet completed.
        - pending_refill_requests (list): Open refill requests (not dispensed or denied).
        - pending_escalations (list): Human escalation cases awaiting staff review.
        - insurance_policies (list): Active insurance policies with payer and type.
        - error (str): Reason if no match was found.
    """
    from clinic.models import Patient

    normalized_name = normalize_name(name)
    normalized_phone = normalize_phone(phone_number)
    normalized_id = normalize_identification_number(identification_number)

    if not normalized_name or not normalized_phone or not normalized_id:
        return IdentifyPatientResult(
            success=False,
            error="name, phone_number, and identification_number are all required.",
        )

    for patient in Patient.objects.all():
        full_name = normalize_name(f"{patient.first_name} {patient.last_name}")
        if (
            full_name == normalized_name
            and normalize_phone(patient.phone_number) == normalized_phone
            and patient.identification_number.upper() == normalized_id
        ):
            context = _patient_context(patient)
            return IdentifyPatientResult(
                success=True,
                patient_code=patient.code,
                patient_name=patient.full_name,
                **context,
            )

    return IdentifyPatientResult(
        success=False,
        error=(
            "No patient found matching the provided name, phone number, "
            "and identification number."
        ),
    )
