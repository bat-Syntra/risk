"""
Migration: Add free_access column to users table
Distinguishes free premium access (gifts) from paid premium access
"""

from database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Add free_access column to users table"""
    db = SessionLocal()
    
    try:
        # Add free_access column (default False = paid access)
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS free_access BOOLEAN DEFAULT FALSE
        """))
        
        # Create index on free_access
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_free_access ON users(free_access)
        """))
        
        db.commit()
        print("✅ Migration complete: Added free_access column to users table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
