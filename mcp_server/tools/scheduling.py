from datetime import date as date_type, datetime

from mcp_server.auth import enforce_patient_scope
from mcp_server.schemas.auth_mapping import schedule_auth_error
from mcp_server.schemas.responses import AppointmentDetails, ScheduleAppointmentResult
from mcp_server.tools.urls import absolute_view_url


def schedule_appointment(
    patient_id: str, doctor_id: str, date: str, time: str, notes: str
) -> ScheduleAppointmentResult:
    """Schedule a 30-minute appointment for a patient with a specific doctor.

    Use this tool AFTER verifying insurance eligibility and checking provider
    availability. The typical workflow is:
      1. identify_patient — resolve the patient code (if unknown)
      2. verify_insurance_eligibility — confirm active coverage
      3. check_provider_availability — find open slots
      4. schedule_appointment — book the slot

    Args:
        patient_id: The patient code (e.g. "PAT-001").
        doctor_id: The doctor's ID (from check_provider_availability results).
        date: Appointment date in YYYY-MM-DD format (e.g. "2026-06-15").
        time: Start time in HH:MM 24-hour format (e.g. "09:30").
              Must match an available slot from check_provider_availability.
        notes: Required. A list of reasons why the patient is scheduling this visit
               (e.g. "Annual checkup, persistent cough for 2 weeks").

    Returns:
        A dict with:
        - success (bool): Whether the appointment was created.
        - appointment (dict): Details including public_id, detail_page_url, patient_id,
          doctor, specialty, date, start_time, end_time, status, and notes.
        - error (str): Reason for failure if success is False.
    """
    auth_error = enforce_patient_scope(patient_id)
    if auth_error:
        return schedule_auth_error(auth_error)

    if not notes or not notes.strip():
        return ScheduleAppointmentResult(
            success=False,
            error=(
                "notes is required. Provide a list of reasons why the patient "
                "is scheduling this visit."
            ),
        )

    from django.db import IntegrityError

    from clinic.models import Appointment, Doctor, DoctorSchedule, Patient

    try:
        patient = Patient.objects.get(code=patient_id)
    except Patient.DoesNotExist:
        return ScheduleAppointmentResult(
            success=False, error=f"Patient '{patient_id}' not found."
        )

    try:
        appt_date = date_type.fromisoformat(date)
    except ValueError:
        return ScheduleAppointmentResult(
            success=False, error=f"Invalid date format '{date}'. Use YYYY-MM-DD."
        )

    try:
        appt_time = datetime.strptime(time, "%H:%M").time()
    except ValueError:
        return ScheduleAppointmentResult(
            success=False, error=f"Invalid time format '{time}'. Use HH:MM (24h)."
        )

    try:
        if doctor_id.isdigit():
            doctor = Doctor.objects.get(pk=doctor_id, is_active=True)
        else:
            doctor = Doctor.objects.get(last_name__iexact=doctor_id.strip(), is_active=True)
    except Doctor.DoesNotExist:
        return ScheduleAppointmentResult(
            success=False, error=f"Doctor '{doctor_id}' not found or inactive."
        )
    except Doctor.MultipleObjectsReturned:
        matches = Doctor.objects.filter(last_name__iexact=doctor_id.strip(), is_active=True)
        options = ", ".join(f"{d.pk} (Dr. {d.first_name} {d.last_name})" for d in matches)
        return ScheduleAppointmentResult(
            success=False,
            error=f"Multiple doctors match '{doctor_id}'. Use ID: {options}",
        )

    try:
        slot = DoctorSchedule.objects.get(
            doctor=doctor, date=appt_date, start_time=appt_time
        )
    except DoctorSchedule.DoesNotExist:
        return ScheduleAppointmentResult(
            success=False,
            error=(
                f"No schedule slot for Dr. {doctor.last_name} "
                f"on {date} at {time}. Use check_provider_availability first."
            ),
        )

    if Appointment.objects.filter(
        schedule_slot=slot, status__in=["SCHEDULED", "COMPLETED"]
    ).exists():
        return ScheduleAppointmentResult(
            success=False,
            error=f"The {time} slot on {date} with Dr. {doctor.last_name} is already booked.",
        )

    try:
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            schedule_slot=slot,
            status="SCHEDULED",
            notes=notes.strip(),
        )
    except IntegrityError:
        return ScheduleAppointmentResult(
            success=False,
            error="Slot was just booked by another request. Please try a different slot.",
        )

    return ScheduleAppointmentResult(
        success=True,
        appointment=AppointmentDetails(
            public_id=appointment.public_id,
            detail_page_url=absolute_view_url(appointment.view_url),
            id=str(appointment.pk),
            patient_id=patient_id,
            doctor_id=str(doctor.pk),
            doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}",
            specialty=doctor.specialty.name,
            date=appt_date.isoformat(),
            start_time=slot.start_time.strftime("%H:%M"),
            end_time=slot.end_time.strftime("%H:%M"),
            status="SCHEDULED",
            notes=appointment.notes,
        ),
    )
