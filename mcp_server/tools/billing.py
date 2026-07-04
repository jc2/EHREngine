from datetime import date

from django.db import models

from mcp_server.auth import enforce_patient_scope
from mcp_server.schemas.auth_mapping import billing_auth_error
from mcp_server.schemas.responses import EstimateVisitCostResult


def estimate_visit_cost(patient_id: str, specialty: str) -> EstimateVisitCostResult:
    """Estimate the patient's fixed out-of-pocket cost for a visit to a specialty.

    Deterministic engine (no LLM math): the cost is resolved from the BillingRule
    table via a tiered cascade and returns the first match:

      Tier 1 — exact:    the patient's insurance_type + the specialty.
      Tier 2 — specialty default: the specialty regardless of insurance.
      Tier 3 — global fallback: a single flat rule when nothing else matches.

    The patient's insurance_type is derived from their active coverage on file
    (the same source as verify_insurance_eligibility), so the LLM only supplies
    the specialty — Django computes the auditable dollar amount.

    Args:
        patient_id: The external patient identifier (e.g. "PAT-001").
        specialty: The specialty code (e.g. "CARDIOLOGY") or name
            (e.g. "Cardiology"). Case-insensitive. Use list_medical_specialties
            to discover valid values.

    Returns:
        A dict with:
        - success (bool): Whether a cost could be resolved.
        - estimated_cost (float): The fixed cost in dollars (if success).
        - currency (str): "USD".
        - rule_tier (int): Which cascade tier matched (1, 2, or 3).
        - rule_tier_label (str): Human-readable tier description.
        - insurance_type (str|null): The patient's insurance type used for Tier 1.
        - specialty (str|null): The normalized specialty name resolved.
        - error (str): Explanation if success is False.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return billing_auth_error(auth_error)

    from clinic.models import (
        BillingRule,
        MedicalDepartment,
        PatientInsurance,
    )

    today = date.today()
    policy = (
        PatientInsurance.objects.filter(
            patient_id=patient_id,
            enrollment_start__lte=today,
        )
        .filter(
            models.Q(enrollment_end__isnull=True) | models.Q(enrollment_end__gte=today)
        )
        .order_by("-enrollment_start")
        .first()
    )
    insurance_type = policy.insurance_type if policy else None

    department = None
    if specialty:
        if specialty.isdigit():
            department = MedicalDepartment.objects.filter(pk=specialty).first()
        else:
            s = specialty.strip()
            department = (
                MedicalDepartment.objects.filter(code__iexact=s).first()
                or MedicalDepartment.objects.filter(name__iexact=s).first()
            )

        if department is None:
            available = list(
                MedicalDepartment.objects.filter(is_active=True).values_list("code", flat=True)
            )
            return EstimateVisitCostResult(
                success=False,
                error=(
                    f"Specialty '{specialty}' not found. "
                    f"Available specialties: {', '.join(available)}"
                ),
            )

    rule = None
    rule_tier = None

    if insurance_type and department:
        rule = BillingRule.objects.filter(
            insurance_type=insurance_type, specialty=department
        ).first()
        if rule:
            rule_tier = 1

    if rule is None and department:
        rule = BillingRule.objects.filter(
            insurance_type__isnull=True, specialty=department
        ).first()
        if rule:
            rule_tier = 2

    if rule is None:
        rule = BillingRule.objects.filter(
            insurance_type__isnull=True, specialty__isnull=True
        ).first()
        if rule:
            rule_tier = 3

    if rule is None:
        return EstimateVisitCostResult(
            success=False,
            error=(
                "No billing rule matched and no global fallback rule is configured. "
                "Seed a Tier 3 (insurance_type NULL, specialty NULL) BillingRule."
            ),
        )

    tier_labels = {
        1: "Exact match (insurance + specialty)",
        2: "Specialty default (any insurance)",
        3: "Global fallback",
    }

    return EstimateVisitCostResult(
        success=True,
        patient_id=patient_id,
        estimated_cost=float(rule.fixed_cost),
        currency="USD",
        rule_tier=rule_tier,
        rule_tier_label=tier_labels[rule_tier],
        insurance_type=insurance_type,
        specialty=department.name if department else None,
    )
