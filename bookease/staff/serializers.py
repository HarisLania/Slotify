"""Serializers for staff members and their availability rules."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from services.models import Service

from .models import StaffMember, TimeOff, WorkingHours

User = get_user_model()


class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHours
        fields = ("id", "day_of_week", "start_time", "end_time")
        read_only_fields = ("id",)

    def validate_day_of_week(self, value):
        if not 0 <= value <= 6:
            raise serializers.ValidationError(
                "day_of_week must be between 0 (Monday) and 6 (Sunday)."
            )
        return value

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                {"end_time": "end_time must be later than start_time."}
            )
        return attrs


class TimeOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeOff
        fields = ("id", "start_datetime", "end_datetime", "reason")
        read_only_fields = ("id",)

    def validate(self, attrs):
        start = attrs.get("start_datetime")
        end = attrs.get("end_datetime")
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                {"end_datetime": "end_datetime must be later than start_datetime."}
            )
        return attrs


class StaffMemberSerializer(serializers.ModelSerializer):
    """
    Read/write serializer for staff.

    On create it also provisions the underlying `User` account (role=staff)
    from the nested write-only credential fields.
    """

    # --- Nested account credentials (write-only, create-time) ---
    username = serializers.CharField(write_only=True, max_length=150)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    last_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

    # --- Read-only mirror of the linked user ---
    user = serializers.SerializerMethodField(read_only=True)

    services = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Service.objects.all(), required=False
    )

    class Meta:
        model = StaffMember
        fields = (
            "id",
            "user",
            "services",
            "is_active",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
        )
        read_only_fields = ("id",)

    def get_user(self, obj) -> dict:
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_services(self, value):
        """Services must belong to the same business as this staff member."""
        business = self.context.get("business")
        if business is not None:
            for service in value:
                if service.business_id != business.id:
                    raise serializers.ValidationError(
                        "You can only assign services that belong to your business."
                    )
        return value

    @transaction.atomic
    def create(self, validated_data):
        business = self.context["business"]
        services = validated_data.pop("services", [])

        user = User.objects.create_user(
            username=validated_data.pop("username"),
            email=validated_data.pop("email"),
            password=validated_data.pop("password"),
            first_name=validated_data.pop("first_name", ""),
            last_name=validated_data.pop("last_name", ""),
            role="staff",
        )
        staff = StaffMember.objects.create(
            business=business,
            user=user,
            is_active=validated_data.get("is_active", True),
        )
        staff.services.set(services)
        return staff

    def update(self, instance, validated_data):
        # Account-credential fields are create-only; ignore them on update.
        for field in ("username", "email", "password", "first_name", "last_name"):
            validated_data.pop(field, None)
        services = validated_data.pop("services", None)
        instance = super().update(instance, validated_data)
        if services is not None:
            instance.services.set(services)
        return instance
