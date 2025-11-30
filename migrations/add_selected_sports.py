"""
Migration: Add selected_sports column to users table
Date: 2025-11-29
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add selected_sports column"""
    # Add selected_sports column (JSON list of sports, null = all sports)
    op.add_column('users', sa.Column('selected_sports', sa.String(), nullable=True))
    print("✅ Migration complete: added selected_sports column")


def downgrade():
    """Remove selected_sports column"""
    op.drop_column('users', 'selected_sports')
    print("✅ Rollback complete: removed selected_sports column")


if __name__ == "__main__":
    # For manual execution without Alembic
    from sqlalchemy import create_engine, text
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///arbitrage_bot.db")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'selected_sports' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN selected_sports TEXT"))
                conn.commit()
                print("✅ Migration executed: selected_sports column added!")
            else:
                print("ℹ️ Column selected_sports already exists, skipping migration")
    except Exception as e:
        print(f"❌ Migration error: {e}")
