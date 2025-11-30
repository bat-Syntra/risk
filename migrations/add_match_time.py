"""
Add match_time column to drop_events table
"""
import sqlite3
import os

def run_migration():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'arbitrage_bot.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(drop_events)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'match_time' not in columns:
        print("Adding match_time column to drop_events...")
        cursor.execute("ALTER TABLE drop_events ADD COLUMN match_time DATETIME")
        conn.commit()
        print("✅ match_time column added!")
    else:
        print("✅ match_time column already exists")
    
    # Create index on match_time for faster queries
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_drop_events_match_time ON drop_events (match_time)")
        conn.commit()
        print("✅ Index created on match_time")
    except Exception as e:
        print(f"Index already exists or error: {e}")
    
    conn.close()

if __name__ == "__main__":
    run_migration()
