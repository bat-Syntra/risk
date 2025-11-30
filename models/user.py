"""
User model with tier system
"""
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, Date, Enum
)
from sqlalchemy.sql import func
from database import Base


class TierLevel(enum.Enum):
    """User subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"


class User(Base):
    """
    User model - represents a Telegram bot user
    """
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Telegram info
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    language = Column(String(10), default="en")  # User's preferred language (fr/en)
    
    # Admin role (super_admin, admin, user)
    role = Column(String(20), default="user", index=True)
    
    # Subscription
    tier = Column(Enum(TierLevel), default=TierLevel.FREE, index=True, nullable=False)
    subscription_start = Column(DateTime(timezone=True))
    subscription_end = Column(DateTime(timezone=True))
    free_access = Column(Boolean, default=False, index=True)  # True = free premium access (not counted in revenue)
    is_active = Column(Boolean, default=True, index=True)
    
    # Referral
    referral_code = Column(String(20), unique=True, index=True)
    referred_by = Column(Integer, index=True)  # telegram_id of referrer
    
    # Stats
    total_bets = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    total_loss = Column(Float, default=0.0)
    alerts_today = Column(Integer, default=0)
    last_alert_date = Column(Date)
    last_alert_at = Column(DateTime(timezone=True))  # For spacing check (FREE tier)
    
    # Percentage filters for each alert type (min and max)
    min_arb_percent = Column(Float, default=0.5)
    max_arb_percent = Column(Float, default=100.0)
    min_middle_percent = Column(Float, default=0.5)
    max_middle_percent = Column(Float, default=100.0)
    min_good_ev_percent = Column(Float, default=0.5)
    max_good_ev_percent = Column(Float, default=100.0)
    
    # Stake rounding (0=precise, 1=dollar, 5=5$, 10=10$)
    stake_rounding = Column(Integer, default=0)
    # Rounding mode: 'down' (round down), 'up' (round up, can exceed budget), 'nearest' (default)
    rounding_mode = Column(String, default='nearest')
    
    # Stake randomizer (pour avoir l'air plus humain)
    stake_randomizer_enabled = Column(Boolean, default=False)
    stake_randomizer_amounts = Column(String, default='')  # Ex: "1,5,10" ou "5,10"
    stake_randomizer_mode = Column(String, default='random')  # 'up', 'down', 'random'
    
    # Casino filter (JSON list of selected casinos, null = all casinos)
    selected_casinos = Column(String, nullable=True)
    # Sport filter (JSON list of selected sports, null = all sports)
    selected_sports = Column(String, nullable=True)
    arbitrage_bets = Column(Integer, default=0)
    arbitrage_profit = Column(Float, default=0.0)
    arbitrage_loss = Column(Float, default=0.0)
    good_ev_bets = Column(Integer, default=0)
    good_ev_profit = Column(Float, default=0.0)
    good_ev_loss = Column(Float, default=0.0)
    middle_bets = Column(Integer, default=0)
    middle_profit = Column(Float, default=0.0)
    middle_loss = Column(Float, default=0.0)
    
    # Settings
    default_bankroll = Column(Float, default=400.0)
    default_risk_percentage = Column(Float, default=5.0)
    notifications_enabled = Column(Boolean, default=True)
    enable_good_odds = Column(Boolean, default=False)  # Good Odds Alerts (Positive EV)
    enable_middle = Column(Boolean, default=False)  # Middle Opportunities
    bet_focus_mode = Column(Boolean, default=False)  # Bet Focus Mode (hides Casino/Guide/Referral from main menu)
    match_today_only = Column(Boolean, default=False)  # Only receive alerts for matches starting TODAY
    min_ev_percent = Column(Float, default=12.0)  # Minimum EV% for Good Odds (default 12% for beginners)
    
    # Percentage filters for each bet type
    min_arb_percent = Column(Float, default=0.5)  # Minimum % for arbitrage alerts
    max_arb_percent = Column(Float, default=100.0)  # Maximum % for arbitrage alerts
    min_middle_percent = Column(Float, default=0.5)  # Minimum % for middle alerts
    max_middle_percent = Column(Float, default=100.0)  # Maximum % for middle alerts
    min_good_ev_percent = Column(Float, default=0.5)  # Minimum % for good EV alerts
    max_good_ev_percent = Column(Float, default=100.0)  # Maximum % for good EV alerts
    
    # Admin & moderation
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, tier={self.tier.value})>"
    
    @property
    def is_premium(self) -> bool:
        """Check if user has any premium tier"""
        return self.tier == TierLevel.PREMIUM
    
    @property
    def subscription_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.tier == TierLevel.FREE:
            return True
        # Lifetime PREMIUM: no subscription_end but tier is PREMIUM → treat as active
        if self.tier == TierLevel.PREMIUM and not self.subscription_end:
            return True
        if not self.subscription_end:
            return False
        return datetime.now() < self.subscription_end.replace(tzinfo=None)
    
    @property
    def days_until_expiry(self) -> int:
        """Days until subscription expires (-1 if FREE or expired)"""
        if self.tier == TierLevel.FREE or not self.subscription_end:
            return -1
        delta = self.subscription_end.replace(tzinfo=None) - datetime.now()
        return max(0, delta.days)
    
    def can_receive_alert_today(self, max_alerts: int) -> bool:
        """Check if user can receive another alert today"""
        if self.last_alert_date != date.today():
            return True
        return self.alerts_today < max_alerts
    
    def increment_alert_count(self):
        """Increment today's alert count and update timestamp"""
        if self.last_alert_date != date.today():
            self.alerts_today = 1
            self.last_alert_date = date.today()
        else:
            self.alerts_today += 1
        self.last_alert_at = datetime.now()  # Update last alert timestamp
    
    def update_profit(self, profit: float):
        """Update user's profit stats"""
        if profit > 0:
            self.total_profit += profit
        else:
            self.total_loss += abs(profit)
        self.total_bets += 1
    
    @property
    def net_profit(self) -> float:
        """Net profit (profit - loss)"""
        return self.total_profit - self.total_loss
    
    @property
    def avg_profit_per_bet(self) -> float:
        """Average profit per bet"""
        if self.total_bets == 0:
            return 0.0
        return self.net_profit / self.total_bets
