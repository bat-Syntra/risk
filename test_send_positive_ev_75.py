"""
Envoie une alerte Positive EV (7.5%) au bot via l'API locale.
Doit passer le filtre min_ev_percent=5.0 et s'afficher dans Telegram.
"""
import asyncio
import httpx

API_BASE = "http://localhost:8080"
SAMPLE_POSITIVE_EV_75 = """🚨 Positive EV Alert 7.5% 🚨

Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +125 @ Betsson (Basketball, NBA)"""

async def main():
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(f"{API_BASE}/api/oddsjam/positive_ev", json={"text": SAMPLE_POSITIVE_EV_75})
        print("Status:", r.status_code)
        print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
