"""
Migration: Add match_today_only field to users table
This filter allows users to receive only alerts for matches starting TODAY
"""
from sqlalchemy import Boolean, Column
from database import SessionLocal, engine
from models.user import User
import logging

logger = logging.getLogger(__name__)

def run_migration():
    """Add match_today_only column to users table"""
    db = SessionLocal()
    try:
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'match_today_only' in columns:
            logger.info("✅ Column 'match_today_only' already exists")
            return
        
        # Add column using raw SQL
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN match_today_only BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
        
        logger.info("✅ Added 'match_today_only' column to users table")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
