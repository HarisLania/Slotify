"""CRUD for services, scoped to the authenticated owner's business."""
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound

from businesses.models import Business
from businesses.permissions import IsOwner

from .models import Service
from .serializers import ServiceSerializer


@extend_schema(tags=["services"])
class ServiceViewSet(viewsets.ModelViewSet):
    """
    /api/services/        GET (list)  POST (create)
    /api/services/{id}/   GET  PATCH  DELETE

    Only ever returns/affects services belonging to the caller's business.
    """

    serializer_class = ServiceSerializer
    permission_classes = [IsOwner]

    def _get_business(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if business is None:
            raise NotFound("No business is associated with this account.")
        return business

    def get_queryset(self):
        # `getattr` guard keeps drf-spectacular schema generation happy.
        if getattr(self, "swagger_fake_view", False):
            return Service.objects.none()
        return Service.objects.filter(business=self._get_business())

    def perform_create(self, serializer):
        # Force the business from the authenticated user — never trust input.
        serializer.save(business=self._get_business())
