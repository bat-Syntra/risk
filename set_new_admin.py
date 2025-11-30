#!/usr/bin/env python3
"""
Set new super admin in database - using raw SQL
"""
from database import SessionLocal
from sqlalchemy import text

NEW_ADMIN_ID = 8004919557

def set_new_admin():
    db = SessionLocal()
    try:
        # Check if user exists
        result = db.execute(text("SELECT telegram_id, role FROM users WHERE telegram_id = :tid"), {"tid": NEW_ADMIN_ID}).fetchone()
        
        if not result:
            # Create new user
            db.execute(text("""
                INSERT INTO users (telegram_id, username, role, tier, free_access, is_active)
                VALUES (:tid, 'new_admin', 'super_admin', 'PREMIUM', 1, 1)
            """), {"tid": NEW_ADMIN_ID})
            print(f"✅ Created new super_admin user: {NEW_ADMIN_ID}")
        else:
            # Update existing user
            db.execute(text("""
                UPDATE users 
                SET role = 'super_admin', tier = 'PREMIUM', free_access = 1
                WHERE telegram_id = :tid
            """), {"tid": NEW_ADMIN_ID})
            print(f"✅ Updated user {NEW_ADMIN_ID} to super_admin")
        
        db.commit()
        
        # Verify
        user = db.execute(text("SELECT telegram_id, role, tier, free_access FROM users WHERE telegram_id = :tid"), {"tid": NEW_ADMIN_ID}).fetchone()
        print(f"📊 User details:")
        print(f"   - Telegram ID: {user[0]}")
        print(f"   - Role: {user[1]}")
        print(f"   - Tier: {user[2]}")
        print(f"   - Free Access: {user[3]}")
        
    finally:
        db.close()

if __name__ == "__main__":
    set_new_admin()
