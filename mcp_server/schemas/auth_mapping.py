"""Map auth scope errors into tool-specific Pydantic response models."""

from mcp_server.schemas.responses import (
    AuthScopeError,
    CheckPendingEscalationResult,
    CheckRefillStatusResult,
    EstimateVisitCostResult,
    ListPatientPrescriptionsResult,
    ReportHumanEscalationResult,
    RequestMedicationRefillResult,
    ScheduleAppointmentResult,
    VerifyInsuranceEligibilityResult,
)


def schedule_auth_error(error: AuthScopeError) -> ScheduleAppointmentResult:
    return ScheduleAppointmentResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def verify_auth_error(error: AuthScopeError) -> VerifyInsuranceEligibilityResult:
    return VerifyInsuranceEligibilityResult(
        eligible=error.eligible,
        success=error.success,
        error=error.error,
        error_code=error.error_code,
    )


def billing_auth_error(error: AuthScopeError) -> EstimateVisitCostResult:
    return EstimateVisitCostResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def prescriptions_auth_error(error: AuthScopeError) -> ListPatientPrescriptionsResult:
    return ListPatientPrescriptionsResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def refill_auth_error(error: AuthScopeError) -> RequestMedicationRefillResult:
    return RequestMedicationRefillResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def check_refill_auth_error(error: AuthScopeError) -> CheckRefillStatusResult:
    return CheckRefillStatusResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def report_escalation_auth_error(error: AuthScopeError) -> ReportHumanEscalationResult:
    return ReportHumanEscalationResult(
        success=False,
        error=error.error,
        error_code=error.error_code,
    )


def check_escalation_auth_error(error: AuthScopeError) -> CheckPendingEscalationResult:
    return CheckPendingEscalationResult(
        has_pending=False,
        pending_count=0,
        success=error.success,
        error=error.error,
        error_code=error.error_code,
    )
