from typing import Any


def list_patient_prescriptions(patient_id: str) -> dict[str, Any]:
    """List all prescriptions for a patient, including active and expired ones.

    Use this tool as a discovery step BEFORE calling request_medication_refill.
    It returns prescription IDs and details needed to identify which prescription
    to refill.

    Args:
        patient_id: The external patient identifier (e.g. "PAT-001").

    Returns:
        A dict with:
        - success (bool): Whether the lookup succeeded.
        - patient_id (str): The patient identifier.
        - total (int): Number of prescriptions found.
        - prescriptions (list[dict]): Each prescription includes:
            prescription_id, medication (name + strength), sig, quantity,
            refills_remaining, refills_authorized, status, date_written,
            expiration_date, is_controlled_substance.
        - error (str): If the patient has no records.
    """
    from clinic.models import PatientInsurance, Prescription

    if not PatientInsurance.objects.filter(patient_id=patient_id).exists():
        available = sorted(
            PatientInsurance.objects.values_list("patient_id", flat=True).distinct()
        )
        return {
            "success": False,
            "error": (
                f"Patient '{patient_id}' not found. "
                f"Available patient IDs: {', '.join(available)}"
            ),
        }

    prescriptions = Prescription.objects.filter(
        patient_id=patient_id,
        status__in=["ACTIVE", "EXPIRED"],
    ).select_related("medication")

    return {
        "success": True,
        "patient_id": patient_id,
        "total": prescriptions.count(),
        "prescriptions": [
            {
                "prescription_id": str(rx.pk),
                "medication": f"{rx.medication.name} {rx.medication.strength}",
                "sig": rx.sig,
                "quantity": rx.quantity,
                "refills_remaining": rx.refills_remaining,
                "refills_authorized": rx.refills_authorized,
                "status": rx.status,
                "date_written": rx.date_written.isoformat(),
                "expiration_date": rx.expiration_date.isoformat(),
                "is_controlled_substance": rx.medication.is_controlled_substance,
            }
            for rx in prescriptions
        ],
    }


def request_medication_refill(patient_id: str, prescription_id: str) -> dict[str, Any]:
    """Request a medication refill for a specific prescription.

    Applies deterministic business rules to decide the refill outcome:
    - APPROVED: prescription is active, not controlled, has refills remaining,
      and is not expired. refills_remaining is decremented by 1.
    - NEEDS_PROVIDER_REVIEW: prescription is expired, medication is a controlled
      substance, or no refills remain. Requires provider authorization.
    - DENIED: prescription has been discontinued by the provider.

    Idempotent: if an APPROVED refill request already exists for this
    prescription within the last 24 hours, it is returned without
    decrementing refills_remaining again.

    Use list_patient_prescriptions first to discover available prescription IDs.

    Args:
        patient_id: The external patient identifier (e.g. "PAT-001").
        prescription_id: The numeric prescription ID (from list_patient_prescriptions).

    Returns:
        A dict with:
        - success (bool): Whether the request was processed (True even for
          NEEDS_PROVIDER_REVIEW; False only for validation errors).
        - refill_request_id (int): The RefillRequest record ID.
        - status (str): "APPROVED", "NEEDS_PROVIDER_REVIEW", or "DENIED".
        - reason (str): Explanation of the decision.
        - medication (str): Medication name and strength.
        - refills_remaining (int): Remaining refills after this operation.
        - requires_provider_review (bool): Whether a provider must review.
        - patient_id (str): The patient identifier.
    """
    from datetime import date, timedelta

    from django.utils import timezone

    from clinic.models import Prescription, RefillRequest

    try:
        rx_pk = int(prescription_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": f"Invalid prescription_id '{prescription_id}'. Must be a numeric ID.",
        }

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
            return {
                "success": False,
                "error": (
                    f"Patient '{patient_id}' has no prescriptions. "
                    "Use list_patient_prescriptions to verify the patient_id."
                ),
            }
        available_str = ", ".join(str(pk) for pk in available)
        return {
            "success": False,
            "error": (
                f"Prescription '{prescription_id}' not found for patient '{patient_id}'. "
                f"Available prescription IDs for this patient: {available_str}"
            ),
        }

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
        return {
            "success": True,
            "refill_request_id": existing.pk,
            "status": existing.status,
            "reason": "Refill already approved within the last 24 hours.",
            "medication": str(prescription.medication),
            "refills_remaining": prescription.refills_remaining,
            "requires_provider_review": False,
            "patient_id": patient_id,
        }

    if prescription.status == "DISCONTINUED":
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="DENIED",
            decision_reason="Prescription discontinued by provider.",
            processed_at=now,
        )
        return {
            "success": True,
            "refill_request_id": refill.pk,
            "status": "DENIED",
            "reason": "Prescription discontinued by provider.",
            "medication": str(prescription.medication),
            "refills_remaining": prescription.refills_remaining,
            "requires_provider_review": False,
            "patient_id": patient_id,
        }

    if prescription.status == "EXPIRED" or prescription.expiration_date < date.today():
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            decision_reason="Prescription expired; provider renewal required.",
        )
        return {
            "success": True,
            "refill_request_id": refill.pk,
            "status": "NEEDS_PROVIDER_REVIEW",
            "reason": "Prescription expired; provider renewal required.",
            "medication": str(prescription.medication),
            "refills_remaining": prescription.refills_remaining,
            "requires_provider_review": True,
            "patient_id": patient_id,
        }

    if prescription.medication.is_controlled_substance:
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            decision_reason="Controlled substance requires provider authorization.",
        )
        return {
            "success": True,
            "refill_request_id": refill.pk,
            "status": "NEEDS_PROVIDER_REVIEW",
            "reason": "Controlled substance requires provider authorization.",
            "medication": str(prescription.medication),
            "refills_remaining": prescription.refills_remaining,
            "requires_provider_review": True,
            "patient_id": patient_id,
        }

    if prescription.refills_remaining <= 0:
        refill = RefillRequest.objects.create(
            prescription=prescription,
            status="NEEDS_PROVIDER_REVIEW",
            decision_reason="No refills remaining; provider reauthorization required.",
        )
        return {
            "success": True,
            "refill_request_id": refill.pk,
            "status": "NEEDS_PROVIDER_REVIEW",
            "reason": "No refills remaining; provider reauthorization required.",
            "medication": str(prescription.medication),
            "refills_remaining": 0,
            "requires_provider_review": True,
            "patient_id": patient_id,
        }

    prescription.refills_remaining -= 1
    prescription.save(update_fields=["refills_remaining"])

    refill = RefillRequest.objects.create(
        prescription=prescription,
        status="APPROVED",
        decision_reason="Refill approved.",
        processed_at=now,
    )
    return {
        "success": True,
        "refill_request_id": refill.pk,
        "status": "APPROVED",
        "reason": "Refill approved.",
        "medication": str(prescription.medication),
        "refills_remaining": prescription.refills_remaining,
        "requires_provider_review": False,
        "patient_id": patient_id,
    }
