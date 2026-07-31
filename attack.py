import asyncio
import httpx

URL = "http://127.0.0.1:8000/bookings/naive"
SEAT_ID = 1
NUM_REQUESTS = 50

async def book(client, n):
    try:
        r = await client.post(URL, json={"user_id": f"user_{n}", "seat_id": SEAT_ID})
        return r.status_code
    except Exception as e:
        return f"error: {e}"

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [book(client, n) for n in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)

    confirmed = results.count(200)
    rejected = results.count(409)
    print(f"\n  Fired {NUM_REQUESTS} requests at seat {SEAT_ID}")
    print(f"  Confirmed (200): {confirmed}")
    print(f"  Rejected  (409): {rejected}")
    print(f"\n  A correct system books this seat exactly ONCE.")
    if confirmed > 1:
        print(f"  BUG: {confirmed} people were sold the same seat!\n")
    else:
        print(f"  OK: only one booking succeeded.\n")

asyncio.run(main())