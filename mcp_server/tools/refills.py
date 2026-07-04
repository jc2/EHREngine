from mcp_server.auth import enforce_patient_scope
from mcp_server.schemas.auth_mapping import (
    check_refill_auth_error,
    prescriptions_auth_error,
    refill_auth_error,
)
from mcp_server.schemas.responses import (
    CheckRefillStatusResult,
    ListPatientPrescriptionsResult,
    PrescriptionSummary,
    RequestMedicationRefillResult,
)
from mcp_server.tools.urls import absolute_view_url


def list_patient_prescriptions(patient_id: str) -> ListPatientPrescriptionsResult:
    """List all prescriptions for a patient, including active and expired ones.

    Use this tool as a discovery step BEFORE calling request_medication_refill.
    It returns prescription IDs and details needed to identify which prescription
    to refill.

    Args:
        patient_id: The patient code (e.g. "PAT-001").

    Returns:
        A dict with:
        - success (bool): Whether the lookup succeeded.
        - patient_id (str): The patient code.
        - total (int): Number of prescriptions found.
        - prescriptions (list[dict]): Each prescription includes:
            prescription_id, medication (name + strength), sig, quantity,
            refills_remaining, refills_authorized, status, date_written,
            expiration_date, is_controlled_substance.
        - error (str): If the patient has no records.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return prescriptions_auth_error(auth_error)

    from clinic.models import Patient, PatientInsurance, Prescription

    if not Patient.objects.filter(code=patient_id).exists():
        available = sorted(Patient.objects.values_list("code", flat=True))
        return ListPatientPrescriptionsResult(
            success=False,
            error=(
                f"Patient '{patient_id}' not found. "
                f"Available patient codes: {', '.join(available)}"
            ),
        )

    if not PatientInsurance.objects.filter(patient_id=patient_id).exists():
        return ListPatientPrescriptionsResult(
            success=False,
            error=f"Patient '{patient_id}' has no insurance records on file.",
        )

    prescriptions = Prescription.objects.filter(
        patient_id=patient_id,
        status__in=["ACTIVE", "EXPIRED"],
    ).select_related("medication")

    return ListPatientPrescriptionsResult(
        success=True,
        patient_id=patient_id,
        total=prescriptions.count(),
        prescriptions=[
            PrescriptionSummary(
                prescription_id=str(rx.pk),
                medication=f"{rx.medication.name} {rx.medication.strength}",
                sig=rx.sig,
                quantity=rx.quantity,
                refills_remaining=rx.refills_remaining,
                refills_authorized=rx.refills_authorized,
                status=rx.status,
                date_written=rx.date_written.isoformat(),
                expiration_date=rx.expiration_date.isoformat(),
                is_controlled_substance=rx.medication.is_controlled_substance,
            )
            for rx in prescriptions
        ],
    )


def request_medication_refill(patient_id: str, prescription_id: str) -> RequestMedicationRefillResult:
    """Request a medication refill for a specific prescription.

    Applies deterministic business rules to decide the refill outcome:
    - APPROVED: prescription is active, not controlled, has refills remaining,
      and is not expired. Refills remaining are decremented when the request
      is marked DISPENSED by staff.
    - NEEDS_PROVIDER_REVIEW: prescription is expired, medication is a controlled
      substance, or no refills remain. Requires provider authorization.
    - DENIED: prescription has been discontinued by the provider.

    Idempotent: if an APPROVED refill request already exists for this
    prescription within the last 24 hours, it is returned without
    decrementing refills_remaining again.

    Use list_patient_prescriptions first to discover available prescription IDs.

    Args:
        patient_id: The patient code (e.g. "PAT-001").
        prescription_id: The numeric prescription ID (from list_patient_prescriptions).

    Returns:
        A dict with:
        - success (bool): Whether the request was processed (True even for
          NEEDS_PROVIDER_REVIEW; False only for validation errors).
        - public_id (str): Unique identifier for this refill request.
        - detail_page_url (str): Full URL where the patient or staff can view this refill request.
        - refill_request_id (int): The RefillRequest record ID.
        - status (str): "APPROVED", "NEEDS_PROVIDER_REVIEW", "DENIED", or "DISPENSED".
        - reason (str): Explanation of the decision.
        - medication (str): Medication name and strength.
        - refills_remaining (int): Remaining refills after this operation.
        - requires_provider_review (bool): Whether a provider must review.
        - patient_id (str): The patient code.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return refill_auth_error(auth_error)

    from datetime import date, timedelta

    from django.utils import timezone

    from clinic.models import Prescription, RefillRequest

    try:
        rx_pk = int(prescription_id)
    except (ValueError, TypeError):
        return RequestMedicationRefillResult(
            success=False,
            error=f"Invalid prescription_id '{prescription_id}'. Must be a numeric ID.",
        )

    try:
        prescription = Prescription.objects.select_related("medication").get(
            pk=rx_pk, patient_id=patient_id
        )
    except Prescription.DoesNotExist:
        available = list(
            Prescription.objects.filter(patient_id=patient_id).values_list(
                "pk", flat=True
            )
        )
        if not available:
            return RequestMedicationRefillResult(
                success=False,
                error=(
                    f"Patient '{patient_id}' has no prescriptions. "
                    "Use list_patient_prescriptions to verify the patient_id."
                ),
            )
        available_str = ", ".join(str(pk) for pk in available)
        return RequestMedicationRefillResult(
            success=False,
            error=(
                f"Prescription '{prescription_id}' not found for patient '{patient_id}'. "
                f"Available prescription IDs for this patient: {available_str}"
            ),
        )

    now = timezone.now()
    recent_cutoff = now - timedelta(hours=24)
    existing = (
        RefillRequest.objects.filter(
            prescription=prescription,
            status="APPROVED",
            requested_at__gte=recent_cutoff,
        )
        .order_by("-requested_at")
        .first()
    )
    if existing:
        return RequestMedicationRefillResult(
            success=True,
            public_id=existing.public_id,
            detail_page_url=absolute_view_url(existing.view_url),
            refill_request_id=existing.pk,
            status=existing.status,
            reason="Refill already approved within the last 24 hours.",
            medication=str(prescription.medication),
            refills_remaining=prescription.refills_remaining,
            requires_provider_review=False,
            patient_id=patient_id,
        )

    def _response(refill):
        return RequestMedicationRefillResult(
            success=True,
            public_id=refill.public_id,
            detail_page_url=absolute_view_url(refill.view_url),
            refill_request_id=refill.pk,
            status=refill.status,
            reason=refill.decision_reason,
            medication=str(prescription.medication),
            refills_remaining=prescription.refills_remaining,
            requires_provider_review=refill.status == "NEEDS_PROVIDER_REVIEW",
            patient_id=patient_id,
        )

    if prescription.status == "DISCONTINUED":
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="DENIED",
            authorization_status=RefillRequest.authorization_status_for_decision(
                "DENIED",
                is_controlled_substance=prescription.medication.is_controlled_substance,
            ),
            decision_reason="Prescription discontinued by provider.",
            processed_at=now,
        )
        return _response(refill)

    is_controlled = prescription.medication.is_controlled_substance

    if prescription.status == "EXPIRED" or prescription.expiration_date < date.today():
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            authorization_status=RefillRequest.authorization_status_for_decision(
                "NEEDS_PROVIDER_REVIEW",
                is_controlled_substance=is_controlled,
            ),
            decision_reason="Prescription expired; provider renewal required.",
        )
        return _response(refill)

    if is_controlled:
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            authorization_status=RefillRequest.authorization_status_for_decision(
                "NEEDS_PROVIDER_REVIEW",
                is_controlled_substance=True,
            ),
            decision_reason="Controlled substance requires provider authorization.",
        )
        return _response(refill)

    if prescription.refills_remaining <= 0:
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            authorization_status=RefillRequest.authorization_status_for_decision(
                "NEEDS_PROVIDER_REVIEW",
                is_controlled_substance=False,
            ),
            decision_reason="No refills remaining; provider reauthorization required.",
        )
        return _response(refill)

    refill = RefillRequest.objects.create(
        prescription=prescription,
        status="APPROVED",
        authorization_status=RefillRequest.authorization_status_for_decision(
            "APPROVED",
            is_controlled_substance=False,
        ),
        decision_reason="Refill approved.",
        processed_at=now,
    )
    return _response(refill)


