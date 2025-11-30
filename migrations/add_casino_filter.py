"""
Add selected_casinos field to users table
Run with: python3 migrations/add_casino_filter.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Add selected_casinos column to users table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]
            
            if 'selected_casinos' not in columns:
                # Add selected_casinos column (JSON string, null = all casinos)
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN selected_casinos TEXT
                """))
                conn.commit()
                logger.info("✅ Added selected_casinos field")
            else:
                logger.info("ℹ️ selected_casinos column already exists, skipping")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            conn.rollback()
            raise
    
    logger.info("🎉 Migration complete!")

if __name__ == "__main__":
    migrate()
