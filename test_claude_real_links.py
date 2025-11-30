"""
Test Claude Vision pour obtenir les VRAIS liens avec event IDs
"""

import os
import asyncio
from utils.smart_link_finder import SmartLinkFinder

async def get_real_links_auburn():
    """
    Force Claude pour obtenir les VRAIS liens avec event IDs
    """
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Pas d'API key Claude configurée!")
        print("Ajoute dans .env: ANTHROPIC_API_KEY=sk-ant-...")
        return
    
    finder = SmartLinkFinder(api_key)
    
    print("🤖 RECHERCHE DES VRAIS LIENS AVEC CLAUDE VISION")
    print("=" * 50)
    print("Match: Auburn vs St. John's")
    print("Casinos: iBet et Sports Interaction")
    print("=" * 50)
    
    # Test 1: Sports Interaction
    print("\n1️⃣ SPORTS INTERACTION - Auburn Under 85.5")
    print("-" * 50)
    
    si_result = await finder.find_bet_link(
        casino='Sports Interaction',
        sport='NCAAB',
        team1='Auburn',
        team2="St. John's",
        bet_team='Auburn',
        market='Team Total Under 85.5',
        force_ai=True  # FORCE CLAUDE!
    )
    
    if si_result.get('success'):
        print(f"✅ VRAI lien trouvé!")
        print(f"   URL: {si_result['url']}")
        print(f"   Event ID: {si_result.get('event_id', 'N/A')}")
        print(f"   Méthode: {si_result.get('method')}")
        print(f"   Coût: ${si_result.get('cost', 0):.3f}")
        
        if si_result.get('event_id'):
            print(f"   💾 Sauvegardé dans le cache!")
    else:
        print(f"❌ Pas trouvé")
        print(f"   Erreur: {si_result.get('error', 'Unknown')}")
        print(f"   URL fallback: {si_result.get('url', 'N/A')}")
    
    # Test 2: iBet (si possible)
    print("\n2️⃣ iBET - Auburn Over 82.5")
    print("-" * 50)
    
    ibet_result = await finder.find_bet_link(
        casino='iBet',
        sport='NCAAB',
        team1='Auburn',
        team2="St. John's",
        bet_team='Auburn',
        market='Team Total Over 82.5',
        force_ai=True  # FORCE CLAUDE!
    )
    
    if ibet_result.get('success'):
        print(f"✅ VRAI lien trouvé!")
        print(f"   URL: {ibet_result['url']}")
        print(f"   Event ID: {ibet_result.get('event_id', 'N/A')}")
        print(f"   Méthode: {ibet_result.get('method')}")
        print(f"   Coût: ${ibet_result.get('cost', 0):.3f}")
    else:
        print(f"❌ Pas trouvé")
        print(f"   Raison: {ibet_result.get('error', 'Site non accessible')}")
        print(f"   URL fallback: {ibet_result.get('url', 'N/A')}")
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 50)
    
    total_cost = si_result.get('cost', 0) + ibet_result.get('cost', 0)
    
    print(f"\n💰 Coût total: ${total_cost:.3f}")
    
    # Cache stats
    stats = finder.get_cache_stats()
    print(f"\n📁 Cache mis à jour:")
    print(f"   - {stats['matches_cached']} matchs stockés")
    print(f"   - {stats['patterns_learned']} patterns appris")
    print(f"   - {stats['events_stored']} événements")
    
    print("\n✅ Les VRAIS liens sont maintenant en cache!")
    print("   La prochaine fois = 0$ et instantané!")
    
    # Affiche les liens pour tester
    print("\n" + "=" * 50)
    print("🔗 VRAIS LIENS À TESTER:")
    print("=" * 50)
    
    if si_result.get('success'):
        print(f"\nSports Interaction:")
        print(f"{si_result['url']}")
    
    if ibet_result.get('success'):
        print(f"\niBet:")
        print(f"{ibet_result['url']}")
    
    return {
        'sports_interaction': si_result,
        'ibet': ibet_result,
        'total_cost': total_cost
    }

if __name__ == "__main__":
    print("🚀 Recherche des VRAIS liens avec Claude Vision\n")
    print("⚠️ ATTENTION: Ça va utiliser Claude (coût ~$0.012)\n")
    
    asyncio.run(get_real_links_auburn())
