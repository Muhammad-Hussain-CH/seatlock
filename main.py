import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="SeatLock")

DB_DSN = "postgresql://seatlock:seatlock_pass@localhost:5433/seatlock"

@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(DB_DSN)

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/events/{event_id}/seats")
async def list_seats(event_id: int):
    rows = await app.state.pool.fetch(
        """
        SELECT id, section, row_label, seat_number, status
        FROM seats
        WHERE event_id = $1
        ORDER BY id
        """,
        event_id,
    )
    return {"count": len(rows), "seats": [dict(r) for r in rows]}

class BookingRequest(BaseModel):
    user_id: str
    seat_id: int

@app.post("/bookings/naive")
async def book_naive(req: BookingRequest):
    pool = app.state.pool

    # STEP 1: check if the seat is available (naive: just a read)
    seat = await pool.fetchrow(
        "SELECT id, status, event_id FROM seats WHERE id = $1",
        req.seat_id,
    )
    if seat is None:
        raise HTTPException(status_code=404, detail="Seat not found")
    if seat["status"] != "available":
        raise HTTPException(status_code=409, detail="Seat already taken")

    # (a real system would think/pay here — this gap is where the race lives)

    # STEP 2: create the booking and mark the seat taken
    booking = await pool.fetchrow(
        """
        INSERT INTO bookings (user_id, event_id, status)
        VALUES ($1, $2, 'confirmed')
        RETURNING id
        """,
        req.user_id, seat["event_id"],
    )
    await pool.execute(
        "UPDATE seats SET status = 'booked' WHERE id = $1",
        req.seat_id,
    )

    return {"booking_id": booking["id"], "seat_id": req.seat_id, "status": "confirmed"}


@app.post("/bookings")
async def book_safe(req: BookingRequest):
    pool = app.state.pool

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Atomic: flip the seat to 'booked' ONLY if it's still available.
            # The WHERE clause is the guard — the DB locks the row for us.
            seat = await conn.fetchrow(
                """
                UPDATE seats
                   SET status = 'booked'
                 WHERE id = $1 AND status = 'available'
                RETURNING id, event_id
                """,
                req.seat_id,
            )
            if seat is None:
                raise HTTPException(status_code=409, detail="Seat already taken")

            booking = await conn.fetchrow(
                """
                INSERT INTO bookings (user_id, event_id, status)
                VALUES ($1, $2, 'confirmed')
                RETURNING id
                """,
                req.user_id, seat["event_id"],
            )
            # Safety net: UNIQUE(seat_id) makes a double-insert physically impossible
            await conn.execute(
                "INSERT INTO booking_seats (booking_id, seat_id) VALUES ($1, $2)",
                booking["id"], req.seat_id,
            )

    return {"booking_id": booking["id"], "seat_id": req.seat_id, "status": "confirmed"}