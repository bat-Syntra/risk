"""
Referral model for tracking referrals and commissions
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from database import Base


class Referral(Base):
    """
    Referral relationship - tracks who referred whom and commissions
    """
    __tablename__ = "referrals"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Referral relationship
    referrer_id = Column(Integer, index=True, nullable=False)  # telegram_id who referred
    referee_id = Column(Integer, index=True, nullable=False)   # telegram_id who was referred
    
    # Commission tracking
    commission_rate = Column(Float, default=0.20)  # 20% default
    total_earned = Column(Float, default=0.0)      # Total commissions earned
    pending_commission = Column(Float, default=0.0)  # Pending payout
    paid_commission = Column(Float, default=0.0)     # Already paid
    
    # Referee info (snapshot)
    referee_tier = Column(String(20))
    referee_subscription_value = Column(Float)  # Monthly subscription value
    
    # Status
    is_active = Column(Boolean, default=True)  # False if referee cancels subscription
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_commission_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Referral(referrer={self.referrer_id}, referee={self.referee_id}, earned=${self.total_earned})>"
    
    def add_commission(self, amount: float):
        """Add commission to this referral"""
        self.total_earned += amount
        self.pending_commission += amount
        self.last_commission_at = datetime.now()
    
    def mark_paid(self, amount: float):
        """Mark commission as paid"""
        self.pending_commission -= amount
        self.paid_commission += amount
    
    @property
    def monthly_commission(self) -> float:
        """Monthly recurring commission if active"""
        if not self.is_active or not self.referee_subscription_value:
            return 0.0
        return self.referee_subscription_value * self.commission_rate


class ReferralTier2(Base):
    """
    Second-tier referral tracking (referrals of referrals)
    """
    __tablename__ = "referrals_tier2"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tier 2 relationship
    original_referrer_id = Column(Integer, index=True, nullable=False)  # Original referrer
    tier1_referrer_id = Column(Integer, index=True, nullable=False)     # Direct referrer
    referee_id = Column(Integer, index=True, nullable=False)            # End user
    
    # Commission (typically 10% for tier 2)
    commission_rate = Column(Float, default=0.10)
    total_earned = Column(Float, default=0.0)
    pending_commission = Column(Float, default=0.0)
    paid_commission = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_commission_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<ReferralTier2(original={self.original_referrer_id}, referee={self.referee_id})>"
    
    def add_commission(self, amount: float):
        """Add tier 2 commission"""
        self.total_earned += amount
        self.pending_commission += amount
        self.last_commission_at = datetime.now()


class ReferralSettings(Base):
    """
    Per-referrer affiliate settings (e.g., manual commission rate override)
    """
    __tablename__ = "referral_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, unique=True, index=True, nullable=False)  # telegram_id of referrer
    override_rate = Column(Float)  # Optional manual override for tier-1 commission (0.20..0.60)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
