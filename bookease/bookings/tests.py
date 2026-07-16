"""Tests for the availability engine, public booking flow and dashboard."""
import datetime as dt
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.availability import get_available_slots
from bookings.models import Booking
from businesses.models import Business
from services.models import Service
from staff.models import StaffMember, TimeOff, WorkingHours

User = get_user_model()

DUBAI = ZoneInfo("Asia/Dubai")
# A fixed future weekday (2030-01-07 is a Monday → weekday() == 0).
FUTURE_DATE = dt.date(2030, 1, 7)


def dubai_dt(date, hour, minute=0):
    return dt.datetime(date.year, date.month, date.day, hour, minute, tzinfo=DUBAI)


class AvailabilityEngineTests(APITestCase):
    """Unit tests for get_available_slots (no HTTP involved)."""

    def setUp(self):
        owner = User.objects.create_user(username="o", password="x", role="owner")
        self.business = Business.objects.create(
            owner=owner, name="Acme", slug="acme", timezone="Asia/Dubai"
        )
        self.service = Service.objects.create(
            business=self.business, name="Cut", duration_minutes=30, price=50
        )
        staff_user = User.objects.create_user(username="bob", password="x", role="staff")
        self.staff = StaffMember.objects.create(business=self.business, user=staff_user)
        self.staff.services.add(self.service)
        # Working 09:00–17:00 on the future date's weekday.
        WorkingHours.objects.create(
            staff=self.staff,
            day_of_week=FUTURE_DATE.weekday(),
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )

    def test_generates_expected_number_of_slots(self):
        slots = get_available_slots(self.staff, self.service, FUTURE_DATE)
        # 09:00..16:30 in 15-min steps = 31 candidate starts.
        self.assertEqual(len(slots), 31)
        self.assertEqual(slots[0], dubai_dt(FUTURE_DATE, 9, 0))
        self.assertEqual(slots[-1], dubai_dt(FUTURE_DATE, 16, 30))

    def test_no_working_hours_returns_empty(self):
        # Tuesday has no WorkingHours row.
        other_day = FUTURE_DATE + dt.timedelta(days=1)
        self.assertEqual(get_available_slots(self.staff, self.service, other_day), [])

    def test_existing_booking_blocks_overlapping_slots(self):
        Booking.objects.create(
            business=self.business,
            service=self.service,
            staff=self.staff,
            customer_name="X",
            customer_email="x@x.test",
            start_time=dubai_dt(FUTURE_DATE, 10, 0),
            end_time=dubai_dt(FUTURE_DATE, 10, 30),
            status="confirmed",
        )
        slots = get_available_slots(self.staff, self.service, FUTURE_DATE)
        # 09:45, 10:00, 10:15 now overlap the booking → removed.
        self.assertNotIn(dubai_dt(FUTURE_DATE, 9, 45), slots)
        self.assertNotIn(dubai_dt(FUTURE_DATE, 10, 0), slots)
        self.assertNotIn(dubai_dt(FUTURE_DATE, 10, 15), slots)
        self.assertIn(dubai_dt(FUTURE_DATE, 10, 30), slots)
        self.assertIn(dubai_dt(FUTURE_DATE, 9, 30), slots)
        self.assertEqual(len(slots), 28)

    def test_buffer_extends_blocked_window(self):
        # Service with a 15-min buffer should block an extra trailing slot.
        buffered = Service.objects.create(
            business=self.business,
            name="Cut+",
            duration_minutes=30,
            buffer_minutes=15,
            price=50,
        )
        self.staff.services.add(buffered)
        Booking.objects.create(
            business=self.business,
            service=buffered,
            staff=self.staff,
            customer_name="X",
            customer_email="x@x.test",
            start_time=dubai_dt(FUTURE_DATE, 10, 0),
            end_time=dubai_dt(FUTURE_DATE, 10, 30),
            status="confirmed",
        )
        slots = get_available_slots(self.staff, buffered, FUTURE_DATE)
        # Booking end 10:30 + 15 buffer = 10:45; a new buffered slot also needs
        # its own trailing buffer, so 10:30 is blocked but 10:45 is free.
        self.assertNotIn(dubai_dt(FUTURE_DATE, 10, 30), slots)
        self.assertIn(dubai_dt(FUTURE_DATE, 10, 45), slots)

    def test_time_off_removes_slots(self):
        TimeOff.objects.create(
            staff=self.staff,
            start_datetime=dubai_dt(FUTURE_DATE, 9, 0),
            end_datetime=dubai_dt(FUTURE_DATE, 12, 0),
        )
        slots = get_available_slots(self.staff, self.service, FUTURE_DATE)
        self.assertTrue(all(s >= dubai_dt(FUTURE_DATE, 12, 0) for s in slots))
        self.assertNotIn(dubai_dt(FUTURE_DATE, 9, 0), slots)

    def test_past_slots_excluded_for_today(self):
        today = timezone.now().astimezone(DUBAI).date()
        WorkingHours.objects.update_or_create(
            staff=self.staff,
            day_of_week=today.weekday(),
            defaults={"start_time": dt.time(0, 0), "end_time": dt.time(23, 45)},
        )
        slots = get_available_slots(self.staff, self.service, today)
        now = timezone.now()
        self.assertTrue(all(s + dt.timedelta(minutes=30) > now for s in slots))


