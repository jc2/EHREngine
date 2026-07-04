from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from clinic.views import (
    appointment_detail,
    escalation_detail,
    generate_schedules,
    lookup_appointment,
    lookup_escalation,
    lookup_refill,
    refill_detail,
    schedule_dashboard,
)

urlpatterns = [
    path("", schedule_dashboard, name="schedule-dashboard"),
    path("generate-schedules/", generate_schedules, name="generate-schedules"),
    path("appointments/lookup/", lookup_appointment, name="appointment-lookup"),
    path("appointments/<str:public_id>/", appointment_detail, name="appointment-detail"),
    path("refills/lookup/", lookup_refill, name="refill-lookup"),
    path("refills/<str:public_id>/", refill_detail, name="refill-detail"),
    path("escalations/lookup/", lookup_escalation, name="escalation-lookup"),
    path("escalations/<str:public_id>/", escalation_detail, name="escalation-detail"),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
