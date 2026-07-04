import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from clinic.models import (
    BillingRule,
    Doctor,
    DoctorSchedule,
    InsurancePayer,
    MedicalDepartment,
    Medication,
    Patient,
    PatientInsurance,
    Prescription,
)

PAYERS = [
    ("BlueCross BlueShield", "BCBS"),
    ("Aetna", "AETNA"),
    ("UnitedHealth Group", "UHC"),
    ("Cigna", "CIGNA"),
    ("Humana", "HUMANA"),
    ("Kaiser Permanente", "KAISER"),
    ("Anthem", "ANTHEM"),
    ("Molina Healthcare", "MOLINA"),
]

SPECIALTIES = [
    ("CARDIOLOGY", "Cardiology"),
    ("DERMATOLOGY", "Dermatology"),
    ("GENERAL_PRACTICE", "General Practice"),
    ("PEDIATRICS", "Pediatrics"),
    ("ORTHOPEDICS", "Orthopedics"),
    ("NEUROLOGY", "Neurology"),
    ("GYNECOLOGY", "Gynecology"),
    ("OPHTHALMOLOGY", "Ophthalmology"),
]

DOCTORS = [
    ("James", "Wilson", "CARDIOLOGY"),
    ("Sarah", "Chen", "CARDIOLOGY"),
    ("Maria", "Rodriguez", "DERMATOLOGY"),
    ("David", "Kim", "DERMATOLOGY"),
    ("Robert", "Johnson", "GENERAL_PRACTICE"),
    ("Emily", "Davis", "GENERAL_PRACTICE"),
    ("Michael", "Patel", "PEDIATRICS"),
    ("Jessica", "Thompson", "PEDIATRICS"),
    ("Daniel", "Martinez", "ORTHOPEDICS"),
    ("Laura", "Anderson", "ORTHOPEDICS"),
    ("William", "Lee", "NEUROLOGY"),
    ("Amanda", "Taylor", "NEUROLOGY"),
    ("Christopher", "Brown", "GYNECOLOGY"),
    ("Sophia", "Garcia", "GYNECOLOGY"),
    ("Andrew", "Nguyen", "OPHTHALMOLOGY"),
    ("Rachel", "Moore", "OPHTHALMOLOGY"),
]

SCHEDULE_START_HOUR = 8
SCHEDULE_END_HOUR = 12
SLOT_MINUTES = 30

PATIENTS = [
    ("PAT-001", "John", "Smith", "555-0101", "ID-100001"),
    ("PAT-002", "Maria", "Garcia", "555-0102", "ID-100002"),
    ("PAT-003", "Robert", "Johnson", "555-0103", "ID-100003"),
    ("PAT-004", "Emily", "Davis", "555-0104", "ID-100004"),
    ("PAT-005", "Michael", "Wilson", "555-0105", "ID-100005"),
    ("PAT-006", "Sarah", "Martinez", "555-0106", "ID-100006"),
    ("PAT-007", "David", "Anderson", "555-0107", "ID-100007"),
    ("PAT-008", "Jessica", "Taylor", "555-0108", "ID-100008"),
    ("PAT-009", "Christopher", "Thomas", "555-0109", "ID-100009"),
    ("PAT-010", "Amanda", "Moore", "555-0110", "ID-100010"),
]


