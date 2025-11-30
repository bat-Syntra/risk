"""
Envoie une alerte Positive EV (15%) au bot via l'API locale.
Cette alerte devrait passer le filtre de l'utilisateur (min 10%).
"""
import asyncio
import httpx

API_BASE = "http://localhost:8080"
SAMPLE_POSITIVE_EV_15 = """🚨 Positive EV Alert 15.0% 🚨

Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +160 @ Betsson (Basketball, NBA)"""

async def main():
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(f"{API_BASE}/api/oddsjam/positive_ev", json={"text": SAMPLE_POSITIVE_EV_15})
        print("Status:", r.status_code)
        print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
