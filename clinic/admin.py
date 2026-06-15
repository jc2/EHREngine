from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Appointment, Doctor, DoctorSchedule, InsurancePayer, PatientInsurance


class InsurancePayerViewSet(SnippetViewSet):
    model = InsurancePayer
    icon = "doc-full"
    menu_label = "Insurance Payers"
    menu_name = "insurance_payers"
    list_display = ["name", "code", "is_active"]
    search_fields = ["name", "code"]


class PatientInsuranceViewSet(SnippetViewSet):
    model = PatientInsurance
    icon = "user"
    menu_label = "Patient Insurance"
    menu_name = "patient_insurance"
    list_display = ["patient_id", "payer", "insurance_type", "enrollment_start", "enrollment_end"]
    list_filter = ["insurance_type", "payer"]
    search_fields = ["patient_id", "member_id"]


class DoctorViewSet(SnippetViewSet):
    model = Doctor
    icon = "group"
    menu_label = "Doctors"
    menu_name = "doctors"
    list_display = ["__str__", "specialty", "license_number", "is_active"]
    list_filter = ["specialty", "is_active"]
    search_fields = ["first_name", "last_name", "license_number"]


class DoctorScheduleViewSet(SnippetViewSet):
    model = DoctorSchedule
    icon = "date"
    menu_label = "Doctor Schedules"
    menu_name = "doctor_schedules"
    list_display = ["doctor", "date", "start_time", "end_time"]
    list_filter = ["date", "doctor__specialty"]


class AppointmentViewSet(SnippetViewSet):
    model = Appointment
    icon = "calendar-alt"
    menu_label = "Appointments"
    menu_name = "appointments"
    list_display = ["patient_id", "doctor", "status", "created_at"]
    list_filter = ["status", "doctor__specialty"]
    search_fields = ["patient_id"]


register_snippet(InsurancePayerViewSet)
register_snippet(PatientInsuranceViewSet)
register_snippet(DoctorViewSet)
register_snippet(DoctorScheduleViewSet)
register_snippet(AppointmentViewSet)
