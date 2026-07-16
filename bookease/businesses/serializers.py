import zoneinfo

from rest_framework import serializers

from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = (
            "id",
            "name",
            "slug",
            "timezone",
            "address",
            "logo",
            "created_at",
        )
        # `slug` is generated at registration and is the public URL key, so it
        # must not be edited after the fact (bookmarked links would break).
        read_only_fields = ("id", "slug", "created_at")

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Business name cannot be blank.")
        return value

    def validate_timezone(self, value):
        # Ensure the timezone is a real IANA zone (e.g. "Asia/Dubai").
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(
                f"'{value}' is not a valid IANA timezone name."
            )
        return value
