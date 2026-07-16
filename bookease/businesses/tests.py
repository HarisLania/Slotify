"""Tests for the owner's business dashboard endpoint."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import Business

User = get_user_model()


class BusinessDashboardTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="SuperSecret123", role="owner"
        )
        self.business = Business.objects.create(
            owner=self.owner, name="Acme", slug="acme", timezone="Asia/Dubai"
        )
        self.url = reverse("business-detail")

    def test_owner_can_retrieve_business(self):
        self.client.force_authenticate(self.owner)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["slug"], "acme")

    def test_owner_can_update_business(self):
        self.client.force_authenticate(self.owner)
        res = self.client.patch(self.url, {"name": "Acme Deluxe", "address": "Dubai"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Acme Deluxe")

    def test_slug_is_read_only(self):
        self.client.force_authenticate(self.owner)
        self.client.patch(self.url, {"slug": "hacked"})
        self.business.refresh_from_db()
        self.assertEqual(self.business.slug, "acme")

    def test_invalid_timezone_rejected(self):
        self.client.force_authenticate(self.owner)
        res = self.client.patch(self.url, {"timezone": "Mars/Phobos"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timezone", res.data)

    def test_unauthenticated_denied(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_non_owner_role_denied(self):
        customer = User.objects.create_user(
            username="cust", password="SuperSecret123", role="customer"
        )
        self.client.force_authenticate(customer)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )
