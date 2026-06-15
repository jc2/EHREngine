from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from clinic.views import generate_schedules, schedule_dashboard

urlpatterns = [
    path("", schedule_dashboard, name="schedule-dashboard"),
    path("generate-schedules/", generate_schedules, name="generate-schedules"),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
