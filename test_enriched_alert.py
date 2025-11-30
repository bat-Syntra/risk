"""
Test du système enrichi avec dates et vérification des cotes
"""
import asyncio
import httpx

# Alert d'arbitrage complète pour tester
TEST_ARBITRAGE = {
    "event_id": "test_enriched_123",
    "arb_percentage": 2.14,
    "match": "Massachusetts vs Bowling Green",
    "league": "NCAAF",
    "market": "Point Spread",
    "sport": "American Football",
    "outcomes": [
        {
            "outcome": "Massachusetts +15.5",
            "odds": -110,
            "casino": "Betway"
        },
        {
            "outcome": "Bowling Green -11",
            "odds": +121,
            "casino": "bet105"
        }
    ]
}

# Alert pour Ajax vs Benfica (celle des screenshots)
TEST_AJAX_BENFICA = {
    "event_id": "ajax_benfica_corners",
    "arb_percentage": 0.57,
    "match": "AFC Ajax vs SL Benfica",
    "league": "UEFA - Champions League",
    "market": "Team Total Corners",
    "sport": "Soccer",
    # Exemple d'intégration complète avec The Odds API
    # Ces deux champs peuvent être fournis par ton système amont
    # pour fiabiliser les dates et deep links.
    "sport_key": "soccer_uefa_champs_league",
    # ID d'exemple observé dans les logs pour Ajax vs Benfica
    # Remplace-le par l'ID réel retourné par The Odds API si besoin.
    "event_id_api": "05828abcad04f663ef67f3501e194268",
    "outcomes": [
        {
            "outcome": "SL Benfica Over 3.5",
            "odds": -278,
            "casino": "LeoVegas"
        },
        {
            "outcome": "SL Benfica Under 4",
            "odds": +270,
            "casino": "Betsson"
        }
    ]
}

async def test_enriched_alert():
    """
    Teste l'envoi d'une alerte enrichie avec:
    - Date/heure du match
    - Cotes actuelles
    - Liens directs
    - Bouton de vérification
    """
    url = "http://localhost:8080/public/drop"
    
    print("🧪 Test Alert Enrichie")
    print("="*60)
    
    # Test 1: NCAAF avec enrichissement
    print("\n📊 Test 1: NCAAF Arbitrage (Massachusetts vs Bowling Green)")
    print("-"*40)
    print(f"Arbitrage: {TEST_ARBITRAGE['arb_percentage']}%")
    print(f"Match: {TEST_ARBITRAGE['match']}")
    print(f"League: {TEST_ARBITRAGE['league']}")
    print(f"Market: {TEST_ARBITRAGE['market']}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=TEST_ARBITRAGE, timeout=20)
            print(f"\nStatus: {response.status_code}")
            if response.status_code == 200:
                print("✅ Envoyé avec succès!")
                print("\n💡 Vérifie ton Telegram:")
                print("   - Tu devrais voir la date/heure du match")
                print("   - Les boutons des casinos avec liens")
                print("   - Un bouton '✅ Vérifier les cotes'")
                print("   - Clique dessus pour actualiser les cotes!")
            else:
                print(f"❌ Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
    
    await asyncio.sleep(2)
    
    # Test 2: Champions League (Ajax vs Benfica)
    print("\n\n📊 Test 2: Champions League (Ajax vs Benfica)")
    print("-"*40)
    print(f"Arbitrage: {TEST_AJAX_BENFICA['arb_percentage']}%")
    print(f"Match: {TEST_AJAX_BENFICA['match']}")
    print(f"League: {TEST_AJAX_BENFICA['league']}")
    print(f"Market: {TEST_AJAX_BENFICA['market']}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=TEST_AJAX_BENFICA, timeout=20)
            print(f"\nStatus: {response.status_code}")
            if response.status_code == 200:
                print("✅ Envoyé avec succès!")
                print("\n💡 Cette fois avec LeoVegas vs Betsson")
                print("   Les bookmakers devraient être corrects maintenant!")
            else:
                print(f"❌ Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
    
    print("\n" + "="*60)
    print("✅ Test terminé!")
    print("\n⚠️ Important:")
    print("1. Les dates et cotes sont récupérées via The Odds API")
    print("2. Si le match n'est pas trouvé, des liens fallback sont utilisés")
    print("3. Clique sur '✅ Vérifier les cotes' pour actualiser")
    print("4. Si l'arbitrage n'existe plus, le message sera mis à jour")

if __name__ == "__main__":
    print("\n🚀 Assure-toi que main_new.py tourne sur le port 8080!")
    print("   cd /Users/z/Library/Mobile\\ Documents/com~apple~CloudDocs/risk0-bot")
    print("   source .venv/bin/activate")
    print("   python3 main_new.py")
    print("\nAppuie sur Enter pour continuer...")
    input()
    
    asyncio.run(test_enriched_alert())
