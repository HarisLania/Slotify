# BookEase — Appointment Booking SaaS (Backend)

A multi-tenant appointment-booking backend built with **Django 5.2 + Django REST
Framework**. Business owners manage their services, staff and bookings from an
authenticated dashboard, while customers book appointments through a public,
no-login flow scoped by a business slug.

- **Auth:** JWT (SimpleJWT)
- **Database:** SQLite out of the box (dev/testing); PostgreSQL in production via `DATABASE_URL`
- **API docs:** Swagger UI + Redoc (drf-spectacular)

---

## 1. Project structure

```
bookease/
├── manage.py
├── requirements.txt
├── .env.example          # template — copy to .env
├── .env                  # local dev config (SQLite, DEBUG=True). NOT for prod.
├── .gitignore
├── config/               # project settings package
│   ├── settings.py       # env-driven; secrets read from .env
│   ├── urls.py           # routes + Swagger/Redoc
│   ├── wsgi.py / asgi.py
├── users/                # custom User + auth (register/login/refresh/me)
├── businesses/           # Business model + owner dashboard endpoint
├── services/             # Service CRUD
├── staff/                # StaffMember, WorkingHours, TimeOff
└── bookings/             # Booking model, availability engine, public flow
    └── availability.py   # slot-calculation logic (unit-testable, standalone)
```

---

## 2. Running locally

### Prerequisites
- Python 3.10+

### Steps

```bash
# 1. Clone / open the project
cd bookease

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env             # then edit values (a working dev .env is already included)

# 5. Apply migrations (creates db.sqlite3)
python manage.py migrate

# 6. Create an admin user (optional, for the Django admin at /admin/)
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver
```

The API is now at `http://127.0.0.1:8000/`.

- **Swagger UI:** http://127.0.0.1:8000/api/docs/
- **Redoc:** http://127.0.0.1:8000/api/redoc/
- **OpenAPI schema:** http://127.0.0.1:8000/api/schema/
- **Django admin:** http://127.0.0.1:8000/admin/

### Quick smoke test
```bash
# Register an owner (also creates their business)
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"acme","email":"a@acme.test","password":"SuperSecret123","business_name":"Acme Salon","timezone":"Asia/Dubai"}'

# Log in to get a JWT
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"acme","password":"SuperSecret123"}'
```

---

## 3. Environment variables

All configuration is read from `.env` (see `.env.example`). Nothing sensitive is
hard-coded in source.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Debug mode | `False` |
| `PRODUCTION` | **Production hardening flag** — enables HTTPS redirect, secure cookies, HSTS | `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `*` |
| `DATABASE_URL` | DB connection URL. Unset → local SQLite | SQLite `db.sqlite3` |
| `JWT_ACCESS_MINUTES` | Access-token lifetime | `60` |
| `JWT_REFRESH_DAYS` | Refresh-token lifetime | `7` |
| `CORS_ALLOW_ALL_ORIGINS` | Allow any frontend origin | `True` |
| `CORS_ALLOWED_ORIGINS` | Explicit allowed origins (when the above is False) | empty |

**Production example:**
```
DEBUG=False
PRODUCTION=True
SECRET_KEY=<long-random-value>
ALLOWED_HOSTS=api.bookease.com
DATABASE_URL=postgres://user:pass@host:5432/bookease
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://app.bookease.com
```

> `PRODUCTION=True` turns on `SECURE_SSL_REDIRECT`, secure/HSTS cookies and
> related hardening. Keep it `False` for local development.

---

## 4. API reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a business owner (creates User + Business) |
| POST | `/api/auth/login/` | Obtain JWT access/refresh tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Current user profile |

### Dashboard (JWT required, owner only)
| Method | Endpoint | Description |
|---|---|---|
| GET/PATCH | `/api/business/` | View/update own business profile |
| GET/POST | `/api/services/` | List / create services |
| GET/PATCH/DELETE | `/api/services/{id}/` | Retrieve / update / delete a service |
| GET/POST | `/api/staff/` | List / add staff (also provisions the staff user) |
| GET/PATCH/DELETE | `/api/staff/{id}/` | Manage a staff member |
| GET/POST | `/api/staff/{id}/working-hours/` | View/set weekly working hours |
| GET/POST | `/api/staff/{id}/time-off/` | View/add time-off blocks |
| GET | `/api/bookings/?status=&staff=&date_from=&date_to=` | List/filter bookings |
| GET | `/api/bookings/{id}/` | Booking detail |
| PATCH | `/api/bookings/{id}/status/` | Update status (confirm/cancel/complete) |

### Public booking flow (no auth, scoped by business slug)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/public/{slug}/services/` | List active services |
| GET | `/api/public/{slug}/staff/?service={id}` | Staff offering a service |
| GET | `/api/public/{slug}/slots/?staff={id}&service={id}&date=YYYY-MM-DD` | Available time slots |
| POST | `/api/public/{slug}/bookings/` | Create a booking |

