from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import (
    Appointment,
    BillingRule,
    Doctor,
    DoctorSchedule,
    HumanEscalation,
    InsurancePayer,
    MedicalDepartment,
    Medication,
    Patient,
    PatientInsurance,
    Prescription,
    RefillRequest,
)


@admin.register(Patient)
class PatientAdmin(ModelAdmin):
    list_display = ["code", "first_name", "last_name", "phone_number", "identification_number", "created_at"]
    list_display_links = ["code"]
    search_fields = ["code", "first_name", "last_name", "phone_number", "identification_number"]


@admin.register(MedicalDepartment)
class MedicalDepartmentAdmin(ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_display_links = ["name"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(InsurancePayer)
class InsurancePayerAdmin(ModelAdmin):
    list_display = ["name", "code", "is_active", "created_at"]
    list_display_links = ["name"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(PatientInsurance)
class PatientInsuranceAdmin(ModelAdmin):
    list_display = ["patient", "payer", "insurance_type", "member_id", "enrollment_start", "enrollment_end"]
    list_display_links = ["patient"]
    list_filter = ["insurance_type", "payer"]
    search_fields = ["patient__code", "member_id"]
    autocomplete_fields = ["patient"]


@admin.register(Doctor)
class DoctorAdmin(ModelAdmin):
    list_display = ["first_name", "last_name", "specialty", "license_number", "is_active"]
    list_display_links = ["first_name", "last_name"]
    list_filter = ["specialty", "is_active"]
    search_fields = ["first_name", "last_name", "license_number"]


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(ModelAdmin):
    list_display = ["doctor", "date", "start_time", "end_time"]
    list_display_links = ["doctor"]
    list_filter = ["date", "doctor__specialty"]
    search_fields = ["doctor__last_name"]
    autocomplete_fields = ["doctor"]


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    list_display = ["public_id", "patient", "doctor", "schedule_slot", "status", "notes", "created_at"]
    list_display_links = ["public_id"]
    list_filter = ["status", "doctor__specialty"]
    search_fields = ["public_id", "patient__code"]
    autocomplete_fields = ["doctor", "patient"]
    readonly_fields = ["public_id"]


@admin.register(Medication)
class MedicationAdmin(ModelAdmin):
    list_display = ["name", "strength", "form", "is_controlled_substance"]
    list_display_links = ["name"]
    search_fields = ["name"]
    list_filter = ["form", "is_controlled_substance"]


class PrescriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = "__all__"

    def clean_refills_authorized(self):
        value = self.cleaned_data["refills_authorized"]
        if not self.instance.pk:
            return value

        old_authorized, old_remaining = (
            Prescription.objects.filter(pk=self.instance.pk)
            .values_list("refills_authorized", "refills_remaining")
            .first()
        )
        if old_authorized is None:
            return value

        refills_used = old_authorized - old_remaining
        if value < refills_used:
            raise ValidationError(
                f"Cannot be less than refills already dispensed ({refills_used})."
            )
        return value


@admin.register(Prescription)
class PrescriptionAdmin(ModelAdmin):
    form = PrescriptionAdminForm
    list_display = [
        "id", "patient", "medication", "prescriber", "sig", "quantity",
        "refills_authorized", "refills_used_display", "status", "date_written",
        "expiration_date", "pharmacy",
    ]
    list_display_links = ["id"]
    search_fields = ["medication__name", "patient__code", "id"]
    list_filter = ["status", "medication", "prescriber__specialty"]
    list_editable = ["refills_authorized"]
    autocomplete_fields = ["medication", "prescriber", "patient"]
    readonly_fields = ["refills_used_display"]
    fields = [
        "patient",
        "medication",
        "prescriber",
        "sig",
        "quantity",
        "refills_authorized",
        "refills_used_display",
        "status",
        "date_written",
        "expiration_date",
        "pharmacy",
    ]

    @admin.display(description="Refills dispensed")
    def refills_used_display(self, obj):
        return obj.refills_used


class RefillRequestAdminForm(forms.ModelForm):
    class Meta:
        model = RefillRequest
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            return cleaned_data

        previous_status = (
            RefillRequest.objects.filter(pk=self.instance.pk)
            .values_list("status", flat=True)
            .first()
        )
        new_status = cleaned_data.get("status")
        if previous_status == "DISPENSED" and new_status != "DISPENSED":
            raise ValidationError(
                "Cannot change status after the refill has been dispensed."
            )
        return cleaned_data


@admin.register(RefillRequest)
class RefillRequestAdmin(ModelAdmin):
    form = RefillRequestAdminForm
    list_display = [
        "public_id",
        "prescription",
        "status",
        "requested_at",
        "authorization_status",
        "decision_reason",
        "processed_at",
    ]
    list_display_links = ["public_id"]
    list_filter = ["status", "authorization_status", "requested_at"]
    list_editable = ["status", "authorization_status"]
    search_fields = [
        "public_id",
        "prescription__patient__code",
        "prescription__medication__name",
    ]
    readonly_fields = ["public_id", "requested_at"]
    autocomplete_fields = ["prescription"]


@admin.register(BillingRule)
class BillingRuleAdmin(ModelAdmin):
    list_display = ["id", "insurance_type", "specialty", "fixed_cost"]
    list_display_links = ["id"]
    list_filter = ["insurance_type", "specialty"]
    autocomplete_fields = ["specialty"]


@admin.register(HumanEscalation)
class HumanEscalationAdmin(ModelAdmin):
    list_display = [
        "public_id",
        "patient",
        "reported_name",
        "status",
        "short_initial_intent",
        "created_at",
        "resolved_at",
    ]
    list_display_links = ["public_id"]
    list_filter = ["status", "created_at"]
    list_editable = ["status"]
    search_fields = [
        "public_id",
        "patient__code",
        "reported_name",
        "reported_phone",
        "reported_identification_number",
    ]
    readonly_fields = ["public_id", "created_at"]
    autocomplete_fields = ["patient"]

    @admin.display(description="Initial intent")
    def short_initial_intent(self, obj):
        if len(obj.initial_intent) <= 60:
            return obj.initial_intent
        return format_html("{}&hellip;", obj.initial_intent[:60])
