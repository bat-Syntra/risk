"""
Test 1: Vérifier que les liens directs fonctionnent
"""

import asyncio
from utils.smart_casino_navigator import SmartCasinoNavigator

async def test_direct_links():
    """
    Test avec un vrai exemple d'arbitrage
    """
    
    # Données d'arbitrage réelles de ton screenshot
    arbitrage_data = {
        'home_team': 'Milwaukee Bucks',
        'away_team': 'Miami Heat',
        'sport': 'NBA',
        'player': 'Myles Turner',
        'market_type': 'Player Assists',
        'bet1': {
            'casino': 'BET99',
            'type': 'Over',
            'line': 2.5,
            'odds': '+335'
        },
        'bet2': {
            'casino': 'Coolbet',
            'type': 'Under', 
            'line': 2.5,
            'odds': '-256'
        }
    }
    
    print("🎯 Test 1: Génération des liens directs\n")
    print("=" * 50)
    
    async with SmartCasinoNavigator() as nav:
        # Teste la génération de liens
        result = await nav.find_bet_links(arbitrage_data)
        
        print(f"✅ BET99 Link:")
        print(f"   {result['bet1_link']}\n")
        
        print(f"✅ Coolbet Link:")
        print(f"   {result['bet2_link']}\n")
        
        if result['enriched_data'].get('event_id'):
            print(f"📊 Données enrichies (via Odds API):")
            print(f"   Event ID: {result['enriched_data']['event_id']}")
            print(f"   Exact teams: {result['enriched_data'].get('exact_home_team')} vs {result['enriched_data'].get('exact_away_team')}")
        else:
            print("ℹ️ Pas d'enrichissement (Odds API key non configurée)")
        
        print("\n" + "=" * 50)
        print("🎯 TEST 1 TERMINÉ!")
        print("\n👉 Ouvre ces liens dans ton browser pour vérifier qu'ils marchent!")
        
        return result

if __name__ == "__main__":
    print("🚀 Lancement du test des liens directs...\n")
    result = asyncio.run(test_direct_links())
    
    print("\n💡 Prochaine étape:")
    print("   1. Copie un des liens ci-dessus")
    print("   2. Ouvre-le dans ton browser")
    print("   3. Vérifie que tu arrives sur la bonne page")
    print("   4. Si oui → passe au test 2!")
