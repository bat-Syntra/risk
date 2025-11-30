"""
Migration script to add admin role system
"""
import sqlite3
from datetime import datetime

DB_PATH = "arbitrage_bot.db"

def run_migration():
    """Add role column to users and create admin_actions table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Add 'role' column to users table (default 'user')
        print("Adding 'role' column to users table...")
        try:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN role TEXT DEFAULT 'user'
            """)
            print("✅ 'role' column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  'role' column already exists")
            else:
                raise
        
        # 2. Create admin_actions table
        print("\nCreating admin_actions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                notes TEXT
            )
        """)
        print("✅ admin_actions table created")
        
        # 3. Create index for better performance
        print("\nCreating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_admin_actions_status 
            ON admin_actions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id 
            ON admin_actions(admin_id)
        """)
        print("✅ Indexes created")
        
        # 4. Set super admin role for owner
        print("\nSetting super_admin role for owner (8213628656)...")
        cursor.execute("""
            UPDATE users 
            SET role = 'super_admin'
            WHERE telegram_id = 8213628656
        """)
        print("✅ Super admin role set")
        
        conn.commit()
        print("\n" + "="*50)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*50)
        
        # Show current roles
        print("\n📊 Current user roles:")
        cursor.execute("""
            SELECT telegram_id, username, role 
            FROM users 
            WHERE role IN ('super_admin', 'admin')
        """)
        for row in cursor.fetchall():
            print(f"  • {row[1] or 'N/A'} ({row[0]}): {row[2]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting admin role migration...\n")
    run_migration()
