from datetime import date as date_type, datetime
from typing import Any

from mcp_server.auth import enforce_patient_scope


def schedule_appointment(
    patient_id: str, doctor_id: str, date: str, time: str
) -> dict[str, Any]:
    """Schedule a 30-minute appointment for a patient with a specific doctor.

    Use this tool AFTER verifying insurance eligibility and checking provider
    availability. The typical workflow is:
      1. verify_insurance_eligibility — confirm active coverage
      2. check_provider_availability — find open slots
      3. schedule_appointment — book the slot

    Args:
        patient_id: The external patient identifier (e.g. "PAT-001").
        doctor_id: The doctor's ID (from check_provider_availability results).
        date: Appointment date in YYYY-MM-DD format (e.g. "2026-06-15").
        time: Start time in HH:MM 24-hour format (e.g. "09:30").
              Must match an available slot from check_provider_availability.

    Returns:
        A dict with:
        - success (bool): Whether the appointment was created.
        - appointment (dict): Details including id, patient_id, doctor,
          specialty, date, start_time, end_time, and status.
        - error (str): Reason for failure if success is False.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return auth_error

    from django.db import IntegrityError

    from clinic.models import Appointment, Doctor, DoctorSchedule

    try:
        appt_date = date_type.fromisoformat(date)
    except ValueError:
        return {"success": False, "error": f"Invalid date format '{date}'. Use YYYY-MM-DD."}

    try:
        appt_time = datetime.strptime(time, "%H:%M").time()
    except ValueError:
        return {"success": False, "error": f"Invalid time format '{time}'. Use HH:MM (24h)."}

    try:
        if doctor_id.isdigit():
            doctor = Doctor.objects.get(pk=doctor_id, is_active=True)
        else:
            doctor = Doctor.objects.get(last_name__iexact=doctor_id.strip(), is_active=True)
    except Doctor.DoesNotExist:
        return {"success": False, "error": f"Doctor '{doctor_id}' not found or inactive."}
    except Doctor.MultipleObjectsReturned:
        matches = Doctor.objects.filter(last_name__iexact=doctor_id.strip(), is_active=True)
        options = ", ".join(f"{d.pk} (Dr. {d.first_name} {d.last_name})" for d in matches)
        return {"success": False, "error": f"Multiple doctors match '{doctor_id}'. Use ID: {options}"}

    try:
        slot = DoctorSchedule.objects.get(
            doctor=doctor, date=appt_date, start_time=appt_time
        )
    except DoctorSchedule.DoesNotExist:
        return {
            "success": False,
            "error": (
                f"No schedule slot for Dr. {doctor.last_name} "
                f"on {date} at {time}. Use check_provider_availability first."
            ),
        }

    if Appointment.objects.filter(
        schedule_slot=slot, status__in=["SCHEDULED", "COMPLETED"]
    ).exists():
        return {
            "success": False,
            "error": f"The {time} slot on {date} with Dr. {doctor.last_name} is already booked.",
        }

    try:
        appointment = Appointment.objects.create(
            patient_id=patient_id,
            doctor=doctor,
            schedule_slot=slot,
            status="SCHEDULED",
        )
    except IntegrityError:
        return {
            "success": False,
            "error": "Slot was just booked by another request. Please try a different slot.",
        }

    return {
        "success": True,
        "appointment": {
            "id": str(appointment.pk),
            "patient_id": patient_id,
            "doctor_id": str(doctor.pk),
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "specialty": doctor.specialty.name,
            "date": appt_date.isoformat(),
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "status": "SCHEDULED",
        },
    }
