"""
Test de réception des alertes Middle et Good EV
Simule les 3 alertes que tu n'as pas reçues
"""
import asyncio
import httpx

# Les 3 alertes que tu n'as PAS reçues
ALERTS = [
    {
        "type": "middle",
        "text": """🚨 Middle Alert 2.45% 🚨

Hellas Verona FC vs Parma Calcio 1913 [Team Total Corners : Parma Calcio 1913 Over 3.5/Parma Calcio 1913 Under 4] Parma Calcio 1913 Over 3.5 -140 @ Pinny, Parma Calcio 1913 Under 4 +155 @ iBet (Soccer, Italy - Serie A)"""
    },
    {
        "type": "positive_ev",
        "text": """🚨 Positive EV Alert 3.5% 🚨

MoraBanc Andorra vs Joventut [Total Points : Over 170.5] -125 @ bwin (Basketball, Spain - Liga ACB)"""
    },
    {
        "type": "middle",
        "text": """🚨 Middle Alert 5.18% 🚨

Alicia Herrero Linana vs Julia Caffarena [1st Set Game Spread : Julia Caffarena +5.5/Alicia Herrero Linana -4.5] Julia Caffarena +5.5 +165 @ Pinny, Alicia Herrero Linana -4.5 -133 @ Jackpot.bet (Tennis, WTA)"""
    }
]

API_BASE = "http://localhost:8080"


async def test_alert_reception():
    print("=" * 70)
    print("🔍 TEST DE RÉCEPTION DES ALERTES")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, alert in enumerate(ALERTS, 1):
            print(f"📤 Test {i}/{len(ALERTS)}: {alert['type'].upper()}")
            print(f"   Text: {alert['text'][:80]}...")
            
            # Determine endpoint
            if alert['type'] == 'middle':
                endpoint = f"{API_BASE}/api/oddsjam/middle"
            elif alert['type'] == 'positive_ev':
                endpoint = f"{API_BASE}/api/oddsjam/positive_ev"
            else:
                print(f"   ❌ Unknown type: {alert['type']}")
                continue
            
            try:
                response = await client.post(
                    endpoint,
                    json={"text": alert['text']},
                    timeout=10.0
                )
                
                print(f"   📡 Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Response: {result}")
                    
                    # Check if sent
                    sent = result.get('sent', 0)
                    if sent > 0:
                        print(f"   ✅ Envoyé à {sent} user(s)")
                    else:
                        print(f"   ⚠️ AUCUN user n'a reçu!")
                        reason = result.get('reason', 'unknown')
                        print(f"   ⚠️ Raison: {reason}")
                else:
                    print(f"   ❌ Error: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            print()
            await asyncio.sleep(1)
    
    print("=" * 70)
    print("✅ Test terminé!")
    print("=" * 70)
    print()
    print("📋 DIAGNOSTIC:")
    print("   Si 'sent: 0' → Les filtres bloquent l'envoi")
    print("   Si 'sent: 1' → L'alerte devrait être arrivée")
    print()
    print("🔍 Vérifie:")
    print("   1. Ton min_ev_percent (actuellement 5.0%)")
    print("   2. enable_good_odds = True")
    print("   3. enable_middle = True")
    print("   4. Tier = PREMIUM")


if __name__ == "__main__":
    asyncio.run(test_alert_reception())