class PublicFlowTests(APITestCase):
    def setUp(self):
        owner = User.objects.create_user(username="o", password="x", role="owner")
        self.business = Business.objects.create(
            owner=owner, name="Acme", slug="acme", timezone="Asia/Dubai"
        )
        self.service = Service.objects.create(
            business=self.business, name="Cut", duration_minutes=30, price=50
        )
        Service.objects.create(
            business=self.business, name="Hidden", duration_minutes=30,
            price=50, is_active=False,
        )
        staff_user = User.objects.create_user(username="bob", password="x", role="staff")
        self.staff = StaffMember.objects.create(business=self.business, user=staff_user)
        self.staff.services.add(self.service)
        WorkingHours.objects.create(
            staff=self.staff,
            day_of_week=FUTURE_DATE.weekday(),
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )

    def test_public_services_lists_active_only(self):
        res = self.client.get(reverse("public-services", args=["acme"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [s["name"] for s in res.data]
        self.assertIn("Cut", names)
        self.assertNotIn("Hidden", names)

    def test_public_staff_filtered_by_service(self):
        res = self.client.get(
            reverse("public-staff", args=["acme"]), {"service": self.service.id}
        )
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.staff.id)

    def test_public_slots(self):
        res = self.client.get(
            reverse("public-slots", args=["acme"]),
            {"staff": self.staff.id, "service": self.service.id,
             "date": FUTURE_DATE.isoformat()},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["slots"]), 31)

    def test_public_slots_requires_params(self):
        res = self.client.get(reverse("public-slots", args=["acme"]))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_success(self):
        slots = get_available_slots(self.staff, self.service, FUTURE_DATE)
        res = self.client.post(
            reverse("public-booking-create", args=["acme"]),
            {
                "service": self.service.id,
                "staff": self.staff.id,
                "start_time": slots[0].isoformat(),
                "customer_name": "Jane Doe",
                "customer_email": "jane@x.test",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get()
        self.assertEqual(booking.status, "pending")
        self.assertEqual(booking.end_time, booking.start_time + dt.timedelta(minutes=30))

    def test_create_booking_unavailable_slot_rejected(self):
        # 03:00 is outside working hours → not an available slot.
        bad = dubai_dt(FUTURE_DATE, 3, 0).isoformat()
        res = self.client.post(
            reverse("public-booking-create", args=["acme"]),
            {
                "service": self.service.id,
                "staff": self.staff.id,
                "start_time": bad,
                "customer_name": "Jane",
                "customer_email": "jane@x.test",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", res.data)

    def test_create_booking_staff_not_offering_service_rejected(self):
        lonely = Service.objects.create(
            business=self.business, name="Solo", duration_minutes=30, price=10
        )
        slots = get_available_slots(self.staff, self.service, FUTURE_DATE)
        res = self.client.post(
            reverse("public-booking-create", args=["acme"]),
            {
                "service": lonely.id,
                "staff": self.staff.id,
                "start_time": slots[0].isoformat(),
                "customer_name": "Jane",
                "customer_email": "jane@x.test",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class DashboardBookingTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="o", password="SuperSecret123", role="owner"
        )
        self.business = Business.objects.create(
            owner=self.owner, name="Acme", slug="acme", timezone="Asia/Dubai"
        )
        self.service = Service.objects.create(
            business=self.business, name="Cut", duration_minutes=30, price=50
        )
        su = User.objects.create_user(username="bob", password="x", role="staff")
        self.staff = StaffMember.objects.create(business=self.business, user=su)
        self.booking = Booking.objects.create(
            business=self.business,
            service=self.service,
            staff=self.staff,
            customer_name="Jane",
            customer_email="jane@x.test",
            start_time=dubai_dt(FUTURE_DATE, 10, 0),
            end_time=dubai_dt(FUTURE_DATE, 10, 30),
            status="pending",
        )
        self.client.force_authenticate(self.owner)

    def test_list_bookings(self):
        res = self.client.get(reverse("booking-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_by_status(self):
        res = self.client.get(reverse("booking-list"), {"status": "confirmed"})
        self.assertEqual(len(res.data), 0)

    def test_update_status(self):
        res = self.client.patch(
            reverse("booking-status", args=[self.booking.id]), {"status": "confirmed"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "confirmed")

    def test_invalid_status_rejected(self):
        res = self.client.patch(
            reverse("booking-status", args=[self.booking.id]), {"status": "banana"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bookings_scoped_to_business(self):
        other = User.objects.create_user(
            username="other", password="x", role="owner"
        )
        Business.objects.create(owner=other, name="Rival", slug="rival")
        self.client.force_authenticate(other)
        res = self.client.get(reverse("booking-list"))
        self.assertEqual(len(res.data), 0)
