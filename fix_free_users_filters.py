"""
Fix filters for existing FREE users
Set correct limits: arb 0.5-2.5%, middle/good_ev = 0
"""
from database import SessionLocal
from models.user import User, TierLevel

def fix_free_user_filters():
    """Fix filters for all FREE users"""
    db = SessionLocal()
    try:
        free_users = db.query(User).filter(User.tier == TierLevel.FREE).all()
        
        fixed_count = 0
        for user in free_users:
            changed = False
            
            # Fix arbitrage max (should be 2.5% for FREE)
            if user.max_arb_percent > 2.5:
                user.max_arb_percent = 2.5
                changed = True
            
            # Fix middle filters (should be 0 for FREE)
            if user.min_middle_percent != 0 or user.max_middle_percent != 0:
                user.min_middle_percent = 0
                user.max_middle_percent = 0
                changed = True
            
            # Fix good EV filters (should be 0 for FREE)
            if user.min_good_ev_percent != 0 or user.max_good_ev_percent != 0:
                user.min_good_ev_percent = 0
                user.max_good_ev_percent = 0
                changed = True
            
            # Reset rounding to 0 (precise) for FREE
            if user.stake_rounding != 0:
                user.stake_rounding = 0
                changed = True
            
            if changed:
                fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"✅ Fixed filters for {fixed_count} FREE users")
        else:
            print("✅ All FREE users already have correct filters")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_free_user_filters()
