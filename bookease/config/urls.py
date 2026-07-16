"""
Root URL configuration for BookEase.

All API routes are namespaced under `/api/`. Interactive API docs
(Swagger UI + Redoc) are served from `/api/docs/` and `/api/redoc/`.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- Auth (register / login / refresh / me) -------------------------
    path("api/auth/", include("users.urls")),

    # --- Dashboard (owner-authenticated) --------------------------------
    path("api/business/", include("businesses.urls")),
    path("api/services/", include("services.urls")),
    path("api/staff/", include("staff.urls")),
    path("api/bookings/", include("bookings.urls")),

    # --- Public customer-facing booking flow (no auth) ------------------
    path("api/public/", include("bookings.public_urls")),

    # --- OpenAPI schema + Swagger / Redoc UIs ---------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Serve uploaded media (e.g. business logos) during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
