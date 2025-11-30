"""
Add rounding_mode column to users table
"""
from sqlalchemy import create_engine, Column, String, MetaData, Table, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def upgrade():
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    users_table = metadata.tables.get('users')
    
    if users_table is not None:
        # Check if column already exists
        if 'rounding_mode' not in users_table.c:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN rounding_mode VARCHAR DEFAULT 'nearest'
                """))
                conn.commit()
                print("✅ Added rounding_mode column to users table")
        else:
            print("⚠️ rounding_mode column already exists")
    else:
        print("❌ users table not found")

if __name__ == "__main__":
    upgrade()
