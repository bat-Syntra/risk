"""
Migration for Book Health Monitoring System
Track user behavior to predict casino limits
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# Revision identifiers
revision = 'book_health_system'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # 1. User casino profiles
    op.create_table('user_casino_profiles',
        sa.Column('profile_id', sa.String(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('casino', sa.String(50), nullable=False),
        
        # Initial questionnaire data
        sa.Column('account_age_months', sa.Integer()),
        sa.Column('estimated_total_bets', sa.Integer()),
        sa.Column('was_active_before', sa.Boolean()),
        sa.Column('total_deposited', sa.Numeric(10, 2)),
        
        # Activity types
        sa.Column('does_sports_betting', sa.Boolean(), default=True),
        sa.Column('does_casino_games', sa.Boolean(), default=False),
        sa.Column('does_poker', sa.Boolean(), default=False),
        sa.Column('does_live_betting', sa.Boolean(), default=False),
        
        # Current status
        sa.Column('is_limited', sa.Boolean(), default=False),
        sa.Column('limited_at', sa.DateTime()),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        
        sa.UniqueConstraint('user_id', 'casino')
    )
    
    # 2. Bet analytics for detailed tracking
    op.create_table('bet_analytics',
        sa.Column('analytics_id', sa.String(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('bet_id', sa.String()),  # Reference to existing bets
        sa.Column('casino', sa.String(50), nullable=False),
        
        # Bet context
        sa.Column('bet_source_type', sa.String(20), nullable=False),  # 'plus_ev', 'arbitrage', 'middle', 'recreational'
        sa.Column('sport', sa.String(30)),
        sa.Column('market_type', sa.String(50)),  # 'ml', 'spread', 'total', 'player_prop'
        
        # Timing analysis
        sa.Column('line_posted_at', sa.DateTime()),
        sa.Column('bet_placed_at', sa.DateTime(), nullable=False),
        sa.Column('seconds_after_post', sa.Integer()),
        
        # Stake analysis
        sa.Column('stake_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('stake_rounded', sa.Boolean()),
        
        # Odds & CLV
        sa.Column('odds_at_bet', sa.Numeric(10, 4), nullable=False),
        sa.Column('closing_odds', sa.Numeric(10, 4)),
        sa.Column('clv', sa.Numeric(10, 6)),  # Closing Line Value
        
        # Results
        sa.Column('result', sa.String(20)),  # 'won', 'lost', 'push', 'void'
        sa.Column('profit_loss', sa.Numeric(10, 2)),
        
        # Context
        sa.Column('bankroll_at_time', sa.Numeric(10, 2)),
        
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # Create indexes
    op.create_index('idx_bet_analytics_user', 'bet_analytics', ['user_id'])
    op.create_index('idx_bet_analytics_casino', 'bet_analytics', ['casino'])
    op.create_index('idx_bet_analytics_user_casino', 'bet_analytics', ['user_id', 'casino'])
    
    # 3. Book health scores (computed daily)
    op.create_table('book_health_scores',
        sa.Column('score_id', sa.String(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('casino', sa.String(50), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        
        # Individual factor scores (0-100 scale)
        sa.Column('win_rate_score', sa.Numeric(5, 2)),
        sa.Column('clv_score', sa.Numeric(5, 2)),
        sa.Column('diversity_score', sa.Numeric(5, 2)),
        sa.Column('timing_score', sa.Numeric(5, 2)),
        sa.Column('stake_pattern_score', sa.Numeric(5, 2)),
        sa.Column('withdrawal_score', sa.Numeric(5, 2)),
        sa.Column('bet_type_score', sa.Numeric(5, 2)),
        sa.Column('activity_change_score', sa.Numeric(5, 2)),
        
        # Total score
        sa.Column('total_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),  # 'SAFE', 'MONITOR', 'WARNING', 'HIGH_RISK', 'CRITICAL'
        
        # Metrics snapshot
        sa.Column('total_bets', sa.Integer()),
        sa.Column('win_rate', sa.Numeric(5, 4)),
        sa.Column('avg_clv', sa.Numeric(10, 6)),
        sa.Column('sports_count', sa.Integer()),
        sa.Column('avg_delay_seconds', sa.Integer()),
        
        # Trend
        sa.Column('score_change_7d', sa.Numeric(5, 2)),
        sa.Column('score_change_30d', sa.Numeric(5, 2)),
        
        # Predictions
        sa.Column('estimated_months_until_limit', sa.Numeric(5, 1)),
        sa.Column('limit_probability', sa.Numeric(5, 4)),
        
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        
        sa.UniqueConstraint('user_id', 'casino', 'calculation_date')
    )
    
    # 4. Recommendations tracking
    op.create_table('health_recommendations',
        sa.Column('recommendation_id', sa.String(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('casino', sa.String(50), nullable=False),
        sa.Column('score_id', sa.String()),
        
        sa.Column('recommendation_type', sa.String(50), nullable=False),
        sa.Column('recommendation_text', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        
        sa.Column('acknowledged', sa.Boolean(), default=False),
        sa.Column('acknowledged_at', sa.DateTime()),
        
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # 5. Limit events (when users actually get limited)
    op.create_table('limit_events',
        sa.Column('event_id', sa.String(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('casino', sa.String(50), nullable=False),
        
        sa.Column('limit_type', sa.String(30), nullable=False),  # 'stake_reduced', 'banned', 'verification_requested'
        sa.Column('previous_max_stake', sa.Numeric(10, 2)),
        sa.Column('new_max_stake', sa.Numeric(10, 2)),
        
        sa.Column('score_at_limit', sa.Numeric(5, 2)),
        
        sa.Column('reported_at', sa.DateTime(), default=datetime.utcnow),
        
        # ML training data
        sa.Column('metrics_at_limit', sa.JSON())
    )
    
    op.create_index('idx_limit_events_casino', 'limit_events', ['casino'])
    
    # 6. Book health state (for FSM questionnaire)
    op.create_table('book_health_state',
        sa.Column('user_id', sa.String(100), primary_key=True),
        sa.Column('current_step', sa.String(50)),
        sa.Column('current_casino', sa.String(50)),
        sa.Column('selected_casinos', sa.JSON()),
        sa.Column('temp_data', sa.JSON()),
        sa.Column('activity_types', sa.JSON()),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # 7. Recreational bet tags
    op.create_table('recreational_bets',
        sa.Column('bet_id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('tagged_at', sa.DateTime(), default=datetime.utcnow)
    )


def downgrade():
    op.drop_table('recreational_bets')
    op.drop_table('book_health_state')
    op.drop_index('idx_limit_events_casino', 'limit_events')
    op.drop_table('limit_events')
    op.drop_table('health_recommendations')
    op.drop_table('book_health_scores')
    op.drop_index('idx_bet_analytics_user_casino', 'bet_analytics')
    op.drop_index('idx_bet_analytics_casino', 'bet_analytics')
    op.drop_index('idx_bet_analytics_user', 'bet_analytics')
    op.drop_table('bet_analytics')
    op.drop_table('user_casino_profiles')
