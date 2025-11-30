"""
Bonus Tracking Model - Track user bonus eligibility and usage
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime, Boolean, String
from sqlalchemy.sql import func
from database import Base


class BonusTracking(Base):
    """Track bonus eligibility and redemption for marketing automation"""
    __tablename__ = 'bonus_tracking'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Eligibility tracking
    started_at = Column(DateTime, nullable=False, default=func.now())  # When user started with /start
    bonus_eligible = Column(Boolean, default=False)  # Is user eligible for bonus?
    bonus_activated_at = Column(DateTime, nullable=True)  # When /bonus was clicked
    bonus_expires_at = Column(DateTime, nullable=True)  # When bonus expires (7 days after activation)
    
    # Redemption tracking
    bonus_redeemed = Column(Boolean, default=False)  # Has user used the bonus?
    bonus_redeemed_at = Column(DateTime, nullable=True)  # When was it redeemed
    
    # Marketing campaign tracking
    campaign_messages_sent = Column(Integer, default=0)  # Number of marketing messages sent
    last_campaign_message_at = Column(DateTime, nullable=True)  # Last time we sent marketing
    
    # Historical tracking
    ever_had_bonus = Column(Boolean, default=False)  # Has user ever been eligible for a bonus?
    bonus_amount = Column(Integer, default=50)  # Amount of bonus in CAD
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<BonusTracking(telegram_id={self.telegram_id}, eligible={self.bonus_eligible}, redeemed={self.bonus_redeemed})>"
