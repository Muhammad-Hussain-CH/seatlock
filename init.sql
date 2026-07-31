CREATE TABLE events (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    venue       TEXT NOT NULL,
    starts_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE seats (
    id           SERIAL PRIMARY KEY,
    event_id     INT NOT NULL REFERENCES events(id),
    section      TEXT NOT NULL,
    row_label    TEXT NOT NULL,
    seat_number  INT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'available',
    hold_id      INT,
    held_until   TIMESTAMPTZ,
    version      INT NOT NULL DEFAULT 0
);

CREATE TABLE holds (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    event_id    INT NOT NULL REFERENCES events(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE bookings (
    id               SERIAL PRIMARY KEY,
    user_id          TEXT NOT NULL,
    event_id         INT NOT NULL REFERENCES events(id),
    status           TEXT NOT NULL DEFAULT 'confirmed',
    idempotency_key  TEXT UNIQUE,
    total_cents      INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE booking_seats (
    booking_id  INT NOT NULL REFERENCES bookings(id),
    seat_id     INT NOT NULL UNIQUE REFERENCES seats(id)
);

INSERT INTO events (name, venue, starts_at)
VALUES ('Coldplay Live', 'National Stadium', now() + interval '30 days');

INSERT INTO seats (event_id, section, row_label, seat_number)
SELECT 1, 'A', chr(65 + (n / 20)), (n % 20) + 1
FROM generate_series(0, 199) AS n;