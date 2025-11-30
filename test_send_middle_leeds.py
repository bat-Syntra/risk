"""
Envoie l'alerte Middle (Leeds vs Aston Villa) fournie par l'utilisateur vers l'API locale.
"""
import asyncio
import httpx

API_BASE = "http://localhost:8080"
MIDDLE_TEXT = """🚨 Middle Alert 2.26% 🚨

Leeds United FC vs Aston Villa FC [Team Total Corners : Leeds United FC Over 3.5/Leeds United FC Under 4] Leeds United FC Over 3.5 -220 @ LeoVegas, Leeds United FC Under 4 +245 @ Betsson (Soccer, England - Premier League)"""

async def main():
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{API_BASE}/api/oddsjam/middle", json={"text": MIDDLE_TEXT})
        print("Status:", r.status_code)
        print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
