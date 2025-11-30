"""
Migration: Add complete parlay correlation and risk profile system
"""
import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

def run_migration():
    """Add tables for parlay correlation, risk profiles, odds tracking"""
    
    with engine.connect() as conn:
        try:
            # 1. Risk profiles and user preferences
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    telegram_chat_id INTEGER,
                    
                    -- Casino preferences (stored as JSON)
                    preferred_casinos TEXT,
                    blocked_casinos TEXT,
                    
                    -- Risk preferences
                    risk_profiles TEXT, -- JSON: ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE', 'LOTTERY']
                    min_parlay_edge REAL DEFAULT 0.10,
                    max_parlay_legs INTEGER DEFAULT 3,
                    
                    -- Notification preferences
                    notification_mode TEXT DEFAULT 'push',
                    max_daily_notifications INTEGER DEFAULT 10,
                    notification_times TEXT,
                    
                    -- Sport preferences (stored as JSON)
                    preferred_sports TEXT,
                    blocked_sports TEXT,
                    
                    -- Other
                    timezone TEXT DEFAULT 'America/Montreal',
                    language TEXT DEFAULT 'fr',
                    bankroll REAL,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    CHECK (notification_mode IN ('push', 'pull'))
                )
            """))
            
            # 2. Correlation patterns table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS correlation_patterns (
                    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT UNIQUE NOT NULL,
                    sport TEXT NOT NULL,
                    scenario_type TEXT NOT NULL,
                    
                    -- Conditions for detection (stored as JSON string)
                    conditions TEXT NOT NULL,
                    
                    -- Correlated outcomes (stored as JSON string)
                    correlated_outcomes TEXT NOT NULL,
                    
                    -- Statistical measures
                    independent_probability REAL NOT NULL,
                    actual_probability REAL NOT NULL,
                    correlation_strength REAL NOT NULL,
                    
                    -- Historical backing
                    sample_size INTEGER NOT NULL,
                    confidence_level REAL NOT NULL,
                    last_tested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Performance tracking
                    times_sent INTEGER DEFAULT 0,
                    times_hit INTEGER DEFAULT 0,
                    times_missed INTEGER DEFAULT 0,
                    actual_hit_rate REAL,
                    
                    -- Filters
                    min_edge REAL DEFAULT 0.10,
                    is_active INTEGER DEFAULT 1,
                    
                    -- Metadata
                    description TEXT,
                    why_correlated TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 3. Odds history tracking
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS odds_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id INTEGER,
                    drop_event_id INTEGER,
                    
                    old_american_odds INTEGER,
                    new_american_odds INTEGER,
                    old_decimal_odds REAL,
                    new_decimal_odds REAL,
                    change_percent REAL,
                    
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    
                    FOREIGN KEY (drop_event_id) REFERENCES drop_events(id)
                )
            """))
            
            # 4. Historical games for correlation analysis
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS historical_games (
                    game_id TEXT PRIMARY KEY,
                    sport TEXT NOT NULL,
                    league TEXT NOT NULL,
                    date DATE NOT NULL,
                    season INTEGER,
                    
                    -- Teams
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    
                    -- Final score
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    
                    -- Betting lines
                    spread_line REAL,
                    spread_result TEXT,
                    
                    total_line REAL,
                    total_result TEXT,
                    total_actual REAL,
                    
                    home_ml_odds INTEGER,
                    away_ml_odds INTEGER,
                    ml_result TEXT,
                    
                    -- Team totals
                    home_team_total REAL,
                    away_team_total REAL,
                    
                    -- Key player stats (JSON)
                    player_stats TEXT,
                    
                    -- Game context
                    game_situation TEXT,
                    margin_of_victory INTEGER,
                    lead_changes INTEGER,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 5. Parlay tracking with risk profiles
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS parlays (
                    parlay_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Legs (stored as JSON)
                    leg_bet_ids TEXT,
                    leg_count INTEGER,
                    bookmakers TEXT,
                    
                    -- Odds
                    combined_american_odds INTEGER,
                    combined_decimal_odds REAL,
                    
                    -- Analysis
                    calculated_edge REAL,
                    quality_score INTEGER,
                    
                    -- Risk profile
                    risk_profile TEXT,
                    risk_label TEXT,
                    stake_guidance TEXT,
                    
                    -- Correlation (if applicable)
                    parlay_type TEXT DEFAULT 'regular',
                    pattern_id INTEGER,
                    correlation_strength REAL,
                    correlation_bonus REAL,
                    
                    -- Tracking
                    status TEXT DEFAULT 'pending',
                    sent_to_users INTEGER DEFAULT 0,
                    users_took_count INTEGER DEFAULT 0,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    
                    FOREIGN KEY (pattern_id) REFERENCES correlation_patterns(pattern_id)
                )
            """))
            
            # 6. Correlation alerts tracking
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS correlation_alerts (
                    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER,
                    
                    game_id TEXT,
                    alerted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Parlay details (stored as JSON)
                    parlay_legs TEXT,
                    parlay_odds REAL,
                    predicted_edge REAL,
                    
                    -- Result
                    result TEXT,
                    actual_roi REAL,
                    
                    users_took_it INTEGER DEFAULT 0,
                    
                    FOREIGN KEY (pattern_id) REFERENCES correlation_patterns(pattern_id)
                )
            """))
            
            # 7. Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_prefs_telegram ON user_preferences(telegram_chat_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_patterns_sport ON correlation_patterns(sport)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_patterns_active ON correlation_patterns(is_active)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_odds_history_bet ON odds_history(bet_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_odds_history_detected ON odds_history(detected_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_historical_sport ON historical_games(sport)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_historical_date ON historical_games(date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parlays_date ON parlays(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parlays_edge ON parlays(calculated_edge)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parlays_quality ON parlays(quality_score)"))
            
            logger.info("✅ Parlay system tables created successfully")
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error creating parlay system tables: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
    print("✅ Parlay system migration completed")