def check_refill_status(patient_id: str, refill_id: str) -> CheckRefillStatusResult:
    """Check whether a medication refill request has been authorized.

    Use this after request_medication_refill to follow up on pending cases, or
    when a patient asks about an existing refill using their reference code.

    Args:
        patient_id: Patient code (e.g. "PAT-001"). Required.
        refill_id: Refill reference code (public_id) from request_medication_refill.

    Returns:
        A dict with:
        - success (bool): Whether the lookup succeeded.
        - refill_id (str): The refill reference code.
        - authorization_status (str): "AUTHORIZED" or "PENDING".
        - is_authorized (bool): True when staff has authorized the refill.
        - status (str): Automated MCP decision (APPROVED, NEEDS_PROVIDER_REVIEW, DENIED, DISPENSED).
        - reason (str): Explanation of the decision.
        - medication (str): Medication name and strength.
        - patient_id (str): The patient code.
        - requested_at (str): ISO timestamp when the refill was requested.
        - processed_at (str): ISO timestamp when authorized, if applicable.
        - detail_page_url (str): Full URL where the patient or staff can view this refill request.
        - error (str): If patient_id or refill_id is missing, or the record was not found.
    """
    from clinic.models import RefillAuthorizationStatus, RefillRequest

    if not patient_id.strip():
        return CheckRefillStatusResult(success=False, error="patient_id is required.")
    if not refill_id.strip():
        return CheckRefillStatusResult(success=False, error="refill_id is required.")

    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return check_refill_auth_error(auth_error)

    patient_code = patient_id.strip()
    refill_code = refill_id.strip()

    try:
        refill = RefillRequest.objects.select_related(
            "prescription",
            "prescription__medication",
        ).get(public_id=refill_code, prescription__patient_id=patient_code)
    except RefillRequest.DoesNotExist:
        return CheckRefillStatusResult(
            success=False,
            error=(
                f"Refill '{refill_code}' not found for patient '{patient_code}'. "
                "Verify the reference code from request_medication_refill."
            ),
        )

    is_authorized = (
        refill.status != "DENIED"
        and refill.authorization_status == RefillAuthorizationStatus.AUTHORIZED
    )

    return CheckRefillStatusResult(
        success=True,
        refill_id=refill.public_id,
        authorization_status=refill.authorization_status,
        is_authorized=is_authorized,
        status=refill.status,
        reason=refill.decision_reason,
        medication=str(refill.prescription.medication),
        patient_id=patient_code,
        requested_at=refill.requested_at.isoformat(),
        processed_at=refill.processed_at.isoformat() if refill.processed_at else None,
        detail_page_url=absolute_view_url(refill.view_url),
    )

