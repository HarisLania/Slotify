"""Authentication views: register, login, refresh, and current-user profile."""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/

    Creates a business owner account together with their business, and
    returns the created user plus the new business id/slug.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        responses={201: OpenApiResponse(description="Account and business created.")},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        business = serializer.context["business"]
        return Response(
            {
                "user": UserSerializer(user).data,
                "business": {
                    "id": business.id,
                    "name": business.name,
                    "slug": business.slug,
                },
            },
            status=status.HTTP_201_CREATED,
        )


# Login and refresh reuse SimpleJWT's views verbatim; we subclass only so the
# endpoints get documented under our own names in the schema and are easy to
# customise later.
class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — obtain JWT access & refresh tokens."""

    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ — exchange a refresh token for a new access token."""

    permission_classes = [AllowAny]


class MeView(APIView):
    """GET /api/auth/me/ — the authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)
