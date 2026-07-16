from django.contrib import admin

from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "timezone", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
