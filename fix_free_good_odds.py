"""
Fix: Disable Good Odds and Middle for ALL FREE users
Run this once to fix existing FREE users
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from models.user import User, TierLevel

def fix_free_users():
    """Disable Good Odds and Middle for all FREE users"""
    db = SessionLocal()
    
    try:
        # Get all FREE users
        free_users = db.query(User).filter(User.tier == TierLevel.FREE).all()
        
        print(f"Found {len(free_users)} FREE users")
        
        updated = 0
        for user in free_users:
            changed = False
            
            # Disable Good Odds if enabled
            if user.enable_good_odds:
                user.enable_good_odds = False
                changed = True
                print(f"  - User {user.telegram_id}: Disabled Good Odds")
            
            # Disable Middle if enabled
            if user.enable_middle:
                user.enable_middle = False
                changed = True
                print(f"  - User {user.telegram_id}: Disabled Middle")
            
            if changed:
                updated += 1
        
        if updated > 0:
            db.commit()
            print(f"\n✅ Updated {updated}/{len(free_users)} FREE users")
            print("Good Odds and Middle are now DISABLED for all FREE users!")
        else:
            print(f"\n✓ All {len(free_users)} FREE users already have Good Odds and Middle disabled")
            print("No changes needed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Fixing FREE users - Disabling Good Odds and Middle...\n")
    fix_free_users()
