"""
Migration: Add bet_type column to drop_events table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

def upgrade():
    """Add bet_type column"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(drop_events)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'bet_type' not in columns:
            # Add column (SQLite doesn't support IF NOT EXISTS in ALTER)
            conn.execute(text("""
                ALTER TABLE drop_events 
                ADD COLUMN bet_type VARCHAR(20);
            """))
            print("✅ Column bet_type added")
        else:
            print("✓ Column bet_type already exists")
        
        # Set default value for existing rows (assume arbitrage)
        conn.execute(text("""
            UPDATE drop_events 
            SET bet_type = 'arbitrage' 
            WHERE bet_type IS NULL;
        """))
        print("✅ Default values set")
        
        # Create index
        try:
            conn.execute(text("""
                CREATE INDEX ix_drop_events_bet_type 
                ON drop_events(bet_type);
            """))
            print("✅ Index created")
        except:
            print("✓ Index already exists")
        
        conn.commit()
        print("✅ Migration completed: Added bet_type to drop_events")

def downgrade():
    """Remove bet_type column"""
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_drop_events_bet_type;"))
        conn.execute(text("ALTER TABLE drop_events DROP COLUMN IF EXISTS bet_type;"))
        conn.commit()
        print("✅ Rollback completed: Removed bet_type from drop_events")

if __name__ == "__main__":
    print("Running migration...")
    upgrade()
