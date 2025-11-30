"""
Add percentage filters for arbitrage, middle, and good EV alerts
Run with: python3 migrations/add_percent_filters.py
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
    """Add percentage filter columns to users table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Add columns for arbitrage filters
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN min_arb_percent FLOAT DEFAULT 0.5"
            ))
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN max_arb_percent FLOAT DEFAULT 100.0"
            ))
            logger.info("✅ Added arbitrage percent filters")
        except Exception as e:
            logger.warning(f"Arbitrage filters might already exist: {e}")
        
        # Add columns for middle filters
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN min_middle_percent FLOAT DEFAULT 0.5"
            ))
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN max_middle_percent FLOAT DEFAULT 100.0"
            ))
            logger.info("✅ Added middle percent filters")
        except Exception as e:
            logger.warning(f"Middle filters might already exist: {e}")
        
        # Add columns for good EV filters
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN min_good_ev_percent FLOAT DEFAULT 0.5"
            ))
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN max_good_ev_percent FLOAT DEFAULT 100.0"
            ))
            logger.info("✅ Added good EV percent filters")
        except Exception as e:
            logger.warning(f"Good EV filters might already exist: {e}")
        
        conn.commit()
    
    logger.info("🎉 Migration complete!")

if __name__ == "__main__":
    migrate()
