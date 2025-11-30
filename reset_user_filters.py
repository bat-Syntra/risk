"""
Reset percentage filters for a specific user to default values
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User

def reset_filters(telegram_id):
    """Reset filters for a specific user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            print(f"❌ User {telegram_id} not found!")
            return
        
        print(f"Found user: {user.username} ({user.telegram_id})")
        print(f"Current filters:")
        print(f"  Arb: {user.min_arb_percent}% - {user.max_arb_percent}%")
        print(f"  Good EV: {user.min_good_ev_percent}% - {user.max_good_ev_percent}%")
        print(f"  Middle: {user.min_middle_percent}% - {user.max_middle_percent}%")
        
        # Reset to defaults
        user.min_arb_percent = 0.5
        user.max_arb_percent = 100.0
        user.min_good_ev_percent = 0.5
        user.max_good_ev_percent = 100.0
        user.min_middle_percent = 0.5
        user.max_middle_percent = 100.0
        
        db.commit()
        
        print(f"\n✅ Filters reset to defaults:")
        print(f"  Arb: 0.5% - 100%")
        print(f"  Good EV: 0.5% - 100%")
        print(f"  Middle: 0.5% - 100%")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Reset for ZEROR1SK
    reset_filters(8213628656)