---

## 5. Slot-availability logic

Lives in `bookings/availability.py` as a standalone, testable function
`get_available_slots(staff, service, date)`:

1. Read the staff member's `WorkingHours` for that weekday (times are in the
   business's own IANA timezone).
2. Subtract any overlapping `TimeOff`.
3. Generate candidate slots every 15 minutes, each `service.duration_minutes` long.
4. Drop candidates overlapping an existing `pending`/`confirmed` booking,
   expanding each interval by its `buffer_minutes`.
5. Drop slots in the past (when the date is today).
6. Return the remaining start times (timezone-aware).

The public "create booking" endpoint **re-validates** the requested slot against
this function server-side, so a slot taken between viewing and submitting is
rejected rather than double-booked.

---

## 6. Running the tests

The suite uses Django's test runner and an in-memory/SQLite test database — no
extra services required.

```bash
# Run everything
python manage.py test

# Run a single app's tests
python manage.py test bookings

# More verbose
python manage.py test -v2
```

**Coverage** (44 tests): registration & JWT auth, business dashboard + timezone
validation, service CRUD/scoping/validators, staff provisioning, working-hours &
time-off validation, the availability engine (slot generation, existing-booking
and buffer blocking, time-off, past-slot exclusion), the full public booking flow,
and dashboard booking listing/filtering/status updates.

Optional coverage report:
```bash
pip install coverage
coverage run manage.py test && coverage report
```

---

## 7. Notes & design decisions

These are choices made while implementing the MVP from the spec:

- **Custom user model** (`users.User`) with `role` (`owner`/`staff`/`customer`)
  and `phone`, set as `AUTH_USER_MODEL` from the first migration.
- **Registration** creates the `User` (role=owner) **and** their `Business`
  atomically. The business `slug` is auto-generated from the name and made unique
  (`acme-salon`, `acme-salon-2`, …); it is read-only afterward so public links
  never break. MVP assumes **one business per owner**.
- **Adding staff** provisions the underlying `User` account (role=staff) from
  nested write-only credential fields on the same request.
- **Security:** endpoints are `IsAuthenticated` by default; dashboard endpoints
  additionally require the `owner` role and are always scoped to the caller's own
  business (cross-tenant access returns 404). Public endpoints opt out of auth
  explicitly.
- **Validation:** serializer-level validators with clear messages for POST/PUT
  (positive durations, non-negative price/buffer, valid IANA timezone,
  `end > start` for working hours and time-off, weekday range 0–6, slot
  availability on booking).
- **API docs:** drf-spectacular serves Swagger UI (`/api/docs/`) and Redoc
  (`/api/redoc/`).
- **Database:** SQLite by default for local dev and tests; set `DATABASE_URL` to
  a Postgres URL for production. `psycopg` and `gunicorn` are included in
  `requirements.txt` for deployment.
- **Timezones:** `USE_TZ=True`; datetimes stored in UTC, availability computed in
  each business's configured timezone.

### Changelog
- **v1.0.0** — Initial MVP: users/auth, businesses, services, staff (+working
  hours & time-off), bookings, availability engine, public booking flow, Swagger,
  and full test suite.
