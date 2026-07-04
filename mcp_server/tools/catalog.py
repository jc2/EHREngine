from mcp_server.schemas.responses import (
    ListInsurancePayersResult,
    ListMedicalSpecialtiesResult,
    PayerSummary,
    SpecialtySummary,
)


def list_insurance_payers() -> ListInsurancePayersResult:
    """List all active insurance payers in the system.

    Use this tool to discover which insurance payers are available before
    calling verify_insurance_eligibility. Returns the payer code (used as
    payer_id in other tools), name, and ID.
    """
    from clinic.models import InsurancePayer

    payers = InsurancePayer.objects.filter(is_active=True).order_by("name")

    return ListInsurancePayersResult(
        total=payers.count(),
        payers=[
            PayerSummary(
                id=str(p.pk),
                code=p.code,
                name=p.name,
            )
            for p in payers
        ],
    )


def list_medical_specialties() -> ListMedicalSpecialtiesResult:
    """List all active medical specialties (departments) in the system.

    Use this tool to discover which specialties are available before
    calling check_provider_availability. Returns the specialty code
    (used as medical_specialty in other tools), display name, and
    the number of active doctors in each specialty.
    """
    from django.db.models import Count, Q

    from clinic.models import MedicalDepartment

    specialties = (
        MedicalDepartment.objects.filter(is_active=True)
        .annotate(
            doctor_count=Count(
                "doctors", filter=Q(doctors__is_active=True)
            )
        )
        .order_by("name")
    )

    return ListMedicalSpecialtiesResult(
        total=specialties.count(),
        specialties=[
            SpecialtySummary(
                id=str(s.pk),
                code=s.code,
                name=s.name,
                active_doctors=s.doctor_count,
            )
            for s in specialties
        ],
    )
