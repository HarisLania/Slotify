from django.urls import path

from .views import (
    BookingDetailView,
    BookingListView,
    BookingStatusUpdateView,
)

# Mounted at /api/bookings/
urlpatterns = [
    path("", BookingListView.as_view(), name="booking-list"),
    path("<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path(
        "<int:pk>/status/",
        BookingStatusUpdateView.as_view(),
        name="booking-status",
    ),
]
