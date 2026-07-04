from mcp_server.auth import enforce_patient_scope
from mcp_server.schemas.auth_mapping import (
    check_escalation_auth_error,
    report_escalation_auth_error,
)
from mcp_server.schemas.responses import (
    CheckPendingEscalationResult,
    PendingEscalationCase,
    ReportHumanEscalationResult,
)
from mcp_server.tools.urls import absolute_view_url


def report_human_escalation(
    reported_name: str,
    reported_phone: str,
    reported_identification_number: str,
    initial_intent: str,
    failure_reason: str,
    patient_id: str = "",
    agent_notes: str = "",
) -> ReportHumanEscalationResult:
    """Report a human escalation when the agent cannot complete a patient request.

    Use this tool when automated workflows fail and a human staff member needs to
    follow up. Always include the demographic snapshot the agent collected, even
    if the patient was not identified in the system.

    Args:
        reported_name: Patient full name collected by the agent.
        reported_phone: Patient phone number collected by the agent.
        reported_identification_number: Patient ID collected by the agent.
        initial_intent: What the patient was trying to accomplish.
        failure_reason: Why the agent could not complete the request.
        patient_id: Optional patient code (e.g. "PAT-001") if already identified.
        agent_notes: Optional additional context from the conversation.

    Returns:
        A dict with:
        - success (bool): Whether the escalation was recorded.
        - escalation_id (str): Public ID of the created escalation.
        - status (str): Always "NEW" on success.
        - detail_page_url (str): Full URL where the patient or staff can view the escalation case.
        - error (str): Reason if the report failed.
    """
    if not reported_name.strip():
        return ReportHumanEscalationResult(success=False, error="reported_name is required.")
    if not reported_phone.strip():
        return ReportHumanEscalationResult(success=False, error="reported_phone is required.")
    if not reported_identification_number.strip():
        return ReportHumanEscalationResult(
            success=False, error="reported_identification_number is required."
        )
    if not initial_intent.strip():
        return ReportHumanEscalationResult(success=False, error="initial_intent is required.")
    if not failure_reason.strip():
        return ReportHumanEscalationResult(success=False, error="failure_reason is required.")

    from clinic.models import HumanEscalation, Patient

    patient = None
    if patient_id:
        auth_error = enforce_patient_scope(patient_id)
        if auth_error:
            return report_escalation_auth_error(auth_error)

        try:
            patient = Patient.objects.get(code=patient_id)
        except Patient.DoesNotExist:
            available = sorted(Patient.objects.values_list("code", flat=True))
            return ReportHumanEscalationResult(
                success=False,
                error=(
                    f"Patient '{patient_id}' not found. "
                    f"Available patient codes: {', '.join(available)}"
                ),
            )

    escalation = HumanEscalation.objects.create(
        patient=patient,
        reported_name=reported_name.strip(),
        reported_phone=reported_phone.strip(),
        reported_identification_number=reported_identification_number.strip(),
        initial_intent=initial_intent.strip(),
        failure_reason=failure_reason.strip(),
        agent_notes=agent_notes.strip(),
    )

    return ReportHumanEscalationResult(
        success=True,
        escalation_id=escalation.public_id,
        status=escalation.status,
        detail_page_url=absolute_view_url(escalation.view_url),
    )


def check_pending_escalation(patient_id: str) -> CheckPendingEscalationResult:
    """Check whether a patient has pending (NEW) human escalation cases.

    Use this before retrying a workflow to avoid duplicate escalations. Only
    open (NEW) cases linked to the patient are returned; resolved cases are ignored.

    Args:
        patient_id: Patient code (e.g. "PAT-001"). Required.

    Returns:
        A dict with:
        - has_pending (bool): Whether any NEW escalation cases exist.
        - pending_count (int): Number of matching NEW cases.
        - cases (list[dict]): Matching cases with escalation_id, initial_intent,
          created_at, and detail_page_url. Empty when has_pending is false.
        - error (str): If patient_id is missing or the patient was not found.
    """
    from clinic.models import EscalationStatus, HumanEscalation, Patient

    if not patient_id.strip():
        return CheckPendingEscalationResult(
            has_pending=False,
            pending_count=0,
            error="patient_id is required.",
        )

    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return check_escalation_auth_error(auth_error)

    patient_code = patient_id.strip()
    if not Patient.objects.filter(code=patient_code).exists():
        available = sorted(Patient.objects.values_list("code", flat=True))
        return CheckPendingEscalationResult(
            has_pending=False,
            pending_count=0,
            error=(
                f"Patient '{patient_code}' not found. "
                f"Available patient codes: {', '.join(available)}"
            ),
        )

    pending = HumanEscalation.objects.filter(
        patient_id=patient_code,
        status=EscalationStatus.NEW,
    )

    cases = [
        PendingEscalationCase(
            escalation_id=escalation.public_id,
            initial_intent=escalation.initial_intent,
            created_at=escalation.created_at.isoformat(),
            detail_page_url=absolute_view_url(escalation.view_url),
        )
        for escalation in pending
    ]

    return CheckPendingEscalationResult(
        has_pending=len(cases) > 0,
        pending_count=len(cases),
        cases=cases,
    )
