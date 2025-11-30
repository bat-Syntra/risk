"""
Test complet du système Good Odds (Positive EV)
Simule une vraie alerte et affiche le message formaté
"""
import asyncio
import sys
from database import SessionLocal
from models.user import User

# Sample notification text
SAMPLE_POSITIVE_EV = """🚨 Positive EV Alert 7.5% 🚨

Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +125 @ Betsson (Basketball, NBA)"""

SAMPLE_POSITIVE_EV_2 = """🚨 Positive EV Alert 3.5% 🚨

MoraBanc Andorra vs Joventut [Total Points : Over 170.5] -125 @ bwin (Basketball, Spain - Liga ACB)"""


async def test_good_odds():
    print("=" * 60)
    print("🎯 TEST GOOD ODDS - SYSTÈME COMPLET")
    print("=" * 60)
    print()
    
    # Import parser and formatter
    from utils.oddsjam_parser import parse_positive_ev_notification
    from utils.oddsjam_formatters import format_good_odds_message
    from utils.good_odds_calculator import (
        calculate_true_winrate,
        calculate_good_odds_example,
        calculate_kelly_bankroll,
        get_ev_quality_tag
    )
    
    # Test 1: Parse notification
    print("📋 Test 1: Parsing notification...")
    parsed = parse_positive_ev_notification(SAMPLE_POSITIVE_EV)
    
    if not parsed:
        print("❌ Failed to parse!")
        return
    
    print(f"✅ Parsed successfully:")
    print(f"   - EV: {parsed['ev_percent']}%")
    print(f"   - Bookmaker: {parsed['bookmaker']}")
    print(f"   - Odds: {parsed['odds']}")
    print(f"   - Player: {parsed.get('player', 'N/A')}")
    print()
    
    # Test 2: Calculate win rate
    print("📊 Test 2: Calculs mathématiques...")
    odds_int = int(parsed['odds'].replace('+', ''))
    ev_percent = parsed['ev_percent']
    stake = 750.0
    
    true_winrate = calculate_true_winrate(odds_int, ev_percent)
    print(f"✅ TRUE win rate: {true_winrate*100:.1f}% (pas 50%!)")
    
    # Test 3: Example over 10 bets
    example = calculate_good_odds_example(odds_int, stake, ev_percent, 10)
    print(f"✅ Exemple 10 bets:")
    print(f"   - Wins: {example['expected_wins']:.1f} fois")
    print(f"   - Losses: {example['expected_losses']:.1f} fois")
    print(f"   - NET profit: ${example['net_profit']:.2f}")
    print(f"   - ROI: {example['roi']:.1f}%")
    print()
    
    # Test 4: Kelly bankroll
    bankroll = calculate_kelly_bankroll(stake, ev_percent, odds_int)
    print(f"✅ Bankroll Kelly (0.25): ${bankroll:,.0f}")
    print()
    
    # Test 5: EV quality tag
    quality = get_ev_quality_tag(ev_percent, odds_int)
    print(f"✅ Quality tag: {quality['tag']}")
    print(f"   - Tier: {quality['tier']}")
    print(f"   - Recommended: {quality['recommended_for']}")
    print()
    
    # Test 6: Format message (French)
    print("💬 Test 6: Message formaté (FR)...")
    message_fr = format_good_odds_message(parsed, stake, 'fr', 'beginner', 0)
    print("─" * 60)
    print(message_fr)
    print("─" * 60)
    print()
    
    # Test 7: Check user settings
    print("👤 Test 7: Vérification settings utilisateur...")
    db = SessionLocal()
    try:
        # Get your user
        user = db.query(User).filter(User.telegram_id == 8213628656).first()
        if user:
            print(f"✅ User trouvé: {user.username}")
            print(f"   - Tier: {user.tier}")
            print(f"   - enable_good_odds: {user.enable_good_odds}")
            print(f"   - enable_middle: {user.enable_middle}")
            print(f"   - min_ev_percent: {user.min_ev_percent}")
            print(f"   - notifications_enabled: {user.notifications_enabled}")
            print()
            
            # Check if would send
            if not user.enable_good_odds:
                print("⚠️ PROBLÈME: enable_good_odds = False!")
                print("   → Les alertes Good Odds sont désactivées!")
            elif ev_percent < (user.min_ev_percent or 12.0):
                print(f"⚠️ PROBLÈME: EV {ev_percent}% < minimum {user.min_ev_percent}%")
                print("   → Cette alerte serait filtrée!")
            else:
                print("✅ Settings OK - L'alerte devrait passer!")
        else:
            print("❌ User non trouvé!")
    finally:
        db.close()
    
    print()
    print("=" * 60)
    print("✅ Test terminé!")
    print("=" * 60)
    
    # Test with second sample
    print("\n" + "=" * 60)
    print("🎯 TEST 2: Alerte 3.5% EV")
    print("=" * 60)
    
    parsed2 = parse_positive_ev_notification(SAMPLE_POSITIVE_EV_2)
    if parsed2:
        print(f"✅ Parsed: {parsed2['ev_percent']}% EV")
        odds_int2 = int(parsed2['odds'].replace('-', '').replace('+', ''))
        if parsed2['odds'].startswith('-'):
            odds_int2 = -odds_int2
        quality2 = get_ev_quality_tag(parsed2['ev_percent'], odds_int2)
        print(f"✅ Tag: {quality2['tag']}")
        
        # Check if would be filtered
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == 8213628656).first()
            if user:
                min_ev = user.min_ev_percent or 12.0
                if parsed2['ev_percent'] < min_ev:
                    print(f"⚠️ EV {parsed2['ev_percent']}% < minimum {min_ev}%")
                    print("   → Alerte FILTRÉE par tes settings!")
                else:
                    print("✅ Passerait le filtre!")
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(test_good_odds())
