# Event Booking System (Django API)

Role-based Event Booking API using Django REST Framework, with Celery + RabbitMQ background tasks.

## Features

- Two roles:
  - **ORGANIZER**
    - Create, edit, cancel, and delete their own events
    - View bookings made for their own events
  - **CUSTOMER**
    - Browse events
    - Create bookings
    - View and cancel their own bookings
- Background tasks:
  - Booking confirmation email on booking creation
  - Event update email to booked users when organizer updates an event

## Setup

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Celery / RabbitMQ

Run RabbitMQ locally, then run Celery worker:

```bash
celery -A config worker -l info
```

Config:
- `CELERY_BROKER_URL` (default: `amqp://localhost:5672//`)
- `CELERY_RESULT_BACKEND` (default: `rpc://`)

## API Endpoints

Base path: `/api/`

- `GET /events/` – list events (authenticated users)
- `POST /events/` – create event (organizer only)
- `PATCH/PUT /events/{id}/` – update own event (organizer only)
- `DELETE /events/{id}/` – delete own event (organizer only)
- `POST /events/{id}/cancel/` – cancel own event (organizer only)

- `GET /bookings/` – list own bookings (customer only)
- `POST /bookings/` – create booking (customer only)
- `DELETE /bookings/{id}/` – cancel own booking (customer only)

- `GET /organizer/bookings/` – list bookings for organizer's events (organizer only)

## Design Decisions

1. **Single custom user model with role field**
   - Implemented via `bookings.User` (`ORGANIZER` / `CUSTOMER`) to enforce role-based rules consistently.
2. **Event ownership is organizer-bound**
   - Every event stores `organizer`, and update/delete/cancel access is scoped to that owner.
3. **Booking cancellation is soft-cancel**
   - `DELETE /bookings/{id}/` marks booking `CANCELLED` instead of deleting records, preserving history.
4. **Capacity enforced at serializer level**
   - Booking creation checks active booked quantity against event capacity.
5. **Async emails via Celery tasks**
   - API transaction enqueues tasks using `transaction.on_commit(...)` to avoid task dispatch before DB commit.
6. **Console email backend by default**
   - Safer default for local/dev; can be replaced with SMTP settings in deployment.

## Tests

Run:

```bash
python manage.py test bookings
```

Covered:
- Role access control for event creation/update behavior
- Booking creation and email task trigger
- Organizer booking visibility
- Booking ownership enforcement on cancellation