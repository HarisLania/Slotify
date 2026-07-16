"""
Slot-availability engine.

Kept deliberately free of view/serializer concerns so it can be unit-tested
in isolation. The public booking flow and the dashboard both rely on it.

Algorithm (see Backend-Instructions §2.4):
    1. Look up the staff member's WorkingHours for the requested weekday.
    2. Subtract any TimeOff overlapping that day.
    3. Generate candidate slots at a fixed interval within working hours,
       each `service.duration_minutes` long.
    4. Drop candidates overlapping an existing pending/confirmed Booking,
       accounting for `buffer_minutes`.
    5. Drop candidates in the past (when the date is today).
    6. Return the survivors.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from django.utils import timezone

# How finely we step when generating candidate start times.
SLOT_INTERVAL_MINUTES = 15


def _combine(date: dt.date, time: dt.time, tz: ZoneInfo) -> dt.datetime:
    """Combine a local date + time into a timezone-aware datetime."""
    return dt.datetime.combine(date, time, tzinfo=tz)


def get_available_slots(staff, service, date: dt.date) -> list[dt.datetime]:
    """
    Return a list of timezone-aware datetimes representing bookable slot
    *start* times for `staff` performing `service` on `date`.

    Times are expressed in the business's own timezone.
    """
    business_tz = ZoneInfo(staff.business.timezone)
    duration = dt.timedelta(minutes=service.duration_minutes)
    buffer_ = dt.timedelta(minutes=service.buffer_minutes)
    interval = dt.timedelta(minutes=SLOT_INTERVAL_MINUTES)

    # 1. Working hours for this weekday (0=Mon ... 6=Sun). One row per day.
    working = staff.working_hours.filter(day_of_week=date.weekday()).first()
    if working is None:
        return []

    window_start = _combine(date, working.start_time, business_tz)
    window_end = _combine(date, working.end_time, business_tz)

    # 2. Time-off blocks that intersect this working window.
    time_off = list(
        staff.time_off.filter(
            start_datetime__lt=window_end, end_datetime__gt=window_start
        )
    )

    # 4. Existing bookings that block slots (pending / confirmed) for the day.
    from .models import Booking  # local import avoids circular dependency

    bookings = list(
        Booking.objects.filter(
            staff=staff,
            status__in=Booking.BLOCKING_STATUSES,
            start_time__lt=window_end,
            end_time__gt=window_start - buffer_,
        ).select_related("service")
    )

    now = timezone.now()
    slots: list[dt.datetime] = []

    candidate = window_start
    while candidate + duration <= window_end:
        slot_start = candidate
        slot_end = candidate + duration

        # 5. Skip slots in the past.
        if slot_end <= now:
            candidate += interval
            continue

        if _conflicts_with_time_off(slot_start, slot_end, time_off):
            candidate += interval
            continue

        if _conflicts_with_booking(slot_start, slot_end, buffer_, bookings):
            candidate += interval
            continue

        slots.append(slot_start)
        candidate += interval

    return slots


def _conflicts_with_time_off(slot_start, slot_end, time_off) -> bool:
    """True if the slot overlaps any time-off block."""
    for off in time_off:
        if slot_start < off.end_datetime and off.start_datetime < slot_end:
            return True
    return False


def _conflicts_with_booking(slot_start, slot_end, new_buffer, bookings) -> bool:
    """
    True if the slot overlaps an existing booking.

    Each interval is expanded by its trailing buffer so consecutive
    appointments keep the required gap:
        existing occupies [start, end + existing_service_buffer]
        candidate occupies [start, end + new_service_buffer]
    """
    candidate_end = slot_end + new_buffer
    for booking in bookings:
        existing_buffer = dt.timedelta(minutes=booking.service.buffer_minutes)
        existing_end = booking.end_time + existing_buffer
        if slot_start < existing_end and booking.start_time < candidate_end:
            return True
    return False
