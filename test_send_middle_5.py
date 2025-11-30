"""
Envoie une alerte Middle (5%) au bot via l'API locale.
"""
import asyncio
import httpx

API_BASE = "http://localhost:8080"
SAMPLE_MIDDLE = """🚨 Middle Alert 5.0% 🚨
Orlando Magic vs New York Knicks [Player Points : Jalen Suggs Under 12.5/Over 11.5] Jalen Suggs Under 12.5 +110 @ Betsson, Jalen Suggs Over 11.5 +105 @ DraftKings (Basketball, NBA)"""

async def main():
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(f"{API_BASE}/api/oddsjam/middle", json={"text": SAMPLE_MIDDLE})
        print("Status:", r.status_code)
        print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
