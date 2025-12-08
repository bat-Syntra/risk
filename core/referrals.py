"""
Referral system with tier 1 and tier 2 commissions
Dynamic tier-1 commission:
- Base: 10%
- Alpha: 12.5%
- 5 clients: 15% + Alpha gratuit
- 10 clients: 25%
- 20 clients: 30%
- 30+ clients: 40%
Tier-2 commission fixed at 10%.
"""
import string
import random
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.user import User, TierLevel
from models.referral import Referral, ReferralTier2, ReferralSettings
from core.tiers import TierManager, TierLevel as CoreTierLevel


class ReferralManager:
    """
    Manages referral codes, tracking, and commission calculations
    """
    
    # Base Commission rates (tier2 fixed). Tier1 is dynamic via get_dynamic_tier1_rate().
    COMMISSION_RATES = {
        "tier1": 0.10,  # base 10% for direct referrals
        "tier1_alpha": 0.125,  # 12.5% for Alpha members
        "tier2": 0.10,  # 10% for second-tier referrals
    }
    
    # No special tier bonus in simplified FREE/PREMIUM model
    
    @staticmethod
    def generate_referral_code(length: int = 8) -> str:
        """
        Generate unique referral code
        
        Args:
            length: Length of code (default 8)
            
        Returns:
            Random alphanumeric code (uppercase)
        """
        characters = string.ascii_uppercase + string.digits
        # Exclude confusing characters
        characters = characters.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def create_user_referral_code(db: Session, telegram_id: int) -> str:
        """
        Create or get referral code for a user
        
        Args:
            db: Database session
            telegram_id: User's telegram ID
            
        Returns:
            Referral code
        """
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            return None
        
        # Check if user already has a code
        if user.referral_code:
            return user.referral_code
        
        # Generate unique code
        max_attempts = 10
        for _ in range(max_attempts):
            code = ReferralManager.generate_referral_code()
            
            # Check if code already exists
            existing = db.query(User).filter(User.referral_code == code).first()
            if not existing:
                user.referral_code = code
                db.commit()
                return code

    # ===== Dynamic Tier Helpers =====
    @staticmethod
    def count_active_tier1(db: Session, referrer_id: int) -> int:
        """Count active direct referrals for a referrer."""
        return db.query(Referral).filter(Referral.referrer_id == referrer_id, Referral.is_active == True).count()

    @staticmethod
    def get_dynamic_tier1_rate(db: Session, referrer_id: int) -> float:
        """Return tier-1 commission rate based on number of active direct referrals."""
        # Check manual override first
        try:
            rs = db.query(ReferralSettings).filter(ReferralSettings.referrer_id == referrer_id).first()
            if rs and rs.override_rate is not None:
                # Clamp between 0.08 and 0.60
                val = max(0.08, min(0.60, float(rs.override_rate)))
                return val
        except Exception:
            pass
        
        # Get referrer to check tier
        try:
            referrer = db.query(User).filter(User.telegram_id == referrer_id).first()
            is_free = referrer and referrer.tier == TierLevel.FREE
        except Exception:
            is_free = True  # Default to FREE behavior
        
        # Get active count
        try:
            active = ReferralManager.count_active_tier1(db, referrer_id)
        except Exception:
            active = 0
        
        # Base rates
        if is_free:
            return 0.10  # 10% base for all users
        else:
            base_rate = 0.125  # 12.5% for Alpha members
        
        # Progressive thresholds
        if active >= 30:
            return 0.40  # 40% for 30+ clients
        if active >= 20:
            return 0.30  # 30% for 20+ clients
        if active >= 10:
            return 0.25  # 25% for 10+ clients
        if active >= 5:
            return 0.15  # 15% for 5+ clients
        return base_rate  # 12.5% Alpha base or 10% Free base

    @staticmethod
    def award_free_premium_if_eligible(db: Session, referrer_id: int) -> bool:
        """Grant long PREMIUM if referrer has >=5 active direct referrals. Returns True if granted/ensured."""
        try:
            active = ReferralManager.count_active_tier1(db, referrer_id)
        except Exception:
            active = 0
        if active < 5:  # Changed from 10 to 5 clients
            return False
        u = db.query(User).filter(User.telegram_id == referrer_id).first()
        if not u:
            return False
        # Ensure PREMIUM with far expiry (e.g., +365 days). Extend if shorter.
        target_end = datetime.now() + timedelta(days=365)
        if u.tier != TierLevel.PREMIUM:
            u.tier = TierLevel.PREMIUM
            u.subscription_start = datetime.now()
            u.subscription_end = target_end
            db.commit()
            return True
        # Already premium: extend if expiring sooner than target_end
        try:
            if not u.subscription_end or u.subscription_end < target_end:
                u.subscription_end = target_end
                db.commit()
                return True
        except Exception:
            pass
        return False
        
        # Fallback: use telegram_id as suffix
        code = f"REF{telegram_id % 100000}"
        user.referral_code = code
        db.commit()
        return code
    
    @staticmethod
    def apply_referral(db: Session, referee_telegram_id: int, referral_code: str) -> bool:
        """
        Apply referral code when new user signs up
        
        Args:
            db: Database session
            referee_telegram_id: New user's telegram ID
            referral_code: Referral code used
            
        Returns:
            True if successfully applied
        """
        # Find referee (new user)
        referee = db.query(User).filter(User.telegram_id == referee_telegram_id).first()
        if not referee:
            return False
        
        # Don't allow if already referred
        if referee.referred_by:
            return False
        
        # Find referrer by code
        referrer = db.query(User).filter(User.referral_code == referral_code).first()
        if not referrer:
            return False
        
        # Can't refer yourself
        if referrer.telegram_id == referee_telegram_id:
            return False
        
        # Apply referral
        referee.referred_by = referrer.telegram_id
        
        # Create Referral record (tier 1)
        referral = Referral(
            referrer_id=referrer.telegram_id,
            referee_id=referee.telegram_id,
            commission_rate=ReferralManager.COMMISSION_RATES["tier1"],
            referee_tier=referee.tier.value,
            referee_subscription_value=(
                TierManager.get_price(CoreTierLevel.PREMIUM)
                if referee.tier == TierLevel.PREMIUM else 0
            ),
        )
        db.add(referral)
        
        # Check for tier 2 referral (referrer was also referred by someone)
        if referrer.referred_by:
            original_referrer = db.query(User).filter(
                User.telegram_id == referrer.referred_by
            ).first()
            
            if original_referrer:
                # Create tier 2 referral
                tier2_referral = ReferralTier2(
                    original_referrer_id=original_referrer.telegram_id,
                    tier1_referrer_id=referrer.telegram_id,
                    referee_id=referee.telegram_id,
                    commission_rate=ReferralManager.COMMISSION_RATES["tier2"],
                )
                db.add(tier2_referral)
        
        db.commit()
        return True
    
    @staticmethod
    def calculate_commission(
        db: Session,
        referee_telegram_id: int,
        payment_amount: float,
        tier: TierLevel
    ) -> Dict:
        """
        Calculate and distribute commissions when referee makes a payment
        
        Args:
            db: Database session
            referee_telegram_id: User who made payment
            payment_amount: Amount paid
            tier: Tier subscribed to
            
        Returns:
            Dictionary with commission breakdown
        """
        result = {
            "total_distributed": 0,
            "tier1_commission": 0,
            "tier2_commission": 0,
            "tier1_referrer_id": None,
            "tier2_referrer_id": None,
        }
        
        # Find referee
        referee = db.query(User).filter(User.telegram_id == referee_telegram_id).first()
        if not referee or not referee.referred_by:
            return result
        
        # Find tier 1 referral
        tier1_referral = db.query(Referral).filter(
            Referral.referee_id == referee_telegram_id
        ).first()
        
        if tier1_referral and tier1_referral.is_active:
            # Calculate tier 1 commission (dynamic rate based on referrer's active directs)
            dynamic_rate = ReferralManager.get_dynamic_tier1_rate(db, tier1_referral.referrer_id)
            tier1_commission = payment_amount * dynamic_rate
            
            # Add commission
            tier1_referral.add_commission(tier1_commission)
            tier1_referral.referee_tier = tier.value
            tier1_referral.referee_subscription_value = payment_amount
            # Update stored rate snapshot to current dynamic for transparency
            try:
                tier1_referral.commission_rate = dynamic_rate
            except Exception:
                pass
            
            result["tier1_commission"] = round(tier1_commission, 2)
            result["tier1_referrer_id"] = tier1_referral.referrer_id
            result["total_distributed"] += tier1_commission
        
        # Find tier 2 referral
        tier2_referral = db.query(ReferralTier2).filter(
            ReferralTier2.referee_id == referee_telegram_id
        ).first()
        
        if tier2_referral and tier2_referral.is_active:
            # Calculate tier 2 commission
            tier2_commission = payment_amount * tier2_referral.commission_rate
            
            # Add commission
            tier2_referral.add_commission(tier2_commission)
            
            result["tier2_commission"] = round(tier2_commission, 2)
            result["tier2_referrer_id"] = tier2_referral.original_referrer_id
            result["total_distributed"] += tier2_commission
        
        db.commit()
        # Bonus: check if referrer qualifies for free PREMIUM (>=10 active directs)
        try:
            if tier1_referral:
                ReferralManager.award_free_premium_if_eligible(db, tier1_referral.referrer_id)
        except Exception:
            pass
        
        result["total_distributed"] = round(result["total_distributed"], 2)
        return result
    
    @staticmethod
    def get_referral_stats(db: Session, telegram_id: int) -> Dict:
        """
        Get referral statistics for a user
        
        Args:
            db: Database session
            telegram_id: User's telegram ID
            
        Returns:
            Dictionary with referral stats
        """
        # Get direct referrals (tier 1)
        tier1_referrals = db.query(Referral).filter(
            Referral.referrer_id == telegram_id
        ).all()
        
        # Get indirect referrals (tier 2)
        tier2_referrals = db.query(ReferralTier2).filter(
            ReferralTier2.original_referrer_id == telegram_id
        ).all()
        
        # Calculate totals
        tier1_count = len(tier1_referrals)
        tier2_count = len(tier2_referrals)
        
        tier1_earnings = sum(r.total_earned for r in tier1_referrals)
        tier2_earnings = sum(r.total_earned for r in tier2_referrals)
        
        tier1_pending = sum(r.pending_commission for r in tier1_referrals)
        tier2_pending = sum(r.pending_commission for r in tier2_referrals)
        
        # Monthly recurring (active subscriptions only)
        tier1_monthly = sum(
            r.monthly_commission for r in tier1_referrals if r.is_active
        )
        tier2_monthly = sum(
            r.monthly_commission for r in tier2_referrals if r.is_active
        )
        
        return {
            "tier1": {
                "count": tier1_count,
                "total_earned": round(tier1_earnings, 2),
                "pending": round(tier1_pending, 2),
                "monthly_recurring": round(tier1_monthly, 2),
            },
            "tier2": {
                "count": tier2_count,
                "total_earned": round(tier2_earnings, 2),
                "pending": round(tier2_pending, 2),
                "monthly_recurring": round(tier2_monthly, 2),
            },
            "total": {
                "count": tier1_count + tier2_count,
                "total_earned": round(tier1_earnings + tier2_earnings, 2),
                "pending": round(tier1_pending + tier2_pending, 2),
                "monthly_recurring": round(tier1_monthly + tier2_monthly, 2),
            }
        }
    
    @staticmethod
    def get_top_referrers(db: Session, limit: int = 10) -> list:
        """
        Get top referrers by total earnings
        
        Args:
            db: Database session
            limit: Number of top referrers to return
            
        Returns:
            List of tuples (telegram_id, username, total_earnings)
        """
        from sqlalchemy import func
        
        top_referrers = db.query(
            Referral.referrer_id,
            func.sum(Referral.total_earned).label('total_earned')
        ).group_by(
            Referral.referrer_id
        ).order_by(
            func.sum(Referral.total_earned).desc()
        ).limit(limit).all()
        
        result = []
        for referrer_id, total_earned in top_referrers:
            user = db.query(User).filter(User.telegram_id == referrer_id).first()
            username = user.username if user else "Unknown"
            result.append((referrer_id, username, round(total_earned, 2)))
        
        return result
    
    @staticmethod
    def deactivate_referral(db: Session, referee_telegram_id: int):
        """
        Deactivate referral when user cancels subscription
        
        Args:
            db: Database session
            referee_telegram_id: User who canceled
        """
        # Deactivate tier 1
        tier1 = db.query(Referral).filter(
            Referral.referee_id == referee_telegram_id
        ).first()
        if tier1:
            tier1.is_active = False
        
        # Deactivate tier 2
        tier2 = db.query(ReferralTier2).filter(
            ReferralTier2.referee_id == referee_telegram_id
        ).first()
        if tier2:
            tier2.is_active = False
        
        db.commit()
    
    @staticmethod
    def reactivate_referral(db: Session, referee_telegram_id: int, new_tier: TierLevel):
        """
        Reactivate referral when user resubscribes
        
        Args:
            db: Database session
            referee_telegram_id: User who resubscribed
            new_tier: New tier level
        """
        # Reactivate tier 1
        tier1 = db.query(Referral).filter(
            Referral.referee_id == referee_telegram_id
        ).first()
        if tier1:
            tier1.is_active = True
            tier1.referee_tier = new_tier.value
            tier1.referee_subscription_value = (
                TierManager.get_price(CoreTierLevel.PREMIUM) if new_tier == TierLevel.PREMIUM else 0
            )
        
        # Reactivate tier 2
        tier2 = db.query(ReferralTier2).filter(
            ReferralTier2.referee_id == referee_telegram_id
        ).first()
        if tier2:
            tier2.is_active = True
        
        db.commit()
