# SeatLock

A concurrent ticket-booking API that never sells the same seat twice.

## The problem

When two people click "book" on the last seat at the same millisecond, a naive
booking system sells it to both. This project builds that bug on purpose, proves
it under load, then fixes it — and measures the difference.

## The race condition, proven

The naive endpoint checks whether a seat is available, then books it — two
separate database operations with a gap between them. Under concurrent load,
many requests pass the check before any of them writes.

Firing 50 simultaneous requests at a single seat:

| Version | Confirmed | Rejected | Correct? |
|---------|-----------|----------|----------|
| Naive (check-then-write) | **32** | 18 | No — 32 people got the same seat |
| Atomic (conditional UPDATE) | **1** | 49 | Yes — exactly one winner |

## The fix

Collapse the check and the write into a single atomic statement:

```sql
UPDATE seats SET status = 'booked'
WHERE id = $1 AND status = 'available'
RETURNING id;
```

The `WHERE` clause is the guard. Postgres locks the row while this runs, so
concurrent requests are serialized: the first flips the seat to `booked` and
gets a row back; every later request matches nothing and receives a clean
`409 Conflict`. A `UNIQUE(seat_id)` constraint on `booking_seats` acts as a
second line of defense — a duplicate booking is physically impossible at the
storage layer, independent of application logic.

## Tech stack

- **FastAPI** — async Python web framework
- **PostgreSQL 16** — running in Docker
- **asyncpg** — async database driver with connection pooling
- **Docker Compose** — one-command local environment

## Running it

```bash
docker compose up -d
docker exec -i seatlock_db psql -U seatlock -d seatlock < init.sql
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive API.

To reproduce the race condition:

```bash
python attack.py   # fires 50 concurrent bookings at one seat
```

## Endpoints

- `GET  /health` — liveness check
- `GET  /events/{id}/seats` — list seat availability
- `POST /bookings/naive` — the buggy version (kept to demonstrate the flaw)
- `POST /bookings` — the correct, atomic version

## What broke along the way

**Docker credential baking.** Postgres only applies `POSTGRES_PASSWORD` the
first time its volume is created. Editing the compose file later has no effect —
the fix is `docker compose down -v` to wipe the volume and recreate.

**Silent port collision.** The app kept failing to authenticate against
Postgres. The container was fine; a local Windows PostgreSQL service was
squatting on port 5432, so the app was connecting to the wrong database
entirely. Remapping the container to 5433 resolved it. Lesson: "same port"
is an assumption worth verifying.

## Concepts demonstrated

Race conditions, database row locking, atomic operations, transaction
isolation, defense-in-depth with unique constraints, and connection pooling.
