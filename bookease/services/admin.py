from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "duration_minutes", "price", "is_active")
    list_filter = ("is_active", "business")
    search_fields = ("name",)
