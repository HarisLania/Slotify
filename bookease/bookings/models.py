from django.db import models

from businesses.models import Business
from services.models import Service
from staff.models import StaffMember


class Booking(models.Model):
    """A single appointment. Customer details are stored inline (no account)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    ]

    # Statuses that make a slot "taken" for availability purposes.
    BLOCKING_STATUSES = ("pending", "confirmed")

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="bookings"
    )
    # PROTECT: never silently delete a service/staff that has history attached.
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT)

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["staff", "start_time"])]
        ordering = ("-start_time",)

    def __str__(self):
        return f"{self.customer_name} — {self.service} @ {self.start_time:%Y-%m-%d %H:%M}"
