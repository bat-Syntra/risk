"""Debug why user is not receiving Good Odds and Middle alerts"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, TierLevel

def check_user_alert_eligibility(user_id: int = 8213628656):
    """Check why a user is not receiving alerts"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            print(f"❌ User {user_id} not found in database")
            return
            
        print(f"\n=== USER ALERT ELIGIBILITY CHECK ===")
        print(f"User ID: {user.telegram_id}")
        print(f"Name: {user.first_name} {user.last_name or ''}")
        print(f"Tier: {user.tier}")
        print(f"Language: {user.language}")
        
        # Check subscription
        print(f"\n=== SUBSCRIPTION STATUS ===")
        print(f"Subscription End: {user.subscription_end}")
        print(f"Subscription Active: {user.subscription_active}")
        print(f"Is Banned: {user.is_banned}")
        print(f"Notifications Enabled: {user.notifications_enabled}")
        
        # Check if user is premium
        try:
            is_premium = (user.tier != TierLevel.FREE)
            print(f"Is Premium (tier check): {is_premium}")
        except Exception as e:
            print(f"Error checking premium status: {e}")
            is_premium = False
        
        # Check Good Odds settings
        print(f"\n=== GOOD ODDS SETTINGS ===")
        print(f"Enable Good Odds: {user.enable_good_odds}")
        print(f"Min Good EV %: {user.min_good_ev_percent or 0.5}")
        print(f"Max Good EV %: {user.max_good_ev_percent or 100.0}")
        
        # Check Middle settings
        print(f"\n=== MIDDLE SETTINGS ===")
        print(f"Enable Middle: {user.enable_middle}")
        print(f"Min Middle %: {user.min_middle_percent or 0.5}")
        print(f"Max Middle %: {user.max_middle_percent or 100.0}")
        
        # Check other relevant settings
        print(f"\n=== OTHER SETTINGS ===")
        print(f"Default Bankroll: ${user.default_bankroll}")
        print(f"Stake Rounding: {user.stake_rounding}")
        
        # Check eligibility for Good Odds
        print(f"\n=== GOOD ODDS ELIGIBILITY CHECK ===")
        eligible_good_odds = (
            user.enable_good_odds == True and
            user.is_banned == False and
            user.notifications_enabled == True and
            is_premium
        )
        print(f"✅ Eligible for Good Odds: {eligible_good_odds}")
        if not eligible_good_odds:
            if not user.enable_good_odds:
                print("  ❌ Good Odds is disabled")
            if user.is_banned:
                print("  ❌ User is banned")
            if not user.notifications_enabled:
                print("  ❌ Notifications are disabled")
            if not is_premium:
                print("  ❌ User is not Premium")
        
        # Check eligibility for Middle
        print(f"\n=== MIDDLE ELIGIBILITY CHECK ===")
        eligible_middle = (
            user.enable_middle == True and
            user.is_banned == False and
            user.notifications_enabled == True and
            is_premium
        )
        print(f"✅ Eligible for Middle: {eligible_middle}")
        if not eligible_middle:
            if not user.enable_middle:
                print("  ❌ Middle is disabled")
            if user.is_banned:
                print("  ❌ User is banned")
            if not user.notifications_enabled:
                print("  ❌ Notifications are disabled")
            if not is_premium:
                print("  ❌ User is not Premium")
                
        # Test Good Odds with sample percentage
        print(f"\n=== SAMPLE ALERT TESTS ===")
        test_ev = 7.5
        print(f"Test Good Odds EV: {test_ev}%")
        passes_filter = user.min_good_ev_percent <= test_ev <= user.max_good_ev_percent
        print(f"  Passes filter: {passes_filter}")
        
        test_middle = 5.0
        print(f"Test Middle: {test_middle}%")
        passes_middle = user.min_middle_percent <= test_middle <= user.max_middle_percent
        print(f"  Passes filter: {passes_middle}")
        
    finally:
        db.close()

if __name__ == "__main__":
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8213628656
    check_user_alert_eligibility(user_id)
