"""
Add min_ev_percent column to users table
Migration script
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment (.env) so DATABASE_URL is set (sqlite in this project)
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import inspect
from database import engine

def upgrade():
    """Add min_ev_percent column for Good Odds filtering"""
    print("Adding min_ev_percent column...")
    
    try:
        inspector = inspect(engine)
        existing_cols = {col['name'] for col in inspector.get_columns('users')}
        
        with engine.begin() as conn:
            if 'min_ev_percent' not in existing_cols:
                # SQLite-friendly, default 12.0 for beginners
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN min_ev_percent REAL DEFAULT 12.0")
                print("✅ min_ev_percent column added successfully!")
            else:
                print("✅ min_ev_percent column already exists!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

def downgrade():
    """Remove min_ev_percent column"""
    print("Removing min_ev_percent column...")
    
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE users DROP COLUMN IF EXISTS min_ev_percent")
            print("✅ min_ev_percent column removed successfully!")
            
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        raise

if __name__ == "__main__":
    print("Running migration: add_min_ev_percent")
    upgrade()
    print("Migration complete!")
