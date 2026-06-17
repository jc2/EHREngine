from datetime import date
from typing import Any

from django.db import models

from mcp_server.auth import enforce_patient_scope


def verify_insurance_eligibility(patient_id: str, payer_id: str) -> dict[str, Any]:
    """Verify whether a patient has active insurance coverage with a specific payer.

    Use this tool BEFORE scheduling an appointment to confirm the patient's
    insurance is currently active. Returns the insurance type (HMO or PPO),
    which determines whether the patient needs a referral to see a specialist.

    - HMO plans require a referral from a primary care physician.
    - PPO plans allow direct specialist visits (no referral needed).

    Args:
        patient_id: The external patient identifier (e.g. "PAT-001").
        payer_id: The insurance payer's code (e.g. "CIGNA", "BCBS", "AETNA",
                  "UHC", "HUMANA", "KAISER", "ANTHEM", "MOLINA") or numeric ID.

    Returns:
        A dict with:
        - eligible (bool): Whether the patient has active coverage.
        - insurance_type (str): "HMO" or "PPO" if eligible.
        - member_id (str): The insurance member number if eligible.
        - payer (dict): Payer name and ID if eligible.
        - reason (str): Explanation if not eligible.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return auth_error

    from clinic.models import InsurancePayer, PatientInsurance

    s = payer_id.strip()
    if s.isdigit():
        payer = InsurancePayer.objects.filter(pk=s, is_active=True).first()
    else:
        payer = (
            InsurancePayer.objects.filter(code__iexact=s, is_active=True).first()
            or InsurancePayer.objects.filter(name__iexact=s, is_active=True).first()
        )

    if payer is None:
        available = list(
            InsurancePayer.objects.filter(is_active=True).values_list("code", flat=True)
        )
        return {
            "eligible": False,
            "reason": (
                f"Payer '{payer_id}' not found or inactive. "
                f"Available payers: {', '.join(available)}"
            ),
        }

    today = date.today()
    policy = (
        PatientInsurance.objects.filter(
            patient_id=patient_id,
            payer=payer,
            enrollment_start__lte=today,
        )
        .filter(
            models.Q(enrollment_end__isnull=True) | models.Q(enrollment_end__gte=today)
        )
        .first()
    )

    if not policy:
        return {
            "eligible": False,
            "reason": f"Patient '{patient_id}' has no active insurance with {payer.name}.",
        }

    return {
        "eligible": True,
        "patient_id": patient_id,
        "payer": {"id": payer.pk, "name": payer.name},
        "insurance_type": policy.insurance_type,
        "insurance_type_description": (
            "HMO - Requires referral from primary care physician for specialists"
            if policy.insurance_type == "HMO"
            else "PPO - Can see specialists directly without referral"
        ),
        "member_id": policy.member_id,
        "enrollment_start": policy.enrollment_start.isoformat(),
        "enrollment_end": (
            policy.enrollment_end.isoformat() if policy.enrollment_end else None
        ),
    }
