"""Serializers for authentication and the current-user profile."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from businesses.models import Business

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Registers a business owner.

    Creates the `User` (role=owner) *and* their `Business` in a single
    atomic transaction, so a half-registered account can never exist.
    """

    # --- Account fields ---
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # --- Business fields ---
    business_name = serializers.CharField(max_length=255)
    timezone = serializers.CharField(max_length=64, required=False, default="Asia/Dubai")

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        # Run Django's configured password validators for strong, clear errors.
        validate_password(value)
        return value

    def _unique_slug(self, name):
        """Derive a URL-safe, unique slug from the business name."""
        base = slugify(name) or "business"
        slug = base
        counter = 1
        while Business.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base}-{counter}"
        return slug

    @transaction.atomic
    def create(self, validated_data):
        business_name = validated_data.pop("business_name")
        timezone = validated_data.pop("timezone", "Asia/Dubai")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            phone=validated_data.get("phone", ""),
            role="owner",
        )

        business = Business.objects.create(
            owner=user,
            name=business_name,
            slug=self._unique_slug(business_name),
            timezone=timezone,
        )
        # Stash for the view's response.
        self.context["business"] = business
        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only-ish representation of the authenticated user (`/auth/me/`)."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "phone")
        read_only_fields = ("id", "role")
