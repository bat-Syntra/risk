"""
Migration script to add bet_focus_mode column to users table
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from sqlalchemy import text

def add_bet_focus_mode():
    """Add bet_focus_mode column to users table"""
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result]
        
        if 'bet_focus_mode' not in columns:
            print("Adding bet_focus_mode column...")
            db.execute(text("ALTER TABLE users ADD COLUMN bet_focus_mode BOOLEAN DEFAULT 0"))
            db.commit()
            print("✅ bet_focus_mode column added successfully!")
        else:
            print("⚠️ bet_focus_mode column already exists")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Adding bet_focus_mode column to users table...")
    add_bet_focus_mode()
    print("✅ Migration complete!")
