from datetime import date as date_type
from typing import Any


VALID_SPECIALTIES = [
    "CARDIOLOGY",
    "DERMATOLOGY",
    "GENERAL_PRACTICE",
    "PEDIATRICS",
    "ORTHOPEDICS",
    "NEUROLOGY",
    "GYNECOLOGY",
    "OPHTHALMOLOGY",
]


def check_provider_availability(
    medical_specialty: str, date: str
) -> dict[str, Any]:
    """Check available appointment slots for all doctors in a medical specialty on a given date.

    Use this tool to find open 30-minute time slots. Each doctor works from
    08:00 to 12:00 in 30-minute blocks. Only slots without an existing
    appointment (SCHEDULED or COMPLETED) are returned.

    Args:
        medical_specialty: One of the following specialties (case-insensitive):
            CARDIOLOGY, DERMATOLOGY, GENERAL_PRACTICE, PEDIATRICS,
            ORTHOPEDICS, NEUROLOGY, GYNECOLOGY, OPHTHALMOLOGY.
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
    from clinic.models import DoctorSchedule

    specialty = medical_specialty.strip().upper()
    if specialty not in VALID_SPECIALTIES:
        return {
            "specialty": medical_specialty,
            "date": date,
            "total_available": 0,
            "available_slots": [],
            "error": (
                f"Invalid specialty '{medical_specialty}'. "
                f"Must be one of: {', '.join(VALID_SPECIALTIES)}"
            ),
        }

    try:
        check_date = date_type.fromisoformat(date)
    except ValueError:
        return {
            "specialty": specialty,
            "date": date,
            "total_available": 0,
            "available_slots": [],
            "error": f"Invalid date format '{date}'. Use YYYY-MM-DD.",
        }

    open_slots = (
        DoctorSchedule.objects.filter(
            doctor__specialty=specialty,
            doctor__is_active=True,
            date=check_date,
        )
        .exclude(appointment__status__in=["SCHEDULED", "COMPLETED"])
        .select_related("doctor")
        .order_by("start_time", "doctor__last_name")
    )

    available = [
        {
            "doctor_id": str(slot.doctor.pk),
            "doctor_name": f"Dr. {slot.doctor.first_name} {slot.doctor.last_name}",
            "specialty": slot.doctor.get_specialty_display(),
            "date": slot.date.isoformat(),
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
        }
        for slot in open_slots
    ]

    return {
        "specialty": specialty,
        "date": check_date.isoformat(),
        "total_available": len(available),
        "available_slots": available,
    }
