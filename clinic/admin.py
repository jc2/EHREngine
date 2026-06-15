from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    Appointment,
    Doctor,
    DoctorSchedule,
    InsurancePayer,
    MedicalDepartment,
    PatientInsurance,
)


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
    list_display = ["patient_id", "payer", "insurance_type", "member_id", "enrollment_start", "enrollment_end"]
    list_display_links = ["patient_id"]
    list_filter = ["insurance_type", "payer"]
    search_fields = ["patient_id", "member_id"]


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
    list_display = ["patient_id", "doctor", "schedule_slot", "status", "notes", "created_at"]
    list_display_links = ["patient_id"]
    list_filter = ["status", "doctor__specialty"]
    search_fields = ["patient_id"]
    autocomplete_fields = ["doctor"]
