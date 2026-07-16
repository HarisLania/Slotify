from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "business",
        "service",
        "staff",
        "start_time",
        "status",
    )
    list_filter = ("status", "business", "staff")
    search_fields = ("customer_name", "customer_email")
    date_hierarchy = "start_time"
