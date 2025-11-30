"""
Migration script to add bet type tracking
Adds bet_type column to user_bets and type-specific stats to users table
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import SessionLocal, engine

def migrate():
    """Run migration to add bet type columns"""
    db = SessionLocal()
    try:
        print("🔄 Starting migration: add_bet_types...")
        
        # Add bet_type to user_bets if not exists
        try:
            db.execute(text("""
                ALTER TABLE user_bets 
                ADD COLUMN bet_type VARCHAR(20) DEFAULT 'arbitrage'
            """))
            print("✅ Added bet_type column to user_bets")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️  bet_type column already exists in user_bets")
            else:
                raise
        
        # Add type-specific stats to users if not exists
        stats_columns = [
            ("arbitrage_bets", "INTEGER DEFAULT 0"),
            ("arbitrage_profit", "FLOAT DEFAULT 0.0"),
            ("arbitrage_loss", "FLOAT DEFAULT 0.0"),
            ("good_ev_bets", "INTEGER DEFAULT 0"),
            ("good_ev_profit", "FLOAT DEFAULT 0.0"),
            ("good_ev_loss", "FLOAT DEFAULT 0.0"),
            ("middle_bets", "INTEGER DEFAULT 0"),
            ("middle_profit", "FLOAT DEFAULT 0.0"),
            ("middle_loss", "FLOAT DEFAULT 0.0"),
        ]
        
        for col_name, col_def in stats_columns:
            try:
                db.execute(text(f"""
                    ALTER TABLE users 
                    ADD COLUMN {col_name} {col_def}
                """))
                print(f"✅ Added {col_name} column to users")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"⚠️  {col_name} column already exists in users")
                else:
                    raise
        
        db.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
