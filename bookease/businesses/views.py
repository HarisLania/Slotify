"""Dashboard endpoint for the owner to view/update their own business."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.exceptions import NotFound

from .models import Business
from .permissions import IsOwner
from .serializers import BusinessSerializer


@extend_schema(tags=["business"])
class BusinessDetailView(RetrieveUpdateAPIView):
    """
    GET  /api/business/  — retrieve the authenticated owner's business.
    PATCH/PUT /api/business/ — update it.

    Scoped to `request.user`, so an owner can only ever see/edit their own
    business regardless of ids.
    """

    serializer_class = BusinessSerializer
    permission_classes = [IsOwner]
    http_method_names = ["get", "patch", "put"]

    def get_object(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if business is None:
            raise NotFound("No business is associated with this account.")
        return business
