from datetime import date as date_type

from mcp_server.schemas.responses import AvailableSlot, CheckProviderAvailabilityResult


def check_provider_availability(
    medical_specialty: str, date: str
) -> CheckProviderAvailabilityResult:
    """Check available appointment slots for all doctors in a medical specialty on a given date.

    Use this tool to find open 30-minute time slots. Each doctor works from
    08:00 to 12:00 in 30-minute blocks. Only slots without an existing
    appointment (SCHEDULED or COMPLETED) are returned.

    Use list_medical_specialties first if you don't know the valid codes.

    Args:
        medical_specialty: The specialty code (e.g. "CARDIOLOGY") or name
            (e.g. "Cardiology"). Case-insensitive.
        date: The date to check, in YYYY-MM-DD format (e.g. "2026-06-15").

    Returns:
        A dict with:
        - specialty (str): The normalized specialty name.
        - date (str): The date checked.
        - total_available (int): Number of open slots.
        - available_slots (list): Each slot contains doctor_id, doctor_name,
          date, start_time, end_time. Use doctor_id and start_time when
          calling schedule_appointment.
    """
    from clinic.models import DoctorSchedule, MedicalDepartment

    query = medical_specialty.strip()
    dept = (
        MedicalDepartment.objects.filter(code__iexact=query, is_active=True).first()
        or MedicalDepartment.objects.filter(name__iexact=query, is_active=True).first()
    )

    if not dept:
        available_codes = list(
            MedicalDepartment.objects.filter(is_active=True).values_list("code", flat=True)
        )
        return CheckProviderAvailabilityResult(
            specialty=medical_specialty,
            date=date,
            total_available=0,
            available_slots=[],
            error=(
                f"Specialty '{medical_specialty}' not found. "
                f"Available: {', '.join(available_codes)}"
            ),
        )

    try:
        check_date = date_type.fromisoformat(date)
    except ValueError:
        return CheckProviderAvailabilityResult(
            specialty=dept.code,
            date=date,
            total_available=0,
            available_slots=[],
            error=f"Invalid date format '{date}'. Use YYYY-MM-DD.",
        )

    open_slots = (
        DoctorSchedule.objects.filter(
            doctor__specialty=dept,
            doctor__is_active=True,
            date=check_date,
        )
        .exclude(appointment__status__in=["SCHEDULED", "COMPLETED"])
        .select_related("doctor", "doctor__specialty")
        .order_by("start_time", "doctor__last_name")
    )

    available = [
        AvailableSlot(
            doctor_id=str(slot.doctor.pk),
            doctor_name=f"Dr. {slot.doctor.first_name} {slot.doctor.last_name}",
            specialty=slot.doctor.specialty.name,
            date=slot.date.isoformat(),
            start_time=slot.start_time.strftime("%H:%M"),
            end_time=slot.end_time.strftime("%H:%M"),
        )
        for slot in open_slots
    ]

    return CheckProviderAvailabilityResult(
        specialty=dept.code,
        date=check_date.isoformat(),
        total_available=len(available),
        available_slots=available,
    )
