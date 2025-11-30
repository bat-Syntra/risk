"""
Force l'utilisation de Claude pour voir le cache
"""

import os
import asyncio
from utils.smart_link_finder import SmartLinkFinder

async def test_with_ai():
    """
    Force Claude pour obtenir le VRAI lien avec event ID
    """
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Pas d'API key - impossible de tester Claude")
        return
    
    finder = SmartLinkFinder(api_key)
    
    print("🤖 TEST: Forcer Claude Vision pour obtenir le VRAI lien")
    print("=" * 50)
    
    # Force l'utilisation de Claude (force_ai=True)
    print("\n1️⃣ Premier appel - Claude va chercher le vrai lien...")
    result1 = await finder.find_bet_link(
        casino='Betway',
        sport='NCAAB',
        team1='Rice',
        team2='Oral Roberts',
        bet_team='Rice',
        force_ai=True  # ← FORCE CLAUDE!
    )
    
    print(f"\nRésultat:")
    print(f"   Méthode: {result1.get('method')}")
    print(f"   URL: {result1.get('url', 'N/A')}")
    print(f"   Event ID: {result1.get('event_id', 'N/A')}")
    print(f"   Coût: ${result1.get('cost', 0):.3f}")
    
    if result1.get('event_id'):
        print(f"   ✅ Event ID sauvegardé dans le cache!")
    
    print("\n" + "-" * 50)
    print("2️⃣ Deuxième appel - Devrait utiliser le CACHE...")
    
    # Deuxième appel SANS forcer - devrait utiliser le cache
    result2 = await finder.find_bet_link(
        casino='Betway',
        sport='NCAAB',
        team1='Rice',
        team2='Oral Roberts',
        bet_team='Rice',
        force_ai=False  # Pas de force
    )
    
    print(f"\nRésultat:")
    print(f"   Méthode: {result2.get('method')}")
    print(f"   URL: {result2.get('url', 'N/A')}")
    print(f"   Coût: ${result2.get('cost', 0):.3f}")
    
    if result2.get('method') == 'cache':
        print(f"   🎉 CACHE HIT! Économisé ${result1.get('cost', 0):.3f}")
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ:")
    print(f"   Première recherche: ${result1.get('cost', 0):.3f} (Claude)")
    print(f"   Recherches suivantes: $0.000 (Cache)")
    print(f"   Économies sur 100 fois le même match: ${result1.get('cost', 0) * 99:.2f}")

if __name__ == "__main__":
    print("⚠️ ATTENTION: Ce test va utiliser Claude Vision (coût ~$0.006)\n")
    response = input("Continuer? (y/n): ")
    
    if response.lower() == 'y':
        asyncio.run(test_with_ai())
    else:
        print("Test annulé")
