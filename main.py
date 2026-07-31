import asyncpg
from fastapi import FastAPI

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