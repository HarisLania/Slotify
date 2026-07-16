from django.core.validators import MinValueValidator
from django.db import models

from businesses.models import Business


class Service(models.Model):
    """A bookable service offered by a business (e.g. 'Haircut', 30 min)."""

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    # Gap enforced *after* a booking of this service (cleanup, travel, etc.).
    buffer_minutes = models.PositiveIntegerField(default=0)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.duration_minutes}m)"
