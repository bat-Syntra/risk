"""
Add arbitrage_calls table for ML/LLM data collection
OPTIMIZED: Lightweight, indexed, non-blocking
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_arbitrage_calls'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create lightweight table for ML data
    op.execute("""
        CREATE TABLE IF NOT EXISTS arbitrage_calls (
            call_id TEXT PRIMARY KEY,
            call_type TEXT NOT NULL,
            
            -- Match (compact)
            sport TEXT,
            team_a TEXT,
            team_b TEXT,
            match_date TIMESTAMP,
            
            -- Bookmakers
            book_a TEXT NOT NULL,
            book_b TEXT NOT NULL,
            market TEXT,
            
            -- Odds (compact - only essentials)
            odds_a REAL NOT NULL,
            odds_b REAL NOT NULL,
            roi_percent REAL NOT NULL,
            
            -- Stakes
            stake_a REAL,
            stake_b REAL,
            profit_expected REAL,
            
            -- Tracking (lightweight)
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            users_notified INTEGER DEFAULT 0,
            users_clicked INTEGER DEFAULT 0,
            
            -- Result (filled later - nullable)
            outcome TEXT,
            profit_actual REAL,
            
            -- ML features (compact)
            clv_a REAL,
            clv_b REAL
        );
        
        -- CRITICAL: Indexes for fast queries (no performance impact)
        CREATE INDEX IF NOT EXISTS idx_calls_type ON arbitrage_calls(call_type);
        CREATE INDEX IF NOT EXISTS idx_calls_sport ON arbitrage_calls(sport);
        CREATE INDEX IF NOT EXISTS idx_calls_sent_at ON arbitrage_calls(sent_at);
        CREATE INDEX IF NOT EXISTS idx_calls_roi ON arbitrage_calls(roi_percent);
        
        -- Composite index for ML queries
        CREATE INDEX IF NOT EXISTS idx_calls_ml ON arbitrage_calls(call_type, sport, sent_at);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS arbitrage_calls;")
