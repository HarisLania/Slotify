"""Tests for service CRUD, scoping and validation."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import Business
from services.models import Service

User = get_user_model()


class ServiceTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="SuperSecret123", role="owner"
        )
        self.business = Business.objects.create(
            owner=self.owner, name="Acme", slug="acme"
        )
        self.client.force_authenticate(self.owner)
        self.list_url = reverse("service-list")

    def _valid_payload(self, **overrides):
        payload = {
            "name": "Haircut",
            "description": "A trim",
            "duration_minutes": 30,
            "buffer_minutes": 5,
            "price": "50.00",
        }
        payload.update(overrides)
        return payload

    def test_create_service(self):
        res = self.client.post(self.list_url, self._valid_payload())
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(Service.objects.first().business, self.business)

    def test_zero_duration_rejected(self):
        res = self.client.post(self.list_url, self._valid_payload(duration_minutes=0))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration_minutes", res.data)

    def test_negative_price_rejected(self):
        res = self.client.post(self.list_url, self._valid_payload(price="-5"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", res.data)

    def test_list_is_scoped_to_own_business(self):
        # Another owner's service must not appear.
        other = User.objects.create_user(
            username="other", password="SuperSecret123", role="owner"
        )
        other_biz = Business.objects.create(owner=other, name="Rival", slug="rival")
        Service.objects.create(
            business=other_biz, name="Massage", duration_minutes=60, price=100
        )
        Service.objects.create(
            business=self.business, name="Haircut", duration_minutes=30, price=50
        )
        res = self.client.get(self.list_url)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Haircut")

    def test_cannot_access_other_business_service_detail(self):
        other = User.objects.create_user(
            username="other", password="SuperSecret123", role="owner"
        )
        other_biz = Business.objects.create(owner=other, name="Rival", slug="rival")
        svc = Service.objects.create(
            business=other_biz, name="Massage", duration_minutes=60, price=100
        )
        res = self.client.get(reverse("service-detail", args=[svc.id]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
