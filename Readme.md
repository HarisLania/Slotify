# BookEase — Appointment Booking SaaS
### Backend Documentation (MVP)

**Stack**
- **Backend:** Django + Django REST Framework, PostgreSQL, SimpleJWT for auth

### 2.1 Apps

users
businesses
services
staff
bookings

### 2.2 Data Models

```python
# users/models.py
class User(AbstractUser):
    ROLE_CHOICES = [
        ("owner", "Business Owner"),
        ("staff", "Staff Member"),
        ("customer", "Customer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)


# businesses/models.py
class Business(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # used for public booking URL
    timezone = models.CharField(max_length=64, default="Asia/Dubai")
    address = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


# services/models.py
class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    buffer_minutes = models.PositiveIntegerField(default=0)  # gap after booking
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)


# staff/models.py
class StaffMember(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="staff_members")
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    services = models.ManyToManyField(Service, related_name="staff_members")
    is_active = models.BooleanField(default=True)


class WorkingHours(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.IntegerField()  # 0=Monday ... 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ("staff", "day_of_week")


class TimeOff(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="time_off")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)


# bookings/models.py
class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    ]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["staff", "start_time"])]
```

---

### 2.3 API Endpoints

**Auth**
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register business owner (creates User + Business) |
| POST | `/api/auth/login/` | Obtain JWT access/refresh tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Current user profile |

**Business (dashboard, auth required — owner only)**
| Method | Endpoint | Description |
|---|---|---|
| GET/PATCH | `/api/business/` | View/create/update own business profile |

**Services**
| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/services/` | List / create services |
| GET/PATCH/DELETE | `/api/services/{id}/` | Retrieve / update / delete |

**Staff**
| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/staff/` | List / add staff members |
| GET/PATCH/DELETE | `/api/staff/{id}/` | Manage a staff member |
| GET/POST | `/api/staff/{id}/working-hours/` | View/set weekly working hours |
| GET/POST | `/api/staff/{id}/time-off/` | View/add time-off blocks |

**Public booking flow (no auth — customer-facing, scoped by business slug)**
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/public/{business_slug}/services/` | List active services |
| GET | `/api/public/{business_slug}/staff/?service={id}` | Staff offering a service |
| GET | `/api/public/{business_slug}/slots/?staff={id}&service={id}&date=YYYY-MM-DD` | Available time slots for a given day |
| POST | `/api/public/{business_slug}/bookings/` | Create a booking |

**Bookings (dashboard, auth required)**
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/bookings/?status=&staff=&date_from=&date_to=` | List/filter bookings |
| GET | `/api/bookings/{id}/` | Booking detail |
| PATCH | `/api/bookings/{id}/status/` | Update status (confirm/cancel/complete) |

---

### 2.4 Core Business Logic — Slot Availability

The slot-calculation endpoint is the trickiest part; the logic:

1. Get the staff member's `WorkingHours` for the day of week of the requested date.
2. Subtract any `TimeOff` overlapping that date.
3. Generate candidate slots at fixed intervals (e.g. every 15 min) within
   working hours, each slot length = `service.duration_minutes`.
4. Exclude any slot that overlaps an existing `Booking` for that staff member
   (status in `pending`/`confirmed`), accounting for `buffer_minutes`.
5. Exclude slots in the past (if date is today).
6. Return the remaining slots as available times.

Keep this as a plain function/service class (e.g. `services/availability.py`)
rather than jamming it into the view — makes it testable in isolation.

---


### 2.4 API Endpoints

1. Don't expose keys. keep it in a separate env file
2. Create Readme of my document and the update section if you do any updates on your own. Add Insturction of running the project locally as well.
3. Keep the code clean with good comments
4. Add the production flag in env as well
5. Add the swagger and sqlite db for testing
6. Add the test cases as well covering everything and also in readme on steps to run it.
7. Create proper requirements file and work with latest django REST and python.
8. Add the validators as well with proper messages for POST and put.
