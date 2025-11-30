"""
Fix existing LIFETIME users to have Good Odds and Middle enabled
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User, TierLevel

def fix_lifetime_alerts():
    """Enable Good Odds and Middle for all LIFETIME Premium users"""
    db = SessionLocal()
    try:
        # Find all LIFETIME users (PREMIUM with no subscription_end)
        lifetime_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.subscription_end == None
        ).all()
        
        fixed_count = 0
        for user in lifetime_users:
            changed = False
            if not user.enable_good_odds:
                user.enable_good_odds = True
                changed = True
                print(f"✅ User {user.telegram_id} (@{user.username}): Enabled Good Odds")
            
            if not user.enable_middle:
                user.enable_middle = True
                changed = True
                print(f"✅ User {user.telegram_id} (@{user.username}): Enabled Middle")
            
            if changed:
                fixed_count += 1
        
        # Also fix regular PREMIUM users who might have these disabled
        premium_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.subscription_end != None
        ).all()
        
        for user in premium_users:
            changed = False
            if not user.enable_good_odds:
                user.enable_good_odds = True
                changed = True
                print(f"✅ Premium User {user.telegram_id} (@{user.username}): Enabled Good Odds")
            
            if not user.enable_middle:
                user.enable_middle = True
                changed = True
                print(f"✅ Premium User {user.telegram_id} (@{user.username}): Enabled Middle")
            
            if changed:
                fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"\n🎯 Fixed {fixed_count} Premium/Lifetime users!")
        else:
            print("\n✅ All Premium/Lifetime users already have Good Odds and Middle enabled!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Fixing Good Odds and Middle alerts for LIFETIME users...")
    fix_lifetime_alerts()
