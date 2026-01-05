#!/usr/bin/env python3
"""
Test script to verify referral system is working correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User, TierLevel
from models.referral import Referral
from core.referrals import ReferralManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_referral_system():
    """Test the referral system end-to-end"""
    db = SessionLocal()
    
    try:
        # Create test referrer user
        referrer_id = 999999999  # Test telegram ID
        referee_id = 888888888   # Test referee telegram ID
        
        # Clean up any existing test users
        db.query(User).filter(User.telegram_id.in_([referrer_id, referee_id])).delete()
        db.query(Referral).filter(Referral.referrer_id == referrer_id).delete()
        db.query(Referral).filter(Referral.referee_id == referee_id).delete()
        db.commit()
        
        # Create referrer
        referrer = User(
            telegram_id=referrer_id,
            username="test_referrer",
            first_name="Test",
            last_name="Referrer",
            language="en",
            tier=TierLevel.FREE,
            is_active=True
        )
        db.add(referrer)
        db.commit()
        
        # Generate referral code for referrer
        referral_code = ReferralManager.create_user_referral_code(db, referrer_id)
        logger.info(f"✅ Created referrer with code: {referral_code}")
        
        # Create referee (new user)
        referee = User(
            telegram_id=referee_id,
            username="test_referee",
            first_name="Test",
            last_name="Referee", 
            language="en",
            tier=TierLevel.FREE,
            is_active=True
        )
        db.add(referee)
        db.commit()
        
        logger.info(f"✅ Created referee user: {referee_id}")
        
        # Test applying referral code
        logger.info(f"🔄 Testing referral application...")
        result = ReferralManager.apply_referral(db, referee_id, referral_code)
        
        if result:
            logger.info(f"✅ Referral applied successfully!")
            
            # Check if referral was recorded
            referral_record = db.query(Referral).filter(
                Referral.referrer_id == referrer_id,
                Referral.referee_id == referee_id
            ).first()
            
            if referral_record:
                logger.info(f"✅ Referral record found in database")
                logger.info(f"   Referrer: {referral_record.referrer_id}")
                logger.info(f"   Referee: {referral_record.referee_id}")
                logger.info(f"   Commission Rate: {referral_record.commission_rate}")
            else:
                logger.error(f"❌ No referral record found in database")
                return False
            
            # Check referee's referred_by field
            db.refresh(referee)
            if referee.referred_by == referrer_id:
                logger.info(f"✅ Referee's referred_by field set correctly")
            else:
                logger.error(f"❌ Referee's referred_by field not set. Expected: {referrer_id}, Got: {referee.referred_by}")
                return False
            
            # Test referral stats
            stats = ReferralManager.get_referral_stats(db, referrer_id)
            if stats['total']['count'] > 0:
                logger.info(f"✅ Referral stats show {stats['total']['count']} referrals")
            else:
                logger.error(f"❌ Referral stats show 0 referrals")
                return False
            
            logger.info(f"🎉 All tests passed! Referral system is working correctly.")
            return True
            
        else:
            logger.error(f"❌ Failed to apply referral code")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        # Clean up test data
        try:
            db.query(Referral).filter(Referral.referrer_id == referrer_id).delete()
            db.query(Referral).filter(Referral.referee_id == referee_id).delete()
            db.query(User).filter(User.telegram_id.in_([referrer_id, referee_id])).delete()
            db.commit()
            logger.info("🧹 Cleaned up test data")
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
        
        db.close()

if __name__ == "__main__":
    print("🧪 Testing referral system...")
    success = test_referral_system()
    if success:
        print("✅ Referral system test PASSED")
        sys.exit(0)
    else:
        print("❌ Referral system test FAILED")
        sys.exit(1)
