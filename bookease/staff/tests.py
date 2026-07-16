"""Tests for staff management, working hours and time-off."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import Business
from services.models import Service
from staff.models import StaffMember

User = get_user_model()


class StaffTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="SuperSecret123", role="owner"
        )
        self.business = Business.objects.create(
            owner=self.owner, name="Acme", slug="acme"
        )
        self.service = Service.objects.create(
            business=self.business, name="Haircut", duration_minutes=30, price=50
        )
        self.client.force_authenticate(self.owner)

    def test_create_staff_provisions_user(self):
        payload = {
            "username": "barber_bob",
            "email": "bob@acme.test",
            "password": "SuperSecret123",
            "first_name": "Bob",
            "services": [self.service.id],
        }
        res = self.client.post(reverse("staff-list"), payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        staff = StaffMember.objects.get()
        self.assertEqual(staff.user.username, "barber_bob")
        self.assertEqual(staff.user.role, "staff")
        self.assertIn(self.service, staff.services.all())

    def _make_staff(self):
        user = User.objects.create_user(
            username="bob", password="SuperSecret123", role="staff"
        )
        staff = StaffMember.objects.create(business=self.business, user=user)
        staff.services.add(self.service)
        return staff

    def test_set_working_hours(self):
        staff = self._make_staff()
        url = reverse("staff-working-hours", args=[staff.id])
        res = self.client.post(
            url, {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_working_hours_end_before_start_rejected(self):
        staff = self._make_staff()
        url = reverse("staff-working-hours", args=[staff.id])
        res = self.client.post(
            url, {"day_of_week": 0, "start_time": "17:00", "end_time": "09:00"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_time", res.data)

    def test_working_hours_bad_day_rejected(self):
        staff = self._make_staff()
        url = reverse("staff-working-hours", args=[staff.id])
        res = self.client.post(
            url, {"day_of_week": 9, "start_time": "09:00", "end_time": "17:00"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_time_off_end_before_start_rejected(self):
        staff = self._make_staff()
        url = reverse("staff-time-off", args=[staff.id])
        res = self.client.post(
            url,
            {
                "start_datetime": "2030-01-10T12:00:00Z",
                "end_datetime": "2030-01-10T09:00:00Z",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_datetime", res.data)

    def test_cannot_add_working_hours_to_other_business_staff(self):
        other = User.objects.create_user(
            username="other", password="SuperSecret123", role="owner"
        )
        other_biz = Business.objects.create(owner=other, name="Rival", slug="rival")
        other_user = User.objects.create_user(
            username="rivalbob", password="SuperSecret123", role="staff"
        )
        other_staff = StaffMember.objects.create(business=other_biz, user=other_user)
        url = reverse("staff-working-hours", args=[other_staff.id])
        res = self.client.post(
            url, {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
