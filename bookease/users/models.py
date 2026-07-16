from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    A single account can be a business owner, a staff member, or a customer.
    Owners and staff authenticate into the dashboard; customers book publicly
    without needing an account (their contact details live on the Booking).
    """

    ROLE_CHOICES = [
        ("owner", "Business Owner"),
        ("staff", "Staff Member"),
        ("customer", "Customer"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="owner")
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
