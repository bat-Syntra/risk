"""
Test du système Smart Link Finder avec cache
"""

import os
import asyncio
import json
from pathlib import Path
from utils.smart_link_finder import SmartLinkFinder

async def demo_cache_system():
    """
    Démo du système de cache qui apprend
    """
    
    print("🎯 DÉMO DU SYSTÈME SMART LINK FINDER")
    print("=" * 50)
    
    # Check si on a une API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        print("✅ Claude Vision disponible (API key trouvée)")
    else:
        print("⚠️ Mode gratuit uniquement (pas d'API key)")
    
    finder = SmartLinkFinder(api_key)
    
    # Affiche les stats du cache
    stats = finder.get_cache_stats()
    print(f"\n📊 Cache actuel:")
    print(f"   - {stats['matches_cached']} matchs en mémoire")
    print(f"   - {stats['patterns_learned']} patterns appris")
    print(f"   - {stats['events_stored']} événements stockés")
    print(f"   - Taille: {stats['cache_size_kb']:.1f} KB")
    
    print("\n" + "=" * 50)
    print("TEST 1: Premier arbitrage (pas en cache)")
    print("=" * 50)
    
    # Premier appel - va utiliser best effort ou Claude
    result1 = await finder.find_bet_link(
        casino='Betway',
        sport='NCAAB',
        team1='Rice',
        team2='Oral Roberts',
        bet_team='Rice'
    )
    
    print(f"\nRésultat:")
    print(f"   Méthode: {result1.get('method')}")
    print(f"   URL: {result1.get('url', 'N/A')[:60]}...")
    print(f"   Coût: ${result1.get('cost', 0):.3f}")
    
    if result1.get('event_id'):
        print(f"   Event ID: {result1['event_id']} 💾 (sauvegardé!)")
    
    print("\n" + "=" * 50)
    print("TEST 2: Même arbitrage (devrait utiliser le cache)")
    print("=" * 50)
    
    # Deuxième appel - devrait utiliser le cache si disponible
    result2 = await finder.find_bet_link(
        casino='Betway',
        sport='NCAAB',
        team1='Rice',
        team2='Oral Roberts',
        bet_team='Rice'
    )
    
    print(f"\nRésultat:")
    print(f"   Méthode: {result2.get('method')}")
    print(f"   URL: {result2.get('url', 'N/A')[:60]}...")
    print(f"   Coût: ${result2.get('cost', 0):.3f}")
    
    print("\n" + "=" * 50)
    print("📈 ÉVOLUTION DU CACHE")
    print("=" * 50)
    
    # Montre comment le cache grandit
    final_stats = finder.get_cache_stats()
    print(f"Cache après tests:")
    print(f"   - {final_stats['matches_cached']} matchs (+{final_stats['matches_cached'] - stats['matches_cached']})")
    print(f"   - {final_stats['patterns_learned']} patterns (+{final_stats['patterns_learned'] - stats['patterns_learned']})")
    print(f"   - Économies futures: ${result1.get('cost', 0):.3f} par match similaire")
    
    # Montre le contenu du cache
    cache_dir = Path('link_cache')
    if cache_dir.exists():
        print(f"\n📁 Fichiers de cache créés:")
        for file in cache_dir.glob('*.json'):
            size = file.stat().st_size
            print(f"   - {file.name}: {size} bytes")
            
            # Montre un aperçu du contenu
            if size > 0:
                with open(file) as f:
                    content = json.load(f)
                    if content:
                        print(f"     Contenu: {list(content.keys())[:3]}...")
    
    print("\n💡 EXPLICATION:")
    print("   1. Premier appel → Cherche le lien (gratuit ou IA)")
    print("   2. Si trouvé avec IA → Sauvegarde dans le cache")
    print("   3. Appels suivants → Utilise le cache (0$)")
    print("   4. Le cache grandit → De moins en moins besoin d'IA!")
    
    return {
        'initial_stats': stats,
        'final_stats': final_stats,
        'savings_per_match': result1.get('cost', 0)
    }

async def simulate_multiple_arbitrages():
    """
    Simule plusieurs arbitrages pour voir le cache grandir
    """
    
    print("\n" + "=" * 50)
    print("🔄 SIMULATION: 5 arbitrages différents")
    print("=" * 50)
    
    finder = SmartLinkFinder(os.getenv('ANTHROPIC_API_KEY'))
    
    test_matches = [
        ('Duke', 'North Carolina', 'Duke'),
        ('Lakers', 'Celtics', 'Lakers'),
        ('Yankees', 'Red Sox', 'Yankees'),
        ('Real Madrid', 'Barcelona', 'Barcelona'),
        ('Rice', 'Oral Roberts', 'Rice')  # Répétition pour tester cache
    ]
    
    total_cost = 0
    cache_hits = 0
    
    for team1, team2, bet_team in test_matches:
        result = await finder.find_bet_link(
            casino='Betway',
            sport='NCAAB',
            team1=team1,
            team2=team2,
            bet_team=bet_team
        )
        
        cost = result.get('cost', 0)
        total_cost += cost
        
        if result.get('method') == 'cache':
            cache_hits += 1
            print(f"   ✅ {team1} vs {team2}: CACHE HIT! (économisé ${cost:.3f})")
        else:
            print(f"   🔍 {team1} vs {team2}: {result.get('method')} (${cost:.3f})")
    
    print(f"\n📊 Résultats de la simulation:")
    print(f"   - Total dépensé: ${total_cost:.3f}")
    print(f"   - Cache hits: {cache_hits}/{len(test_matches)}")
    print(f"   - Économies: ${cache_hits * 0.006:.3f}")
    
    stats = finder.get_cache_stats()
    print(f"   - Cache final: {stats['matches_cached']} matchs stockés")

if __name__ == "__main__":
    print("🚀 Lancement des tests du Smart Link Finder\n")
    
    # Test principal
    asyncio.run(demo_cache_system())
    
    # Simulation optionnelle
    response = input("\n❓ Veux-tu simuler plusieurs arbitrages? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(simulate_multiple_arbitrages())
    
    print("\n✅ Tests terminés!")
    print("\n💡 Le cache est maintenant dans link_cache/")
    print("   Il sera réutilisé automatiquement à chaque run!")
