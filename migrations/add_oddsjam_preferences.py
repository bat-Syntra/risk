"""
Add enable_good_odds and enable_middle columns to users table
Migration script
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment (.env) so DATABASE_URL is set (sqlite in this project)
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import Column, Boolean, inspect
from database import engine, Base
from models.user import User

def upgrade():
    """Add new columns for OddsJam preferences"""
    print("Adding OddsJam preference columns...")
    
    try:
        inspector = inspect(engine)
        existing_cols = {col['name'] for col in inspector.get_columns('users')}
        
        with engine.begin() as conn:
            if 'enable_good_odds' not in existing_cols:
                # SQLite-friendly, no IF NOT EXISTS needed since we check above
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN enable_good_odds BOOLEAN DEFAULT 0")
            if 'enable_middle' not in existing_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN enable_middle BOOLEAN DEFAULT 0")
        
        print("✅ OddsJam preference columns added successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

def downgrade():
    """Remove OddsJam preference columns"""
    print("Removing OddsJam preference columns...")
    
    try:
        with engine.begin() as conn:
            conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS enable_good_odds")
            conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS enable_middle")
            print("✅ OddsJam preference columns removed successfully!")
            
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        raise

if __name__ == "__main__":
    print("Running migration: add_oddsjam_preferences")
    upgrade()
    print("Migration complete!")
