"""
Test script - Simule une alerte d'arbitrage
Envoie directement à l'API Risk0_bot sans attendre Nonoriribot
"""
import asyncio
import aiohttp

# Test alert data
TEST_ALERT = {
    "event_id": "test_arb_12345",
    "arb_percentage": 5.16,
    "match": "Toronto Raptors vs Los Angeles Lakers",
    "league": "NBA",
    "market": "Total Points",
    "sport": "Basketball",
    "outcomes": [
        {
            "outcome": "Over 220.5",
            "odds": -200,
            "casino": "Betsson"
        },
        {
            "outcome": "Under 220.5",
            "odds": 255,
            "casino": "Coolbet"
        }
    ]
}

async def send_test_alert():
    """
    Envoie une alerte de test à l'API
    """
    url = "http://localhost:8080/public/drop"
    
    print("🧪 Test Alert - Envoi à Risk0_bot API")
    print("="*60)
    print(f"📊 Arbitrage: {TEST_ALERT['arb_percentage']}%")
    print(f"🏀 Match: {TEST_ALERT['match']}")
    print(f"🎯 League: {TEST_ALERT['league']}")
    print(f"📍 Market: {TEST_ALERT['market']}")
    print(f"🔢 Outcomes: {len(TEST_ALERT['outcomes'])}")
    
    for i, outcome in enumerate(TEST_ALERT['outcomes'], 1):
        odds_str = f"+{outcome['odds']}" if outcome['odds'] > 0 else str(outcome['odds'])
        print(f"   {i}. {outcome['outcome']} @ {odds_str} ({outcome['casino']})")
    
    print("="*60)
    print(f"📤 Envoi à: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=TEST_ALERT) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"\n✅ SUCCESS!")
                    print(f"Response: {result}")
                    print(f"\n💡 Check ton bot Telegram - tu devrais avoir reçu l'alerte!")
                else:
                    print(f"\n❌ ERREUR: Status {response.status}")
                    text = await response.text()
                    print(f"Response: {text}")
    
    except Exception as e:
        print(f"\n❌ ERREUR de connexion: {e}")
        print(f"\n⚠️ Assure-toi que main_new.py est lancé!")

if __name__ == "__main__":
    asyncio.run(send_test_alert())
