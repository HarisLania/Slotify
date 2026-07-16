from django.contrib import admin

from .models import StaffMember, TimeOff, WorkingHours


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 0


class TimeOffInline(admin.TabularInline):
    model = TimeOff
    extra = 0


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "business", "is_active")
    list_filter = ("is_active", "business")
    inlines = [WorkingHoursInline, TimeOffInline]
