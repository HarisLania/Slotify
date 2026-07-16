"""Serializers for both the dashboard and the public booking flow."""
import datetime as dt

from rest_framework import serializers

from services.models import Service
from staff.models import StaffMember

from .availability import get_available_slots
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    """Dashboard read representation of a booking."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    staff_name = serializers.CharField(source="staff.user.username", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "business",
            "service",
            "service_name",
            "staff",
            "staff_name",
            "customer_name",
            "customer_email",
            "customer_phone",
            "start_time",
            "end_time",
            "status",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class BookingStatusSerializer(serializers.ModelSerializer):
    """Restricted serializer for the status-transition endpoint."""

    class Meta:
        model = Booking
        fields = ("id", "status")
        read_only_fields = ("id",)

    def validate_status(self, value):
        valid = {choice[0] for choice in Booking.STATUS_CHOICES}
        if value not in valid:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(sorted(valid))}."
            )
        return value


class PublicServiceSerializer(serializers.ModelSerializer):
    """Customer-facing service listing (no internal fields)."""

    class Meta:
        model = Service
        fields = ("id", "name", "description", "duration_minutes", "price")


class PublicStaffSerializer(serializers.ModelSerializer):
    """Customer-facing staff listing."""

    name = serializers.SerializerMethodField()

    class Meta:
        model = StaffMember
        fields = ("id", "name")

    def get_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username


class PublicBookingCreateSerializer(serializers.Serializer):
    """
    Validates and creates a booking from the public flow.

    The `business` is resolved from the URL slug and injected via context, so
    it is never taken from the request body.
    """

    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    staff = serializers.PrimaryKeyRelatedField(queryset=StaffMember.objects.all())
    start_time = serializers.DateTimeField()
    customer_name = serializers.CharField(max_length=255)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_customer_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Customer name is required.")
        return value

    def validate(self, attrs):
        business = self.context["business"]
        service = attrs["service"]
        staff = attrs["staff"]
        start_time = attrs["start_time"]

        # --- Ownership / consistency checks ---
        if service.business_id != business.id:
            raise serializers.ValidationError(
                {"service": "This service does not belong to this business."}
            )
        if not service.is_active:
            raise serializers.ValidationError(
                {"service": "This service is not currently available."}
            )
        if staff.business_id != business.id:
            raise serializers.ValidationError(
                {"staff": "This staff member does not belong to this business."}
            )
        if not staff.is_active:
            raise serializers.ValidationError(
                {"staff": "This staff member is not currently available."}
            )
        if not staff.services.filter(pk=service.pk).exists():
            raise serializers.ValidationError(
                {"staff": "This staff member does not offer the selected service."}
            )

        # --- The slot must actually be available right now ---
        # Re-checking here (rather than trusting the client) closes the gap
        # between the customer viewing slots and submitting the booking.
        local_date = start_time.astimezone(
            get_business_tz(business)
        ).date()
        available = get_available_slots(staff, service, local_date)
        if start_time not in available:
            raise serializers.ValidationError(
                {"start_time": "This slot is no longer available. Please pick another."}
            )

        attrs["end_time"] = start_time + dt.timedelta(minutes=service.duration_minutes)
        return attrs

    def create(self, validated_data):
        business = self.context["business"]
        return Booking.objects.create(
            business=business,
            service=validated_data["service"],
            staff=validated_data["staff"],
            customer_name=validated_data["customer_name"],
            customer_email=validated_data["customer_email"],
            customer_phone=validated_data.get("customer_phone", ""),
            notes=validated_data.get("notes", ""),
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
            status="pending",
        )


def get_business_tz(business):
    """Small helper so the serializer stays readable."""
    from zoneinfo import ZoneInfo

    return ZoneInfo(business.timezone)
