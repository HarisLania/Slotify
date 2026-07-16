from rest_framework.routers import DefaultRouter

from .views import ServiceViewSet

# Mounted at /api/services/
router = DefaultRouter()
router.register("", ServiceViewSet, basename="service")

urlpatterns = router.urls
