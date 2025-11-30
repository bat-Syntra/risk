"""
Script pour voir TOUS les MIDDLE bets et identifier ceux qui ont les mauvaises valeurs
"""
import logging
from database import SessionLocal
from models.drop_event import DropEvent  # Import first to avoid circular dependency
from models.bet import UserBet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_all_middles():
    """Check all MIDDLE bets"""
    db = SessionLocal()
    try:
        # Find ALL MIDDLE bets
        all_middles = db.query(UserBet).filter(
            UserBet.bet_type == 'middle'
        ).all()
        
        logger.info(f"Found {len(all_middles)} MIDDLE bets total:")
        logger.info("=" * 80)
        
        for bet in all_middles:
            logger.info(f"Bet #{bet.id}")
            logger.info(f"  Match: {bet.match_name or 'N/A'}")
            logger.info(f"  Sport: {bet.sport or 'N/A'}")
            logger.info(f"  Match Date: {bet.match_date or 'N/A'}")
            logger.info(f"  Bet Date: {bet.bet_date}")
            logger.info(f"  Drop Event ID: {bet.drop_event_id}")
            logger.info(f"  Total Stake: ${bet.total_stake:.2f}")
            logger.info(f"  Expected Profit: ${bet.expected_profit:.2f}")
            logger.info(f"  Status: {bet.status}")
            
            # Check if values look wrong (stake too small)
            if bet.total_stake < 100:
                logger.warning(f"  ⚠️ SUSPICIOUS: Stake too low (${bet.total_stake:.2f})")
            
            logger.info("-" * 80)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_all_middles()
