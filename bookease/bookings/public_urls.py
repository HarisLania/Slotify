"""Public, unauthenticated booking flow. Mounted at /api/public/."""
from django.urls import path

from .views import (
    PublicBookingCreateView,
    PublicServiceListView,
    PublicSlotsView,
    PublicStaffListView,
)

urlpatterns = [
    path(
        "<slug:business_slug>/services/",
        PublicServiceListView.as_view(),
        name="public-services",
    ),
    path(
        "<slug:business_slug>/staff/",
        PublicStaffListView.as_view(),
        name="public-staff",
    ),
    path(
        "<slug:business_slug>/slots/",
        PublicSlotsView.as_view(),
        name="public-slots",
    ),
    path(
        "<slug:business_slug>/bookings/",
        PublicBookingCreateView.as_view(),
        name="public-booking-create",
    ),
]
