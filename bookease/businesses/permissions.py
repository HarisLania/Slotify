from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allows access only to authenticated users with the `owner` role."""

    message = "Only business owners can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "owner"
        )
