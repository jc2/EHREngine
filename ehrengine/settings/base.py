import os

import dj_database_url
import logfire
from django.urls import reverse_lazy

logfire.configure(service_name="ehrengine")
logfire.instrument_django()

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-production")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "clinic",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "ehrengine.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ehrengine.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://ehrengine:ehrengine_dev@localhost:5432/ehrengine_db"
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

UNFOLD = {
    "SITE_TITLE": "EHREngine",
    "SITE_HEADER": "EHREngine",
    "SITE_SYMBOL": "medical_services",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Scheduling",
                "separator": True,
                "items": [
                    {
                        "title": "Appointments",
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:clinic_appointment_changelist"),
                    },
                    {
                        "title": "Doctor Schedules",
                        "icon": "schedule",
                        "link": reverse_lazy("admin:clinic_doctorschedule_changelist"),
                    },
                ],
            },
            {
                "title": "Clinic",
                "separator": True,
                "items": [
                    {
                        "title": "Doctors",
                        "icon": "group",
                        "link": reverse_lazy("admin:clinic_doctor_changelist"),
                    },
                    {
                        "title": "Specialties",
                        "icon": "local_hospital",
                        "link": reverse_lazy("admin:clinic_medicaldepartment_changelist"),
                    },
                ],
            },
            {
                "title": "Pharmacy",
                "separator": True,
                "items": [
                    {
                        "title": "Medications",
                        "icon": "medication",
                        "link": reverse_lazy("admin:clinic_medication_changelist"),
                    },
                    {
                        "title": "Prescriptions",
                        "icon": "prescriptions",
                        "link": reverse_lazy("admin:clinic_prescription_changelist"),
                    },
                    {
                        "title": "Refill Requests",
                        "icon": "replay",
                        "link": reverse_lazy("admin:clinic_refillrequest_changelist"),
                    },
                ],
            },
            {
                "title": "Insurance",
                "separator": True,
                "items": [
                    {
                        "title": "Insurance Payers",
                        "icon": "assured_workload",
                        "link": reverse_lazy("admin:clinic_insurancepayer_changelist"),
                    },
                    {
                        "title": "Patient Insurance",
                        "icon": "badge",
                        "link": reverse_lazy("admin:clinic_patientinsurance_changelist"),
                    },
                ],
            },
            {
                "title": "Authentication",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "groups",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
