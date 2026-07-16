from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "description",
            "duration_minutes",
            "buffer_minutes",
            "price",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Duration must be a positive number of minutes."
            )
        if value > 24 * 60:
            raise serializers.ValidationError(
                "Duration cannot exceed 24 hours (1440 minutes)."
            )
        return value

    def validate_buffer_minutes(self, value):
        if value < 0:
            raise serializers.ValidationError("Buffer time cannot be negative.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
