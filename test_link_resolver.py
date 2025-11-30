#!/usr/bin/env python3
"""
Test script pour vérifier le BookmakerLinkResolver
Usage: python3 test_link_resolver.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.bookmaker_link_resolver import BookmakerLinkResolver
from utils.odds_api_links import find_outcome_link_v2
import logging

# Config logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_all_bookmakers():
    """Test tous les bookmakers avec un événement NBA réel"""
    
    resolver = BookmakerLinkResolver()
    
    # Event NBA de test (tu peux remplacer par un vrai)
    test_event = {
        'sport_key': 'basketball_nba',
        'event_id': '6a1207eb38c703385ba9624905fab3ba',
        'teams': ('Chicago Bulls', 'New Orleans Pelicans'),
        'market': 'h2h',
        'outcome': 'Chicago Bulls'
    }
    
    # Liste de tous tes bookmakers
    bookmakers = [
        '888sport',
        'bet365', 
        'BET99',
        'Betsson',
        'BetVictor',
        'Betway',
        'bwin',
        'Casumo',
        'Coolbet',
        'iBet',
        'Jackpot.bet',
        'LeoVegas',
        'Mise-o-jeu',
        'Pinnacle',
        'Proline',
        'Sports Interaction',
        'Stake',
        'TonyBet'
    ]
    
    print("\n" + "="*80)
    print("🧪 TEST DU BOOKMAKER LINK RESOLVER")
    print("="*80)
    print(f"\n📍 Event: {test_event['teams'][0]} vs {test_event['teams'][1]}")
    print(f"🏀 Sport: {test_event['sport_key']}")
    print(f"🎯 Market: {test_event['market']}")
    print(f"📊 Outcome: {test_event['outcome']}")
    print("\n" + "-"*80)
    
    results = {
        'level1': [],  # The Odds API
        'level2': [],  # OpticOdds
        'level3': [],  # Manual patterns
        'level4': []   # Homepage fallback
    }
    
    for bookmaker in bookmakers:
        print(f"\n🔍 Testing {bookmaker}...")
        
        try:
            link = resolver.get_direct_link(
                bookmaker=bookmaker,
                sport_key=test_event['sport_key'],
                event_id=test_event['event_id'],
                market=test_event['market'],
                outcome=test_event['outcome'],
                teams=test_event['teams']
            )
            
            # Déterminer le niveau utilisé
            if '/event/' in link or '/match/' in link or '/evt/' in link or '#/HO/' in link:
                if 'coolbet' in link or 'leovegas' in link or 'betsson' in link:
                    level = 'level1'  # Probablement depuis l'API
                else:
                    level = 'level3'  # Pattern manuel
            elif any(x in link for x in ['/sportsbook', '/sports', '/betting']):
                level = 'level4'  # Homepage
            else:
                level = 'level3'  # Pattern manuel
            
            results[level].append(bookmaker)
            
            print(f"  ✅ {bookmaker}: {link}")
            print(f"  📊 Level: {level.replace('level', 'Level ')}")
            
        except Exception as e:
            print(f"  ❌ {bookmaker}: ERROR - {e}")
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES RÉSULTATS")
    print("="*80)
    
    total = len(bookmakers)
    for level, books in results.items():
        count = len(books)
        pct = (count / total) * 100
        level_name = {
            'level1': 'Level 1 (The Odds API)',
            'level2': 'Level 2 (OpticOdds)',
            'level3': 'Level 3 (Manual Patterns)',
            'level4': 'Level 4 (Homepage Fallback)'
        }[level]
        
        print(f"\n{level_name}: {count}/{total} ({pct:.1f}%)")
        if books:
            print(f"  → {', '.join(books)}")
    
    print("\n" + "="*80)
    print("✅ Test terminé!")
    print("="*80)

def test_specific_bookmaker(bookmaker_name: str):
    """Test un bookmaker spécifique avec différents marchés"""
    
    resolver = BookmakerLinkResolver()
    
    test_cases = [
        {
            'name': 'NBA Moneyline',
            'sport_key': 'basketball_nba',
            'event_id': '6a1207eb38c703385ba9624905fab3ba',
            'teams': ('Chicago Bulls', 'New Orleans Pelicans'),
            'market': 'h2h',
            'outcome': 'Chicago Bulls'
        },
        {
            'name': 'Player Points (Kel\'el Ware)',
            'sport_key': 'basketball_nba',
            'event_id': '6a1207eb38c703385ba9624905fab3ba',
            'teams': ('Miami Heat', 'Detroit Pistons'),
            'market': 'player_points',
            'outcome': 'Kel\'el Ware Over 14.5'
        },
        {
            'name': 'NFL Spread',
            'sport_key': 'americanfootball_nfl',
            'event_id': 'abc123def456',
            'teams': ('Kansas City Chiefs', 'Buffalo Bills'),
            'market': 'spreads',
            'outcome': 'Kansas City Chiefs -3.5'
        }
    ]
    
    print(f"\n🧪 Testing {bookmaker_name} with different markets:")
    print("="*60)
    
    for test in test_cases:
        print(f"\n📍 {test['name']}:")
        try:
            link = resolver.get_direct_link(
                bookmaker=bookmaker_name,
                sport_key=test['sport_key'],
                event_id=test['event_id'],
                market=test['market'],
                outcome=test['outcome'],
                teams=test['teams']
            )
            print(f"  ✅ Link: {link}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

def test_v2_function():
    """Test la fonction find_outcome_link_v2"""
    
    print("\n🧪 Testing find_outcome_link_v2 function:")
    print("="*60)
    
    link = find_outcome_link_v2(
        bookmaker_name='BET99',
        sport_key='basketball_nba',
        event_id='6a1207eb38c703385ba9624905fab3ba',
        market_type='h2h',
        outcome_name='Chicago Bulls',
        teams=('Chicago Bulls', 'New Orleans Pelicans')
    )
    
    print(f"Result: {link}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test BookmakerLinkResolver')
    parser.add_argument('--bookmaker', help='Test specific bookmaker')
    parser.add_argument('--all', action='store_true', help='Test all bookmakers')
    parser.add_argument('--v2', action='store_true', help='Test v2 function')
    
    args = parser.parse_args()
    
    if args.bookmaker:
        test_specific_bookmaker(args.bookmaker)
    elif args.v2:
        test_v2_function()
    else:
        test_all_bookmakers()
