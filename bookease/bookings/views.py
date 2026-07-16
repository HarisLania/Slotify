"""Booking endpoints — dashboard (auth) and public (customer-facing)."""
import datetime as dt

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business
from businesses.permissions import IsOwner
from services.models import Service
from staff.models import StaffMember

from .availability import get_available_slots
from .models import Booking
from .serializers import (
    BookingSerializer,
    BookingStatusSerializer,
    PublicBookingCreateSerializer,
    PublicServiceSerializer,
    PublicStaffSerializer,
)


# ===========================================================================
# Dashboard (authenticated, owner-only)
# ===========================================================================
class OwnerBusinessMixin:
    def get_business(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if business is None:
            raise NotFound("No business is associated with this account.")
        return business


@extend_schema(
    tags=["bookings"],
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status."),
        OpenApiParameter("staff", OpenApiTypes.INT, description="Filter by staff id."),
        OpenApiParameter("date_from", OpenApiTypes.DATE, description="Inclusive lower bound (YYYY-MM-DD)."),
        OpenApiParameter("date_to", OpenApiTypes.DATE, description="Inclusive upper bound (YYYY-MM-DD)."),
    ],
)
class BookingListView(OwnerBusinessMixin, generics.ListAPIView):
    """GET /api/bookings/ — list & filter the business's bookings."""

    serializer_class = BookingSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()

        qs = Booking.objects.filter(business=self.get_business()).select_related(
            "service", "staff__user"
        )
        params = self.request.query_params

        if status_ := params.get("status"):
            qs = qs.filter(status=status_)
        if staff_id := params.get("staff"):
            qs = qs.filter(staff_id=staff_id)
        if date_from := params.get("date_from"):
            qs = qs.filter(start_time__date__gte=self._parse_date(date_from, "date_from"))
        if date_to := params.get("date_to"):
            qs = qs.filter(start_time__date__lte=self._parse_date(date_to, "date_to"))
        return qs

    @staticmethod
    def _parse_date(value, field):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            raise ValidationError({field: "Expected date in YYYY-MM-DD format."})


@extend_schema(tags=["bookings"])
class BookingDetailView(OwnerBusinessMixin, generics.RetrieveAPIView):
    """GET /api/bookings/{id}/ — booking detail."""

    serializer_class = BookingSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        return Booking.objects.filter(business=self.get_business())


@extend_schema(tags=["bookings"])
class BookingStatusUpdateView(OwnerBusinessMixin, generics.UpdateAPIView):
    """PATCH /api/bookings/{id}/status/ — confirm / cancel / complete etc."""

    serializer_class = BookingStatusSerializer
    permission_classes = [IsOwner]
    http_method_names = ["patch"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        return Booking.objects.filter(business=self.get_business())


# ===========================================================================
# Public booking flow (no auth — scoped by business slug)
# ===========================================================================
class PublicBaseMixin:
    """Resolves the business from the `business_slug` URL kwarg."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_business(self):
        return get_object_or_404(Business, slug=self.kwargs["business_slug"])


@extend_schema(tags=["public"])
class PublicServiceListView(PublicBaseMixin, generics.ListAPIView):
    """GET /api/public/{business_slug}/services/ — active services."""

    serializer_class = PublicServiceSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Service.objects.none()
        return Service.objects.filter(business=self.get_business(), is_active=True)


@extend_schema(
    tags=["public"],
    parameters=[
        OpenApiParameter("service", OpenApiTypes.INT, description="Filter to staff offering this service id."),
    ],
)
class PublicStaffListView(PublicBaseMixin, generics.ListAPIView):
    """GET /api/public/{business_slug}/staff/?service={id} — bookable staff."""

    serializer_class = PublicStaffSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StaffMember.objects.none()
        qs = StaffMember.objects.filter(
            business=self.get_business(), is_active=True
        ).select_related("user")
        if service_id := self.request.query_params.get("service"):
            qs = qs.filter(services__id=service_id)
        return qs.distinct()


@extend_schema(
    tags=["public"],
    parameters=[
        OpenApiParameter("staff", OpenApiTypes.INT, required=True, description="Staff id."),
        OpenApiParameter("service", OpenApiTypes.INT, required=True, description="Service id."),
        OpenApiParameter("date", OpenApiTypes.DATE, required=True, description="Day to check (YYYY-MM-DD)."),
    ],
    responses=inline_serializer(
        name="SlotsResponse",
        fields={
            "date": drf_serializers.CharField(),
            "staff": drf_serializers.IntegerField(),
            "service": drf_serializers.IntegerField(),
            "slots": drf_serializers.ListField(child=drf_serializers.DateTimeField()),
        },
    ),
)
class PublicSlotsView(PublicBaseMixin, APIView):
    """
    GET /api/public/{business_slug}/slots/?staff=&service=&date=YYYY-MM-DD

    Returns the list of available start times for the given staff/service/day.
    """

    def get(self, request, business_slug):
        business = self.get_business()
        staff_id = request.query_params.get("staff")
        service_id = request.query_params.get("service")
        date_str = request.query_params.get("date")

        if not (staff_id and service_id and date_str):
            raise ValidationError(
                "Query params 'staff', 'service' and 'date' are all required."
            )
        try:
            date = dt.date.fromisoformat(date_str)
        except ValueError:
            raise ValidationError({"date": "Expected date in YYYY-MM-DD format."})

        staff = get_object_or_404(
            StaffMember, pk=staff_id, business=business, is_active=True
        )
        service = get_object_or_404(
            Service, pk=service_id, business=business, is_active=True
        )

        slots = get_available_slots(staff, service, date)
        return Response(
            {
                "date": date_str,
                "staff": int(staff_id),
                "service": int(service_id),
                "slots": [s.isoformat() for s in slots],
            }
        )


@extend_schema(tags=["public"], request=PublicBookingCreateSerializer)
class PublicBookingCreateView(PublicBaseMixin, generics.CreateAPIView):
    """POST /api/public/{business_slug}/bookings/ — create a booking."""

    serializer_class = PublicBookingCreateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["business"] = self.get_business()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(
            BookingSerializer(booking).data, status=status.HTTP_201_CREATED
        )
