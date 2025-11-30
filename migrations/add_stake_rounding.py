"""
Add stake_rounding field to users table
Run with: python3 migrations/add_stake_rounding.py
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
    """Add stake_rounding column to users table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]
            
            if 'stake_rounding' not in columns:
                # Add stake_rounding column (0=precise, 1=dollar, 5=five, 10=ten)
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN stake_rounding INTEGER DEFAULT 0
                """))
                conn.commit()
                logger.info("✅ Added stake_rounding field")
            else:
                logger.info("ℹ️ stake_rounding column already exists, skipping")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            conn.rollback()
            raise
    
    logger.info("🎉 Migration complete!")

if __name__ == "__main__":
    migrate()
