"""
Test 3: Test d'intégration complète avec le bot
"""

import asyncio
from bot.odds_verifier import OddsVerifier

async def test_full_integration():
    """
    Simule le flow complet comme dans le vrai bot
    """
    
    print("🤖 Test 3: Intégration complète\n")
    print("=" * 50)
    
    # Message d'arbitrage exact de ton screenshot
    arbitrage_message = """🚨 ALERTE ARBITRAGE - 5.10% 🚨

🏟️ Miami Heat vs Milwaukee Bucks
🏀 NBA - Player Assists : Myles Turner Over 2.5/Myles Turner Under 2.5
🕐 Wednesday, Nov 26 - 07:40 PM ET (débute dans 13h 28min)

💰 CASHH: $750.0
✅ Profit Garanti: $39.88 (ROI: 5.32%)

💯 [BET99] Myles Turner Over 2.5
💵 Miser: $182.00 (+335) → Retour: $791.70

❄️ [Coolbet] Myles Turner Under 2.5
💵 Miser: $568.00 (-256) → Retour: $789.88

⚠️ Odds can change - always verify before betting!"""
    
    print("📝 Message d'arbitrage reçu:")
    print(arbitrage_message[:200] + "...\n")
    
    # Initialise le verifier
    verifier = OddsVerifier()
    
    # Parse le message
    print("🔍 Parsing du message...")
    arb_data = verifier.parse_arbitrage_message(arbitrage_message)
    
    print("\n📊 Données extraites:")
    print(f"   Sport: {arb_data.get('sport')}")
    print(f"   Teams: {arb_data.get('away_team')} vs {arb_data.get('home_team')}")
    print(f"   Player: {arb_data.get('player')}")
    print(f"   Market: {arb_data.get('market_type')}")
    print(f"   Bet1: {arb_data.get('bet1')}")
    print(f"   Bet2: {arb_data.get('bet2')}")
    
    # Génère le message avec boutons
    print("\n🎯 Génération du message avec liens...")
    message, keyboard = await verifier.create_arbitrage_message(arb_data, user_id=123456)
    
    print("\n✅ Message généré:")
    print(message[:300] + "...\n")
    
    print("🔗 Boutons générés:")
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.url:
                print(f"   [{button.text}] → {button.url[:50]}...")
            else:
                print(f"   [{button.text}] → callback: {button.callback_data}")
    
    print("\n" + "=" * 50)
    print("🎯 TEST 3 TERMINÉ!")
    print("\n✅ Le système est prêt!")
    print("   1. Parse les messages ✅")
    print("   2. Génère les liens directs ✅")
    print("   3. Crée les boutons Telegram ✅")
    
    # Retourne les données pour test manuel
    return {
        'parsed_data': arb_data,
        'message': message,
        'keyboard': keyboard
    }

async def test_verify_simulation():
    """
    Simule un click sur "Verify Odds"
    """
    print("\n" + "=" * 50)
    print("🔄 Simulation: User clique 'Verify Odds'\n")
    
    from utils.smart_casino_navigator import SmartCasinoNavigator
    
    async with SmartCasinoNavigator() as nav:
        result = await nav.verify_odds_smart(
            bet1_link='https://bet99.ca/en/sportsbook/search?q=Myles+Turner',
            bet2_link='https://coolbet.com/en/sports/search/Myles+Turner',
            player='Myles Turner',
            line=2.5,
            expected_odds1='+335',
            expected_odds2='-256'
        )
        
        print("📊 Résultat de vérification:")
        print(f"   BET99: {result.get('bet1')}")
        print(f"   Coolbet: {result.get('bet2')}")
        print(f"   Still valid: {result.get('still_valid')}")
    
    return result

if __name__ == "__main__":
    print("🚀 Lancement du test d'intégration complète...\n")
    
    # Test 1: Parsing et génération
    result = asyncio.run(test_full_integration())
    
    # Demande si on veut tester la vérification
    response = input("\n❓ Veux-tu tester la vérification des cotes? (y/n): ")
    
    if response.lower() == 'y':
        print("\n🔍 Test de vérification (ça va ouvrir un browser headless)...")
        verify_result = asyncio.run(test_verify_simulation())
        
        print("\n✅ Test complet terminé!")
    else:
        print("\n✅ Test de base terminé!")
        print("👉 Pour intégrer dans ton bot, copie le code de bot/odds_verifier.py")
