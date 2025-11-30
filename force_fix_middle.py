"""
Script pour forcer la correction de TOUS les MIDDLE bets avec drop_event_id
Et supprimer ceux sans drop_event_id (impossible à corriger)
"""
import logging
from datetime import datetime
from database import SessionLocal
from models.drop_event import DropEvent
from models.bet import UserBet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_fix_all_middles():
    """Force fix ALL MIDDLE bets"""
    db = SessionLocal()
    try:
        # Find ALL MIDDLE bets
        all_middles = db.query(UserBet).filter(
            UserBet.bet_type == 'middle'
        ).all()
        
        logger.info(f"Found {len(all_middles)} MIDDLE bets total")
        
        fixed_count = 0
        deleted_count = 0
        
        for bet in all_middles:
            try:
                if bet.drop_event_id is None:
                    # Cannot fix - no DropEvent reference
                    logger.warning(f"Bet #{bet.id}: No drop_event_id - DELETING (cannot be fixed)")
                    db.delete(bet)
                    deleted_count += 1
                    continue
                
                # Get DropEvent
                drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
                
                if not drop:
                    logger.warning(f"Bet #{bet.id}: DropEvent {bet.drop_event_id} not found - DELETING")
                    db.delete(bet)
                    deleted_count += 1
                    continue
                
                # Extract match info
                match_name = drop.match
                sport_name = drop.league
                match_date = None
                
                # Parse commence_time
                if drop.payload:
                    try:
                        commence_time = drop.payload.get('commence_time')
                        if commence_time:
                            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                            match_date = dt.date()
                    except Exception as e:
                        logger.warning(f"Could not parse commence_time for bet {bet.id}: {e}")
                    
                    # Recalculate MIDDLE values
                    try:
                        from utils.middle_calculator import classify_middle_type
                        side_a = drop.payload.get('side_a', {})
                        side_b = drop.payload.get('side_b', {})
                        
                        if side_a and side_b:
                            # Use default bankroll
                            bankroll = 550.0
                            
                            # Recalculate
                            cls = classify_middle_type(side_a, side_b, bankroll)
                            
                            # Update ALL values
                            bet.match_name = match_name
                            bet.sport = sport_name
                            bet.match_date = match_date
                            bet.total_stake = cls['total_stake']
                            bet.expected_profit = cls['profit_scenario_2']  # Jackpot
                            
                            logger.info(f"✅ Fixed bet #{bet.id}: {match_name}")
                            logger.info(f"   Stake: ${bet.total_stake:.2f}, Jackpot: ${bet.expected_profit:.2f}")
                            fixed_count += 1
                    except Exception as e:
                        logger.error(f"Could not recalculate bet #{bet.id}: {e}")
                
            except Exception as e:
                logger.error(f"Error processing bet #{bet.id}: {e}")
                continue
        
        db.commit()
        logger.info("=" * 80)
        logger.info(f"✅ Fixed: {fixed_count} bets")
        logger.info(f"🗑️  Deleted: {deleted_count} bets (no drop_event_id)")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting aggressive MIDDLE bet fixing...")
    force_fix_all_middles()
    logger.info("Done!")