class Command(BaseCommand):
    help = "Seed the database with sample EHR data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-if-exists",
            action="store_true",
            help="Skip seeding if data already exists",
        )

    def handle(self, *args, **options):
        if options["skip_if_exists"] and InsurancePayer.objects.exists():
            self.stdout.write(self.style.WARNING("Data already exists, skipping seed."))
            return

        self._seed_specialties()
        self._seed_payers()
        self._seed_doctors()
        self._seed_schedules()
        self._seed_patients()
        self._seed_patient_insurance()
        self._seed_medications()
        self._seed_prescriptions()
        self._seed_billing_rules()
        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))

    def _seed_specialties(self):
        for code, name in SPECIALTIES:
            MedicalDepartment.objects.get_or_create(
                code=code, defaults={"name": name, "is_active": True}
            )
        self.stdout.write(f"  Seeded {len(SPECIALTIES)} medical specialties.")

    def _seed_payers(self):
        for name, code in PAYERS:
            InsurancePayer.objects.get_or_create(
                code=code, defaults={"name": name, "is_active": True}
            )
        self.stdout.write(f"  Seeded {len(PAYERS)} insurance payers.")

    def _seed_doctors(self):
        for i, (first, last, specialty_code) in enumerate(DOCTORS, start=1):
            specialty = MedicalDepartment.objects.get(code=specialty_code)
            Doctor.objects.get_or_create(
                license_number=f"MD-{i:04d}",
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "specialty": specialty,
                    "is_active": True,
                },
            )
        self.stdout.write(f"  Seeded {len(DOCTORS)} doctors.")

    def _seed_schedules(self):
        doctors = Doctor.objects.all()
        today = date.today()
        count = 0

        for day_offset in range(21):
            d = today + timedelta(days=day_offset)
            if d.weekday() >= 5:
                continue

            for doctor in doctors:
                for hour in range(SCHEDULE_START_HOUR, SCHEDULE_END_HOUR):
                    for minute in (0, SLOT_MINUTES):
                        start = time(hour, minute)
                        end_minute = minute + SLOT_MINUTES
                        end_hour = hour + (end_minute // 60)
                        end_minute = end_minute % 60
                        end = time(end_hour, end_minute)

                        _, created = DoctorSchedule.objects.get_or_create(
                            doctor=doctor,
                            date=d,
                            start_time=start,
                            defaults={"end_time": end},
                        )
                        if created:
                            count += 1

        self.stdout.write(f"  Seeded {count} schedule slots.")

    def _seed_patients(self):
        count = 0
        for code, first, last, phone, id_num in PATIENTS:
            _, created = Patient.objects.get_or_create(
                code=code,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone_number": phone,
                    "identification_number": id_num,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  Seeded {count} patients.")

    def _seed_patient_insurance(self):
        payers = list(InsurancePayer.objects.all())
        today = date.today()
        types = ["HMO", "PPO"]
        count = 0

        for i in range(1, 11):
            patient_code = f"PAT-{i:03d}"
            num_policies = random.choice([1, 1, 1, 2])

            for _ in range(num_policies):
                payer = random.choice(payers)
                months_ago = random.randint(6, 18)
                start = today - timedelta(days=months_ago * 30)

                if i <= 8:
                    end = None
                else:
                    end = today - timedelta(days=random.randint(10, 90))

                _, created = PatientInsurance.objects.get_or_create(
                    patient_id=patient_code,
                    payer=payer,
                    defaults={
                        "insurance_type": random.choice(types),
                        "member_id": f"MBR-{random.randint(100000, 999999)}",
                        "enrollment_start": start,
                        "enrollment_end": end,
                    },
                )
                if created:
                    count += 1

        self.stdout.write(f"  Seeded {count} patient insurance records.")

    def _seed_medications(self):
        meds = [
            ("Lisinopril", "10 mg", "TABLET", False),
            ("Metformin", "500 mg", "TABLET", False),
            ("Alprazolam", "0.5 mg", "TABLET", True),
            ("Atorvastatin", "20 mg", "TABLET", False),
        ]
        for name, strength, form, controlled in meds:
            Medication.objects.get_or_create(
                name=name,
                strength=strength,
                defaults={"form": form, "is_controlled_substance": controlled},
            )
        self.stdout.write(f"  Seeded {len(meds)} medications.")

    def _seed_prescriptions(self):
        today = date.today()
        gp = Doctor.objects.filter(specialty__code="GENERAL_PRACTICE", is_active=True).first()
        cardio = Doctor.objects.filter(specialty__code="CARDIOLOGY", is_active=True).first()
        prescriber = gp or Doctor.objects.filter(is_active=True).first()
        if not prescriber:
            self.stdout.write(self.style.WARNING("  No active doctor found; skipping prescriptions."))
            return

        lisinopril = Medication.objects.get(name="Lisinopril", strength="10 mg")
        metformin = Medication.objects.get(name="Metformin", strength="500 mg")
        alprazolam = Medication.objects.get(name="Alprazolam", strength="0.5 mg")
        atorvastatin = Medication.objects.get(name="Atorvastatin", strength="20 mg")

        prescriptions = [
            # PAT-001 — full refill workflow demo set
            {
                "patient_id": "PAT-001",
                "medication": lisinopril,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth daily",
                "quantity": 30,
                "refills_authorized": 3,
                "refills_remaining": 3,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=30),
                "expiration_date": today + timedelta(days=335),
                "pharmacy": "CVS Pharmacy #1234",
            },
            {
                "patient_id": "PAT-001",
                "medication": metformin,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth twice daily with meals",
                "quantity": 60,
                "refills_authorized": 3,
                "refills_remaining": 0,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=90),
                "expiration_date": today + timedelta(days=275),
                "pharmacy": "CVS Pharmacy #1234",
            },
            {
                "patient_id": "PAT-001",
                "medication": alprazolam,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth as needed for anxiety",
                "quantity": 30,
                "refills_authorized": 2,
                "refills_remaining": 2,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=15),
                "expiration_date": today + timedelta(days=350),
                "pharmacy": "Walgreens #5678",
            },
            {
                "patient_id": "PAT-001",
                "medication": atorvastatin,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth at bedtime",
                "quantity": 30,
                "refills_authorized": 5,
                "refills_remaining": 1,
                "status": "EXPIRED",
                "date_written": today - timedelta(days=400),
                "expiration_date": today - timedelta(days=35),
                "pharmacy": "CVS Pharmacy #1234",
            },
            # PAT-002 — hypertension, ready to refill
            {
                "patient_id": "PAT-002",
                "medication": lisinopril,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth every morning",
                "quantity": 30,
                "refills_authorized": 5,
                "refills_remaining": 4,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=45),
                "expiration_date": today + timedelta(days=320),
                "pharmacy": "Walgreens #2201",
            },
            {
                "patient_id": "PAT-002",
                "medication": atorvastatin,
                "prescriber": cardio or prescriber,
                "sig": "1 tablet by mouth at bedtime",
                "quantity": 30,
                "refills_authorized": 3,
                "refills_remaining": 2,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=60),
                "expiration_date": today + timedelta(days=305),
                "pharmacy": "Walgreens #2201",
            },
            # PAT-003 — diabetes management
            {
                "patient_id": "PAT-003",
                "medication": metformin,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth twice daily",
                "quantity": 60,
                "refills_authorized": 6,
                "refills_remaining": 5,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=20),
                "expiration_date": today + timedelta(days=345),
                "pharmacy": "CVS Pharmacy #3300",
            },
            # PAT-004 — no refills left (needs provider review)
            {
                "patient_id": "PAT-004",
                "medication": lisinopril,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth daily",
                "quantity": 30,
                "refills_authorized": 2,
                "refills_remaining": 0,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=120),
                "expiration_date": today + timedelta(days=245),
                "pharmacy": "Rite Aid #4412",
            },
            {
                "patient_id": "PAT-004",
                "medication": metformin,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth twice daily with meals",
                "quantity": 60,
                "refills_authorized": 3,
                "refills_remaining": 1,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=40),
                "expiration_date": today + timedelta(days=325),
                "pharmacy": "Rite Aid #4412",
            },
            # PAT-005 — controlled substance
            {
                "patient_id": "PAT-005",
                "medication": alprazolam,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth as needed, max 2 per day",
                "quantity": 30,
                "refills_authorized": 1,
                "refills_remaining": 1,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=10),
                "expiration_date": today + timedelta(days=355),
                "pharmacy": "CVS Pharmacy #5501",
            },
            # PAT-006 — expired prescription
            {
                "patient_id": "PAT-006",
                "medication": atorvastatin,
                "prescriber": cardio or prescriber,
                "sig": "1 tablet by mouth nightly",
                "quantity": 30,
                "refills_authorized": 3,
                "refills_remaining": 2,
                "status": "EXPIRED",
                "date_written": today - timedelta(days=380),
                "expiration_date": today - timedelta(days=15),
                "pharmacy": "Walgreens #6600",
            },
            # PAT-007 — cholesterol + blood pressure
            {
                "patient_id": "PAT-007",
                "medication": lisinopril,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth daily",
                "quantity": 30,
                "refills_authorized": 4,
                "refills_remaining": 3,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=25),
                "expiration_date": today + timedelta(days=340),
                "pharmacy": "CVS Pharmacy #7702",
            },
            {
                "patient_id": "PAT-007",
                "medication": atorvastatin,
                "prescriber": cardio or prescriber,
                "sig": "1 tablet by mouth at bedtime",
                "quantity": 30,
                "refills_authorized": 4,
                "refills_remaining": 4,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=25),
                "expiration_date": today + timedelta(days=340),
                "pharmacy": "CVS Pharmacy #7702",
            },
            # PAT-008 — discontinued medication
            {
                "patient_id": "PAT-008",
                "medication": metformin,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth twice daily",
                "quantity": 60,
                "refills_authorized": 3,
                "refills_remaining": 2,
                "status": "DISCONTINUED",
                "date_written": today - timedelta(days=200),
                "expiration_date": today + timedelta(days=165),
                "pharmacy": "Walgreens #8801",
            },
            {
                "patient_id": "PAT-008",
                "medication": lisinopril,
                "prescriber": prescriber,
                "sig": "1 tablet by mouth daily",
                "quantity": 30,
                "refills_authorized": 5,
                "refills_remaining": 5,
                "status": "ACTIVE",
                "date_written": today - timedelta(days=14),
                "expiration_date": today + timedelta(days=351),
                "pharmacy": "Walgreens #8801",
            },
        ]

        count = 0
        for rx in prescriptions:
            _, created = Prescription.objects.get_or_create(
                patient_id=rx["patient_id"],
                medication=rx["medication"],
                defaults={
                    "prescriber": rx["prescriber"],
                    "sig": rx["sig"],
                    "quantity": rx["quantity"],
                    "refills_authorized": rx["refills_authorized"],
                    "refills_remaining": rx["refills_authorized"],
                    "status": rx["status"],
                    "date_written": rx["date_written"],
                    "expiration_date": rx["expiration_date"],
                    "pharmacy": rx["pharmacy"],
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  Seeded {count} prescriptions.")

    def _seed_billing_rules(self):
        # Tiered cascade lookup for the deterministic billing engine (Epic 3).
        # (insurance_type, specialty_code, fixed_cost) — None means "any".
        cardiology = MedicalDepartment.objects.filter(code="CARDIOLOGY").first()
        general = MedicalDepartment.objects.filter(code="GENERAL_PRACTICE").first()

        rules = [
            ("HMO", cardiology, "40.00"),  # Tier 1: exact
            ("PPO", cardiology, "60.00"),  # Tier 1: exact
            (None, general, "25.00"),      # Tier 2: specialty default
            (None, None, "50.00"),         # Tier 3: global fallback
        ]

        count = 0
        for insurance_type, specialty, fixed_cost in rules:
            _, created = BillingRule.objects.get_or_create(
                insurance_type=insurance_type,
                specialty=specialty,
                defaults={"fixed_cost": fixed_cost},
            )
            if created:
                count += 1
        self.stdout.write(f"  Seeded {count} billing rules.")
