"""
Test avec l'arbitrage réel Auburn vs St. John's
"""

import asyncio
import re
from utils.smart_link_finder import SmartLinkFinder, find_arbitrage_links

def parse_arbitrage_message(text):
    """Parse le message d'arbitrage"""
    data = {}
    
    # Teams
    teams_match = re.search(r'🏟️\s*([^vs]+)\s+vs\s+(.+)', text)
    if teams_match:
        data['team1'] = teams_match.group(1).strip()
        data['team2'] = teams_match.group(2).strip()
    
    # Sport
    sport_match = re.search(r'🏀\s*(\w+)', text)
    data['sport'] = sport_match.group(1) if sport_match else 'NCAAB'
    
    # Bet 1
    bet1_match = re.search(r'\[([^\]]+)\]\s*([^\n]+)', text)
    if bet1_match:
        data['bet1'] = {
            'casino': bet1_match.group(1).strip(),
            'team': 'Auburn',
            'market': 'Team Total Over 82.5',
            'odds': '+106'
        }
    
    # Bet 2
    # Cherche la deuxième occurrence
    all_bets = re.findall(r'\[([^\]]+)\]\s*([^\n]+)', text)
    if len(all_bets) >= 2:
        data['bet2'] = {
            'casino': all_bets[1][0].strip(),
            'team': 'Auburn',
            'market': 'Team Total Under 85.5',
            'odds': '+110'
        }
    
    return data

async def test_auburn_arbitrage():
    """Test avec l'arbitrage Auburn"""
    
    arbitrage_text = """🚨 ALERTE ARBITRAGE - 3.84% 🚨

🏟️ Auburn vs St. John's
🏀 NCAAB - Team Total : Auburn Over 82.5/Auburn Under 85.5
🕐 Wednesday, Nov 26 - 08:00 PM ET (débute dans 11h 24min)

💰 CASHH: $750.0
✅ Profit Garanti: $29.92 (ROI: 3.99%)

📱 [iBet] Auburn Over 82.5
💵 Miser: $378.61 (+106) → Retour: $779.94

🏟️ [Sports Interaction] Auburn Under 85.5
💵 Miser: $371.39 (+110) → Retour: $779.92"""
    
    print("🏀 TEST AVEC ARBITRAGE RÉEL: Auburn vs St. John's")
    print("=" * 50)
    
    # Parse
    data = parse_arbitrage_message(arbitrage_text)
    
    print(f"\n📊 Données extraites:")
    print(f"   Match: {data['team1']} vs {data['team2']}")
    print(f"   Sport: {data['sport']}")
    print(f"   Bet1: {data['bet1']['casino']} - {data['bet1']['market']}")
    print(f"   Bet2: {data['bet2']['casino']} - {data['bet2']['market']}")
    
    print("\n" + "=" * 50)
    print("🔍 RECHERCHE DES LIENS DIRECTS")
    print("=" * 50)
    
    # Utilise le Smart Link Finder
    result = await find_arbitrage_links(data)
    
    print("\n" + "=" * 50)
    print("📋 RÉSULTATS FINAUX")
    print("=" * 50)
    
    # iBet
    print(f"\n📱 iBet:")
    print(f"   Méthode: {result['bet1']['method']}")
    print(f"   URL: {result['bet1']['url']}")
    print(f"   Coût: ${result['bet1'].get('cost', 0):.3f}")
    
    # Sports Interaction
    print(f"\n🏟️ Sports Interaction:")
    print(f"   Méthode: {result['bet2']['method']}")
    print(f"   URL: {result['bet2']['url']}")
    print(f"   Coût: ${result['bet2'].get('cost', 0):.3f}")
    
    print(f"\n💰 Coût total: ${result['total_cost']:.3f}")
    
    # Test avec force AI si disponible
    print("\n" + "=" * 50)
    print("🤖 TEST AVEC CLAUDE (pour obtenir le VRAI lien)")
    print("=" * 50)
    
    import os
    if os.getenv('ANTHROPIC_API_KEY'):
        response = input("\nVeux-tu essayer avec Claude pour avoir le VRAI lien? (y/n): ")
        if response.lower() == 'y':
            finder = SmartLinkFinder(os.getenv('ANTHROPIC_API_KEY'))
            
            print("\n🎯 Recherche du VRAI lien Sports Interaction avec Claude...")
            ai_result = await finder.find_bet_link(
                casino='Sports Interaction',
                sport='NCAAB',
                team1='Auburn',
                team2="St. John's",
                bet_team='Auburn',
                market='Team Total Under',
                force_ai=True
            )
            
            if ai_result['success']:
                print(f"   ✅ VRAI lien trouvé!")
                print(f"   URL: {ai_result['url']}")
                print(f"   Event ID: {ai_result.get('event_id', 'N/A')}")
                print(f"   Coût: ${ai_result.get('cost', 0):.3f}")
                print(f"   💾 Sauvegardé dans le cache!")
            else:
                print(f"   ❌ Pas trouvé: {ai_result.get('error')}")
    else:
        print("   ⚠️ Pas de clé API Claude configurée")
    
    print("\n✅ Test terminé!")
    
    # Affiche les liens pour copier
    print("\n" + "=" * 50)
    print("🔗 LIENS À TESTER DANS TON BROWSER:")
    print("=" * 50)
    print(f"\niBet:\n{result['bet1']['url']}")
    print(f"\nSports Interaction:\n{result['bet2']['url']}")

if __name__ == "__main__":
    print("🚀 Test avec l'arbitrage Auburn vs St. John's\n")
    asyncio.run(test_auburn_arbitrage())
