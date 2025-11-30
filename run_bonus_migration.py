"""
Migration script to add bonus_tracking table to database
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bonus_migration():
    """Create bonus_tracking table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Create bonus_tracking table
        logger.info("Creating bonus_tracking table...")
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bonus_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT NOT NULL UNIQUE,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                bonus_eligible BOOLEAN DEFAULT 0,
                bonus_activated_at TIMESTAMP,
                bonus_expires_at TIMESTAMP,
                bonus_redeemed BOOLEAN DEFAULT 0,
                bonus_redeemed_at TIMESTAMP,
                campaign_messages_sent INTEGER DEFAULT 0,
                last_campaign_message_at TIMESTAMP,
                ever_had_bonus BOOLEAN DEFAULT 0,
                bonus_amount INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.commit()
        logger.info("✅ bonus_tracking table created successfully!")
        
        # Create index on telegram_id for faster lookups
        logger.info("Creating index on telegram_id...")
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bonus_telegram_id 
            ON bonus_tracking(telegram_id)
        """))
        connection.commit()
        logger.info("✅ Index created successfully!")
        
        logger.info("🎉 Bonus tracking migration completed!")

if __name__ == "__main__":
    run_bonus_migration()
