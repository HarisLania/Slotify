"""Staff management endpoints (dashboard, owner-only)."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.exceptions import NotFound

from businesses.models import Business
from businesses.permissions import IsOwner

from .models import StaffMember, TimeOff, WorkingHours
from .serializers import (
    StaffMemberSerializer,
    TimeOffSerializer,
    WorkingHoursSerializer,
)


class OwnerBusinessMixin:
    """Resolves and caches the authenticated owner's business."""

    def get_business(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if business is None:
            raise NotFound("No business is associated with this account.")
        return business


@extend_schema(tags=["staff"])
class StaffViewSet(OwnerBusinessMixin, viewsets.ModelViewSet):
    """
    /api/staff/        GET (list)  POST (add — also creates the user account)
    /api/staff/{id}/   GET  PATCH  DELETE
    """

    serializer_class = StaffMemberSerializer
    permission_classes = [IsOwner]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Only resolve the business for real requests, not schema generation.
        if not getattr(self, "swagger_fake_view", False):
            context["business"] = self.get_business()
        return context

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StaffMember.objects.none()
        return (
            StaffMember.objects.filter(business=self.get_business())
            .select_related("user")
            .prefetch_related("services")
        )


class _StaffScopedListCreateView(OwnerBusinessMixin, generics.ListCreateAPIView):
    """
    Shared base for the nested working-hours / time-off collections.

    Both are scoped to a single staff member (`{id}` in the URL) that must
    belong to the authenticated owner's business.
    """

    permission_classes = [IsOwner]

    def get_staff(self):
        staff = (
            StaffMember.objects.filter(
                pk=self.kwargs["staff_id"], business=self.get_business()
            ).first()
        )
        if staff is None:
            raise NotFound("Staff member not found for your business.")
        return staff


@extend_schema(tags=["staff"])
class WorkingHoursView(_StaffScopedListCreateView):
    """GET/POST /api/staff/{id}/working-hours/"""

    serializer_class = WorkingHoursSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WorkingHours.objects.none()
        return WorkingHours.objects.filter(staff=self.get_staff())

    def perform_create(self, serializer):
        serializer.save(staff=self.get_staff())


@extend_schema(tags=["staff"])
class TimeOffView(_StaffScopedListCreateView):
    """GET/POST /api/staff/{id}/time-off/"""

    serializer_class = TimeOffSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TimeOff.objects.none()
        return TimeOff.objects.filter(staff=self.get_staff())

    def perform_create(self, serializer):
        serializer.save(staff=self.get_staff())
