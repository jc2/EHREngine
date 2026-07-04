from datetime import date, time, timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Appointment,
    Doctor,
    DoctorSchedule,
    HumanEscalation,
    MedicalDepartment,
    RefillRequest,
)

SCHEDULE_START_HOUR = 8
SCHEDULE_END_HOUR = 12
SLOT_MINUTES = 30


def _generate_slots(doctors, target_date):
    created = 0
    for doctor in doctors:
        for hour in range(SCHEDULE_START_HOUR, SCHEDULE_END_HOUR):
            for minute in (0, SLOT_MINUTES):
                start = time(hour, minute)
                end_minute = minute + SLOT_MINUTES
                end_hour = hour + (end_minute // 60)
                end = time(end_hour, end_minute % 60)

                _, was_created = DoctorSchedule.objects.get_or_create(
                    doctor=doctor,
                    date=target_date,
                    start_time=start,
                    defaults={"end_time": end},
                )
                if was_created:
                    created += 1
    return created


@require_POST
def generate_schedules(request):
    date_str = request.POST.get("date")
    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)

    scope = request.POST.get("scope", "all")
    scope_id = request.POST.get("scope_id", "")

    if scope == "doctor":
        doctors = Doctor.objects.filter(pk=scope_id, is_active=True)
    elif scope == "specialty":
        doctors = Doctor.objects.filter(specialty__code=scope_id, is_active=True)
    else:
        doctors = Doctor.objects.filter(is_active=True)

    created = _generate_slots(doctors, target_date)

    from django.shortcuts import redirect
    base_url = f"?date={target_date.isoformat()}"
    if scope == "specialty" and scope_id:
        base_url += f"&specialty={scope_id}"
    return redirect(f"/{base_url}")


def schedule_dashboard(request):
    date_str = request.GET.get("date")
    try:
        selected_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        selected_date = date.today()

    specialty_filter = request.GET.get("specialty", "")

    all_specialties = MedicalDepartment.objects.filter(is_active=True).order_by("name")

    if specialty_filter:
        filter_depts = all_specialties.filter(code=specialty_filter)
    else:
        filter_depts = all_specialties

    slots = (
        DoctorSchedule.objects.filter(date=selected_date)
        .select_related("doctor", "doctor__specialty")
        .prefetch_related("appointment")
        .order_by("doctor__specialty__name", "doctor__last_name", "start_time")
    )

    booked_map = {}
    appointments = Appointment.objects.filter(
        schedule_slot__date=selected_date,
        status__in=["SCHEDULED", "COMPLETED"],
    ).select_related("schedule_slot")
    for appt in appointments:
        booked_map[appt.schedule_slot_id] = appt

    dept_doctors = {}
    for dept in filter_depts:
        active_doctors = dept.doctors.filter(is_active=True).order_by("last_name", "first_name")
        if active_doctors.exists():
            dept_doctors[dept.pk] = list(active_doctors)

    departments = []
    for dept in filter_depts:
        if dept.pk not in dept_doctors:
            continue

        spec_slots = [s for s in slots if s.doctor.specialty_id == dept.pk]

        doctors_dict = {}
        for slot in spec_slots:
            doc = slot.doctor
            if doc.pk not in doctors_dict:
                doctors_dict[doc.pk] = {
                    "doctor": doc,
                    "slots": [],
                }
            appt = booked_map.get(slot.pk)
            doctors_dict[doc.pk]["slots"].append({
                "slot": slot,
                "appointment": appt,
                "is_booked": appt is not None,
            })

        has_slots = len(spec_slots) > 0
        doctors_without_slots = []
        if has_slots:
            doctors_with_slot_ids = {s.doctor_id for s in spec_slots}
            doctors_without_slots = [d for d in dept_doctors[dept.pk] if d.pk not in doctors_with_slot_ids]

        departments.append({
            "code": dept.code,
            "name": dept.name,
            "doctors": list(doctors_dict.values()),
            "has_slots": has_slots,
            "doctors_without_slots": doctors_without_slots,
        })

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    total_doctors = sum(len(d["doctors"]) for d in departments)

    return render(request, "clinic/schedule_dashboard.html", {
        "selected_date": selected_date,
        "prev_date": prev_date,
        "next_date": next_date,
        "departments": departments,
        "total_doctors": total_doctors,
        "all_specialties": all_specialties,
        "specialty_filter": specialty_filter,
    })


def appointment_detail(request, public_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient", "doctor", "doctor__specialty", "schedule_slot"
        ),
        public_id=public_id,
    )
    return render(request, "clinic/appointment_detail.html", {"appointment": appointment})


def refill_detail(request, public_id):
    refill = get_object_or_404(
        RefillRequest.objects.select_related(
            "prescription",
            "prescription__medication",
            "prescription__patient",
            "prescription__prescriber",
        ),
        public_id=public_id,
    )
    return render(request, "clinic/refill_detail.html", {"refill": refill})


def escalation_detail(request, public_id):
    escalation = get_object_or_404(
        HumanEscalation.objects.select_related("patient"),
        public_id=public_id,
    )
    return render(request, "clinic/escalation_detail.html", {"escalation": escalation})


@require_GET
def lookup_appointment(request):
    public_id = request.GET.get("code", "").strip()
    if not public_id:
        messages.error(request, "Enter your appointment reference code.")
        return redirect("schedule-dashboard")
    if Appointment.objects.filter(public_id=public_id).exists():
        return redirect("appointment-detail", public_id=public_id)
    messages.error(request, f"No appointment found with reference “{public_id}”.")
    return redirect("schedule-dashboard")


@require_GET
def lookup_refill(request):
    public_id = request.GET.get("code", "").strip()
    if not public_id:
        messages.error(request, "Enter your refill request reference code.")
        return redirect("schedule-dashboard")
    if RefillRequest.objects.filter(public_id=public_id).exists():
        return redirect("refill-detail", public_id=public_id)
    messages.error(request, f"No refill request found with reference “{public_id}”.")
    return redirect("schedule-dashboard")


@require_GET
def lookup_escalation(request):
    public_id = request.GET.get("code", "").strip()
    if not public_id:
        messages.error(request, "Enter your escalation reference code.")
        return redirect("schedule-dashboard")
    if HumanEscalation.objects.filter(public_id=public_id).exists():
        return redirect("escalation-detail", public_id=public_id)
    messages.error(request, f"No escalation found with reference “{public_id}”.")
    return redirect("schedule-dashboard")
