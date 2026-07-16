"""Tests for registration and JWT authentication."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import Business

User = get_user_model()


class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-register")
        self.payload = {
            "username": "acme_owner",
            "email": "owner@acme.test",
            "password": "SuperSecret123",
            "business_name": "Acme Salon",
            "timezone": "Asia/Dubai",
        }

    def test_register_creates_user_and_business(self):
        res = self.client.post(self.url, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="acme_owner")
        self.assertEqual(user.role, "owner")
        business = Business.objects.get(owner=user)
        self.assertEqual(business.name, "Acme Salon")
        self.assertEqual(business.slug, "acme-salon")
        self.assertEqual(res.data["business"]["slug"], "acme-salon")

    def test_duplicate_username_rejected(self):
        self.client.post(self.url, self.payload)
        dupe = {**self.payload, "email": "other@acme.test"}
        res = self.client.post(self.url, dupe)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

    def test_duplicate_email_rejected(self):
        self.client.post(self.url, self.payload)
        dupe = {**self.payload, "username": "other_owner"}
        res = self.client.post(self.url, dupe)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_weak_password_rejected(self):
        weak = {**self.payload, "password": "123"}
        res = self.client.post(self.url, weak)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.data)

    def test_slug_is_made_unique(self):
        self.client.post(self.url, self.payload)
        second = {
            "username": "acme2",
            "email": "acme2@acme.test",
            "password": "SuperSecret123",
            "business_name": "Acme Salon",
        }
        res = self.client.post(self.url, second)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["business"]["slug"], "acme-salon-2")


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jane", email="jane@x.test", password="SuperSecret123", role="owner"
        )

    def test_login_returns_tokens(self):
        res = self.client.post(
            reverse("auth-login"),
            {"username": "jane", "password": "SuperSecret123"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_refresh_returns_new_access(self):
        login = self.client.post(
            reverse("auth-login"),
            {"username": "jane", "password": "SuperSecret123"},
        )
        res = self.client.post(
            reverse("auth-refresh"), {"refresh": login.data["refresh"]}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_me_requires_authentication(self):
        self.assertEqual(
            self.client.get(reverse("auth-me")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_me_returns_profile(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "jane")
