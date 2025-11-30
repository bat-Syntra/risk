"""Test Middle alert sending with debug info"""
import asyncio
import httpx

API_BASE = "http://localhost:8080"

# Test avec un format simplifié
SAMPLE_MIDDLE = """🚨 Middle Alert 5.0% 🚨
Team A vs Team B [Market : Line] Team A Over 10.5 +110 @ Betsson, Team B Under 11.5 +105 @ DraftKings (Basketball, NBA)"""

async def main():
    async with httpx.AsyncClient(timeout=15.0) as client:
        payload = {"text": SAMPLE_MIDDLE}
        print(f"Sending: {payload}")
        r = await client.post(f"{API_BASE}/api/oddsjam/middle", json=payload)
        print("Status:", r.status_code)
        print("Response:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
