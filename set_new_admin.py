#!/usr/bin/env python3
"""
Set new super admin in database
"""
from database import SessionLocal
from models.user import User, TierLevel
from sqlalchemy import text

NEW_ADMIN_ID = 8004919557

def set_new_admin():
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.telegram_id == NEW_ADMIN_ID).first()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=NEW_ADMIN_ID,
                username="new_admin",
                role="super_admin",
                tier=TierLevel.PREMIUM,
                free_access=True,
                is_active=True
            )
            db.add(user)
            print(f"✅ Created new super_admin user: {NEW_ADMIN_ID}")
        else:
            # Update existing user
            user.role = "super_admin"
            user.tier = TierLevel.PREMIUM
            user.free_access = True
            print(f"✅ Updated user {NEW_ADMIN_ID} to super_admin")
        
        db.commit()
        
        # Verify
        user = db.query(User).filter(User.telegram_id == NEW_ADMIN_ID).first()
        print(f"📊 User details:")
        print(f"   - Telegram ID: {user.telegram_id}")
        print(f"   - Role: {user.role}")
        print(f"   - Tier: {user.tier}")
        print(f"   - Free Access: {user.free_access}")
        
    finally:
        db.close()

if __name__ == "__main__":
    set_new_admin()
