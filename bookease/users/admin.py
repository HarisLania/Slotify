from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Expose the extra `role` and `phone` fields in the Django admin."""

    list_display = ("username", "email", "role", "phone", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("BookEase", {"fields": ("role", "phone")}),
    )
