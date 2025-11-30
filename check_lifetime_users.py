"""
Check LIFETIME users and their alert settings
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User, TierLevel

def check_lifetime_users():
    """Check all LIFETIME users and their settings"""
    db = SessionLocal()
    try:
        # Find all LIFETIME users (PREMIUM with no subscription_end)
        lifetime_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.subscription_end == None
        ).all()
        
        print(f"Found {len(lifetime_users)} LIFETIME users:\n")
        
        for user in lifetime_users:
            print(f"User: {user.telegram_id} (@{user.username})")
            print(f"  Tier: {user.tier.value}")
            print(f"  Subscription End: {user.subscription_end}")
            print(f"  Notifications: {user.notifications_enabled}")
            print(f"  Good Odds: {user.enable_good_odds}")
            print(f"  Middle: {user.enable_middle}")
            print(f"  Min Arb %: {user.min_arb_percent}")
            print(f"  Max Arb %: {user.max_arb_percent}")
            print(f"  Min Good EV %: {user.min_good_ev_percent}")
            print(f"  Max Good EV %: {user.max_good_ev_percent}")
            print(f"  Min Middle %: {user.min_middle_percent}")
            print(f"  Max Middle %: {user.max_middle_percent}")
            print(f"  Is Banned: {user.is_banned}")
            print()
        
        # Check regular PREMIUM users for comparison
        premium_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.subscription_end != None
        ).all()
        
        print(f"\nFound {len(premium_users)} regular PREMIUM users:")
        for user in premium_users:
            print(f"  {user.telegram_id} (@{user.username}): Good Odds={user.enable_good_odds}, Middle={user.enable_middle}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_lifetime_users()
