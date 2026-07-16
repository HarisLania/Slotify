from django.urls import path

from .views import BusinessDetailView

# Mounted at /api/business/
urlpatterns = [
    path("", BusinessDetailView.as_view(), name="business-detail"),
]
