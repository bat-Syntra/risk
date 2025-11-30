"""
Run migration to add middle_bets table
"""
import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'arbitrage.db')

def run_migration():
    """Execute migration SQL"""
    
    # Read migration file
    migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'add_middle_bets_table.sql')
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Execute migration
        cursor.executescript(sql)
        conn.commit()
        print("✅ Migration successful: middle_bets table created")
        
        # Verify
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='middle_bets'")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Table 'middle_bets' verified in database")
            
            # Show columns
            cursor.execute("PRAGMA table_info(middle_bets)")
            columns = cursor.fetchall()
            print("\n📊 Columns in middle_bets table:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print("❌ Table 'middle_bets' not found after migration")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 Running middle_bets migration...\n")
    run_migration()
