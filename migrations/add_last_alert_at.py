"""
Migration: Add last_alert_at to users table for spacing checks
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import SessionLocal, engine


def upgrade():
    """Add last_alert_at column to users"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'last_alert_at' not in columns:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN last_alert_at DATETIME;
            """))
            print("✅ Column last_alert_at added to users table")
        else:
            print("✓ Column last_alert_at already exists")
        
        conn.commit()
        print("✅ Migration completed: Added last_alert_at for spacing checks")


def downgrade():
    """Remove last_alert_at column"""
    # SQLite doesn't support DROP COLUMN easily
    print("⚠️ Downgrade not supported for SQLite (would require table rebuild)")


if __name__ == "__main__":
    print("🔄 Running migration: add_last_alert_at")
    upgrade()
