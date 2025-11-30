"""
Bet model for tracking user bet history
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Bet(Base):
    """
    Bet history - tracks all bets placed by users
    """
    __tablename__ = "bets"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_id = Column(Integer, ForeignKey('users.telegram_id'), index=True, nullable=False)
    
    # Event info
    event_id = Column(String(100), index=True)  # From source bot
    match_info = Column(Text)  # "Team A vs Team B"
    sport = Column(String(50), index=True)
    league = Column(String(100))
    market = Column(String(200))  # "Total Points", "Player Props", etc.
    player = Column(String(200))  # If player prop
    
    # Mode & bankroll
    mode = Column(String(10), index=True)  # 'safe' or 'risked'
    bankroll = Column(Float, nullable=False)
    
    # Stakes (JSON format for flexibility)
    # Example: {"Betsson": {"stake": 255.32, "odds": -200, "outcome": "Over 3"}}
    stakes = Column(JSON, nullable=False)
    
    # Outcomes detail (JSON)
    # Example: [{"casino": "Betsson", "outcome": "Over 3", "odds": -200}, ...]
    outcomes = Column(JSON)
    
    # Profit calculations
    arb_percentage = Column(Float)  # Arbitrage percentage
    expected_profit = Column(Float)  # Expected profit (SAFE mode)
    max_profit = Column(Float)  # Max profit (RISKED mode)
    risk_amount = Column(Float)  # Risk amount (RISKED mode)
    
    # Actual result (when bet is settled)
    actual_profit = Column(Float)  # NULL if not yet resolved
    winning_outcome = Column(String(200))  # Which outcome won
    is_settled = Column(Boolean, default=False, index=True)
    
    # Metadata
    source_alert_timestamp = Column(DateTime(timezone=True))  # When alert was received
    casinos_used = Column(JSON)  # List of casino names
    referral_links_used = Column(JSON)  # Which referral links were provided
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    settled_at = Column(DateTime(timezone=True))
    
    # Notes
    notes = Column(Text)  # User notes
    
    def __repr__(self):
        return f"<Bet(id={self.id}, user={self.user_id}, mode={self.mode}, profit={self.expected_profit})>"
    
    def settle(self, winning_outcome: str, actual_profit: float):
        """
        Mark bet as settled with actual result
        
        Args:
            winning_outcome: Which outcome won (e.g., "Over 3")
            actual_profit: Actual profit/loss
        """
        self.is_settled = True
        self.winning_outcome = winning_outcome
        self.actual_profit = actual_profit
        self.settled_at = datetime.now()
    
    @property
    def roi(self) -> float:
        """Return on investment percentage"""
        if not self.bankroll or self.bankroll == 0:
            return 0.0
        if self.actual_profit is not None:
            return (self.actual_profit / self.bankroll) * 100
        if self.expected_profit is not None:
            return (self.expected_profit / self.bankroll) * 100
        return 0.0
    
    @property
    def is_profitable(self) -> bool:
        """Check if bet was profitable"""
        if self.actual_profit is not None:
            return self.actual_profit > 0
        return False
    
    def to_dict(self):
        """Convert to dictionary for easy serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "match_info": self.match_info,
            "sport": self.sport,
            "league": self.league,
            "market": self.market,
            "mode": self.mode,
            "bankroll": self.bankroll,
            "stakes": self.stakes,
            "expected_profit": self.expected_profit,
            "actual_profit": self.actual_profit,
            "is_settled": self.is_settled,
            "roi": self.roi,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserBet(Base):
    """
    Simple bet tracking when user clicks 'I BET' button
    """
    __tablename__ = "user_bets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'), index=True, nullable=False)
    drop_event_id = Column(Integer, ForeignKey('drop_events.id'), index=True)  # Link to drop_events table
    event_hash = Column(String(100), index=True)  # Hash of the call for deduplication
    bet_type = Column(String(20), default='arbitrage', index=True)  # arbitrage, good_ev, middle
    bet_date = Column(Date, nullable=False, index=True)
    match_name = Column(String(255))  # Match name (e.g., "Utah Jazz vs Sacramento Kings")
    sport = Column(String(100))  # Sport/League (e.g., "NBA - Player Rebounds + Assists")
    match_date = Column(Date)  # Actual match date (different from bet_date)
    total_stake = Column(Float, nullable=False)
    expected_profit = Column(Float, nullable=False)
    actual_profit = Column(Float)  # NULL until confirmed
    status = Column(String(20), default='pending', index=True)  # pending, confirmed, corrected
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationship to access drop_event data
    drop_event = relationship("DropEvent", foreign_keys=[drop_event_id])
    
    def __repr__(self):
        return f"<UserBet(id={self.id}, user={self.user_id}, stake={self.total_stake}, profit={self.expected_profit})>"


class DailyStats(Base):
    """
    Aggregated daily statistics per user
    """
    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'), index=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    total_bets = Column(Integer, default=0)
    total_staked = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    confirmed = Column(Boolean, default=False, index=True)  # Whether user confirmed the stats
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<DailyStats(user={self.user_id}, date={self.date}, bets={self.total_bets}, profit={self.total_profit})>"
    
    @property
    def roi(self) -> float:
        """Return on investment percentage"""
        if not self.total_staked or self.total_staked == 0:
            return 0.0
        return (self.total_profit / self.total_staked) * 100


class ConversationState(Base):
    """
    Track conversation state for bet corrections
    """
    __tablename__ = "conversation_states"
    
    user_id = Column(Integer, ForeignKey('users.telegram_id'), primary_key=True, index=True)
    state = Column(String(50))  # awaiting_bet_count, awaiting_stakes, awaiting_profit
    context = Column(JSON)  # Temporary data for the conversation
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ConversationState(user={self.user_id}, state={self.state})>"
