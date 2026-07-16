from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import StaffViewSet, TimeOffView, WorkingHoursView

# Mounted at /api/staff/
router = DefaultRouter()
router.register("", StaffViewSet, basename="staff")

urlpatterns = [
    path(
        "<int:staff_id>/working-hours/",
        WorkingHoursView.as_view(),
        name="staff-working-hours",
    ),
    path(
        "<int:staff_id>/time-off/",
        TimeOffView.as_view(),
        name="staff-time-off",
    ),
]
urlpatterns += router.urls
