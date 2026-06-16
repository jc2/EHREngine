"""
Catch-up verification tests (Epics 2.5 / 3):
  - Deterministic billing engine tiered cascade (estimate_visit_cost).
  - Cross-patient enforcement at the MCP boundary (X-Patient-Id header).
"""
from datetime import date, timedelta

import pytest

from mcp_server import auth
from mcp_server.tools.billing import estimate_visit_cost
from mcp_server.tools.insurance import verify_insurance_eligibility


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def general_practice():
    from clinic.models import MedicalDepartment

    return MedicalDepartment.objects.create(
        code="GENERAL_PRACTICE", name="General Practice", is_active=True
    )


@pytest.fixture
def patient_insurance_hmo(bcbs):
    from clinic.models import PatientInsurance

    return PatientInsurance.objects.create(
        patient_id="PAT-001",
        payer=bcbs,
        insurance_type="HMO",
        member_id="MBR-HMO-1",
        enrollment_start=date.today() - timedelta(days=180),
        enrollment_end=None,
    )


@pytest.fixture
def billing_rules(cardiology, general_practice):
    from clinic.models import BillingRule

    BillingRule.objects.create(insurance_type="HMO", specialty=cardiology, fixed_cost="40.00")
    BillingRule.objects.create(insurance_type="PPO", specialty=cardiology, fixed_cost="60.00")
    BillingRule.objects.create(insurance_type=None, specialty=general_practice, fixed_cost="25.00")
    BillingRule.objects.create(insurance_type=None, specialty=None, fixed_cost="50.00")


@pytest.fixture
def auth_scope():
    """Set/reset the trusted X-Patient-Id contextvar around a test."""
    tokens = []

    def _set(patient_id):
        tokens.append(auth._current_patient_id.set(patient_id))

    yield _set

    for token in reversed(tokens):
        auth._current_patient_id.reset(token)


# ---------------------------------------------------------------------------
# Billing cascade: Tier 1 -> 2 -> 3
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestBillingCascade:
    def test_tier1_exact_match(self, patient_insurance_hmo, billing_rules, cardiology):
        # HMO patient + Cardiology -> exact rule -> $40.
        result = estimate_visit_cost("PAT-001", "CARDIOLOGY")

        assert result["success"] is True
        assert result["estimated_cost"] == 40.0
        assert result["rule_tier"] == 1
        assert result["insurance_type"] == "HMO"

    def test_tier2_specialty_default(self, patient_insurance_hmo, billing_rules):
        # No HMO+General rule exists -> falls to the specialty default ($25).
        result = estimate_visit_cost("PAT-001", "General Practice")

        assert result["success"] is True
        assert result["estimated_cost"] == 25.0
        assert result["rule_tier"] == 2

    def test_tier3_global_fallback(self, patient_insurance_hmo, billing_rules, dermatology):
        # Dermatology has no rule at all -> global fallback ($50).
        result = estimate_visit_cost("PAT-001", "DERMATOLOGY")

        assert result["success"] is True
        assert result["estimated_cost"] == 50.0
        assert result["rule_tier"] == 3

    def test_no_insurance_uses_specialty_or_global(self, billing_rules):
        # Patient with no insurance on file can't match Tier 1, but still resolves.
        result = estimate_visit_cost("PAT-404", "General Practice")

        assert result["success"] is True
        assert result["estimated_cost"] == 25.0
        assert result["rule_tier"] == 2


# ---------------------------------------------------------------------------
# Cross-patient enforcement
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCrossPatientEnforcement:
    def test_foreign_patient_rejected(self, auth_scope, patient_insurance_ppo, bcbs):
        # Session authenticated as PAT-001; tool asked about PAT-002 -> denied.
        auth_scope("PAT-001")
        result = verify_insurance_eligibility("PAT-002", "BCBS")

        assert result["success"] is False
        assert result["error_code"] == "cross_patient_denied"
        # Must never leak the foreign patient's data.
        assert "member_id" not in result

    def test_matching_patient_allowed(self, auth_scope, patient_insurance_ppo, bcbs):
        auth_scope("PAT-001")
        result = verify_insurance_eligibility("PAT-001", "BCBS")

        assert result["eligible"] is True
        assert result["insurance_type"] == "PPO"

    def test_no_header_not_enforced(self, patient_insurance_ppo, bcbs):
        # Direct call (no trusted header) is allowed — enforcement is header-driven.
        result = verify_insurance_eligibility("PAT-001", "BCBS")

        assert result["eligible"] is True

    def test_billing_cross_patient_rejected(self, auth_scope, billing_rules):
        auth_scope("PAT-001")
        result = estimate_visit_cost("PAT-002", "CARDIOLOGY")

        assert result["success"] is False
        assert result["error_code"] == "cross_patient_denied"
        assert "estimated_cost" not in result
