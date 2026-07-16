from django.conf import settings
from django.db import models


class Business(models.Model):
    """A tenant on the platform. Each owner runs one business (MVP)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # used for the public booking URL
    timezone = models.CharField(max_length=64, default="Asia/Dubai")
    address = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "businesses"

    def __str__(self):
        return self.name
