from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from businesses.models import Business
from services.models import Service


class StaffMember(models.Model):
    """A person who performs services for a business."""

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="staff_members"
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    services = models.ManyToManyField(
        Service, related_name="staff_members", blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class WorkingHours(models.Model):
    """Recurring weekly availability for a staff member (one row per weekday)."""

    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name="working_hours"
    )
    # 0 = Monday ... 6 = Sunday (matches Python's datetime.weekday()).
    day_of_week = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ("staff", "day_of_week")
        ordering = ("day_of_week",)

    def __str__(self):
        return f"{self.staff} — day {self.day_of_week} {self.start_time}-{self.end_time}"


class TimeOff(models.Model):
    """A one-off block during which a staff member is unavailable."""

    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name="time_off"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.staff} off {self.start_datetime} → {self.end_datetime}"
