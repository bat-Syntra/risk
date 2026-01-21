#!/usr/bin/env python3
"""
Migration script to create website_users table in SQLite database
Run this to fix: no such table: website_users
"""

import sqlite3
import os
from datetime import datetime

def create_website_users_table():
    """Create the website_users table in the SQLite database"""
    
    # Path to the database file
    db_path = "arbitrage_bot.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Make sure you're running this script from the bot directory")
        return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='website_users'
        """)
        
        if cursor.fetchone():
            print("✅ Table 'website_users' already exists")
            conn.close()
            return True
        
        # Create the website_users table
        cursor.execute("""
            CREATE TABLE website_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX idx_website_users_telegram_id ON website_users(telegram_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_website_users_email ON website_users(email)
        """)
        
        # Create trigger to auto-update updated_at column
        cursor.execute("""
            CREATE TRIGGER update_website_users_updated_at 
            AFTER UPDATE ON website_users
            FOR EACH ROW
            BEGIN
                UPDATE website_users 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        # Commit changes
        conn.commit()
        
        print("✅ Successfully created 'website_users' table")
        print("✅ Created indexes on telegram_id and email")
        print("✅ Created auto-update trigger for updated_at")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(website_users)")
        columns = cursor.fetchall()
        
        print("\n📋 Table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else 'NULL'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creating website_users table...")
    success = create_website_users_table()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("💡 You can now restart your bot to use the admin password features")
    else:
        print("\n❌ Migration failed!")
        print("💡 Check the error above and try again")
