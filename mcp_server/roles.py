from .tools.availability import check_provider_availability
from .tools.billing import estimate_visit_cost
from .tools.catalog import list_insurance_payers, list_medical_specialties
from .tools.escalations import check_pending_escalation, report_human_escalation
from .tools.insurance import verify_insurance_eligibility
from .tools.patients import identify_patient
from .tools.refills import (
    check_refill_status,
    list_patient_prescriptions,
    request_medication_refill,
)
from .tools.scheduling import schedule_appointment

# /mcp/public — excludes request_medication_refill and report_human_escalation
PUBLIC_TOOLS = [
    list_insurance_payers,
    list_medical_specialties,
    identify_patient,
    verify_insurance_eligibility,
    check_provider_availability,
    schedule_appointment,
    list_patient_prescriptions,
    check_refill_status,
    estimate_visit_cost,
    check_pending_escalation,
]

# /mcp/all — full tool surface
ALL_TOOLS = PUBLIC_TOOLS + [
    request_medication_refill,
    report_human_escalation,
]
