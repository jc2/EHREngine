"""Pydantic response models for MCP tools (structured outputSchema metadata)."""

from typing import Literal

from pydantic import BaseModel, Field


class AuthScopeError(BaseModel):
    success: bool = False
    eligible: bool = False
    error: str
    error_code: Literal["cross_patient_denied"] = "cross_patient_denied"


class PayerSummary(BaseModel):
    id: str
    code: str
    name: str


class ListInsurancePayersResult(BaseModel):
    total: int
    payers: list[PayerSummary]


class SpecialtySummary(BaseModel):
    id: str
    code: str
    name: str
    active_doctors: int


class ListMedicalSpecialtiesResult(BaseModel):
    total: int
    specialties: list[SpecialtySummary]


class IdentifyPatientResult(BaseModel):
    success: bool
    patient_code: str | None = None
    patient_name: str | None = None
    pending_appointments: list["PendingAppointmentSummary"] = Field(default_factory=list)
    pending_refill_requests: list["PendingRefillRequestSummary"] = Field(default_factory=list)
    pending_escalations: list["PendingEscalationCase"] = Field(default_factory=list)
    insurance_policies: list["PatientInsuranceSummary"] = Field(default_factory=list)
    error: str | None = None


class PendingAppointmentSummary(BaseModel):
    public_id: str
    detail_page_url: str = Field(
        description="Full URL where the patient or staff can view this appointment."
    )
    date: str
    start_time: str
    end_time: str
    doctor_name: str
    specialty: str
    status: str


class PendingRefillRequestSummary(BaseModel):
    public_id: str
    detail_page_url: str = Field(
        description="Full URL where the patient or staff can view this refill request."
    )
    medication: str
    status: str
    authorization_status: str
    requested_at: str


class PatientInsuranceSummary(BaseModel):
    payer_name: str
    payer_code: str
    insurance_type: str
    member_id: str


class PayerInfo(BaseModel):
    id: int
    name: str


class VerifyInsuranceEligibilityResult(BaseModel):
    eligible: bool
    reason: str | None = None
    success: bool | None = None
    error: str | None = None
    error_code: str | None = None
    patient_id: str | None = None
    payer: PayerInfo | None = None
    insurance_type: str | None = None
    insurance_type_description: str | None = None
    member_id: str | None = None
    enrollment_start: str | None = None
    enrollment_end: str | None = None


class AvailableSlot(BaseModel):
    doctor_id: str
    doctor_name: str
    specialty: str
    date: str
    start_time: str
    end_time: str


class CheckProviderAvailabilityResult(BaseModel):
    specialty: str
    date: str
    total_available: int
    available_slots: list[AvailableSlot]
    error: str | None = None


class AppointmentDetails(BaseModel):
    public_id: str
    detail_page_url: str = Field(
        description="Full URL where the patient or staff can view this appointment."
    )
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    date: str
    start_time: str
    end_time: str
    status: str
    notes: str


class ScheduleAppointmentResult(BaseModel):
    success: bool
    appointment: AppointmentDetails | None = None
    error: str | None = None
    error_code: str | None = None


class PrescriptionSummary(BaseModel):
    prescription_id: str
    medication: str
    sig: str
    quantity: int
    refills_remaining: int
    refills_authorized: int
    status: str
    date_written: str
    expiration_date: str
    is_controlled_substance: bool


class ListPatientPrescriptionsResult(BaseModel):
    success: bool
    patient_id: str | None = None
    total: int | None = None
    prescriptions: list[PrescriptionSummary] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None


class RequestMedicationRefillResult(BaseModel):
    success: bool
    public_id: str | None = None
    detail_page_url: str | None = Field(
        default=None,
        description="Full URL where the patient or staff can view this refill request.",
    )
    refill_request_id: int | None = None
    status: str | None = None
    reason: str | None = None
    medication: str | None = None
    refills_remaining: int | None = None
    requires_provider_review: bool | None = None
    patient_id: str | None = None
    error: str | None = None
    error_code: str | None = None


class CheckRefillStatusResult(BaseModel):
    success: bool
    refill_id: str | None = None
    authorization_status: str | None = None
    is_authorized: bool | None = None
    status: str | None = None
    reason: str | None = None
    medication: str | None = None
    patient_id: str | None = None
    requested_at: str | None = None
    processed_at: str | None = None
    detail_page_url: str | None = Field(
        default=None,
        description="Full URL where the patient or staff can view this refill request.",
    )
    error: str | None = None
    error_code: str | None = None


class EstimateVisitCostResult(BaseModel):
    success: bool
    patient_id: str | None = None
    estimated_cost: float | None = None
    currency: str | None = None
    rule_tier: int | None = None
    rule_tier_label: str | None = None
    insurance_type: str | None = None
    specialty: str | None = None
    error: str | None = None
    error_code: str | None = None


class ReportHumanEscalationResult(BaseModel):
    success: bool
    escalation_id: str | None = None
    status: str | None = None
    detail_page_url: str | None = Field(
        default=None,
        description="Full URL where the patient or staff can view this escalation case.",
    )
    error: str | None = None
    error_code: str | None = None


class PendingEscalationCase(BaseModel):
    escalation_id: str
    initial_intent: str
    created_at: str
    detail_page_url: str = Field(
        description="Full URL where the patient or staff can view this escalation case."
    )


class CheckPendingEscalationResult(BaseModel):
    has_pending: bool
    pending_count: int
    cases: list[PendingEscalationCase] = Field(default_factory=list)
    error: str | None = None
    success: bool | None = None
    error_code: str | None = None
