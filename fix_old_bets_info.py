"""
Script pour remplir les infos manquantes (match_name, sport, match_date) 
des vieux UserBet en les récupérant depuis DropEvent.
"""
import logging
from datetime import datetime
from database import SessionLocal
from models.bet import UserBet
from models.drop_event import DropEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_old_bets():
    """Fix old UserBet entries with missing match info"""
    db = SessionLocal()
    try:
        # Find all MIDDLE bets with drop_event_id (to recalculate values)
        middle_bets = db.query(UserBet).filter(
            UserBet.bet_type == 'middle',
            UserBet.drop_event_id.isnot(None)
        ).all()
        
        # Also find bets with missing match_name
        missing_info_bets = db.query(UserBet).filter(
            UserBet.match_name.is_(None),
            UserBet.drop_event_id.isnot(None)
        ).all()
        
        # Combine both lists (unique)
        old_bets = list(set(middle_bets + missing_info_bets))
        
        logger.info(f"Found {len(old_bets)} bets to fix (including {len(middle_bets)} MIDDLE bets)")
        
        fixed_count = 0
        for bet in old_bets:
            try:
                # Get the associated DropEvent
                drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
                
                if not drop:
                    logger.warning(f"Bet {bet.id} has drop_event_id {bet.drop_event_id} but DropEvent not found")
                    continue
                
                # Extract match info
                match_name = drop.match
                sport_name = drop.league
                match_date = None
                
                # Try to parse commence_time from payload
                if drop.payload:
                    try:
                        commence_time = drop.payload.get('commence_time')
                        if commence_time:
                            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                            match_date = dt.date()
                    except Exception as e:
                        logger.warning(f"Could not parse commence_time for bet {bet.id}: {e}")
                    
                    # For MIDDLE bets, recalculate total_stake and expected_profit from payload
                    if bet.bet_type == 'middle':
                        try:
                            from utils.middle_calculator import classify_middle_type
                            side_a = drop.payload.get('side_a', {})
                            side_b = drop.payload.get('side_b', {})
                            
                            if side_a and side_b:
                                # Use default bankroll (we can't recover the original)
                                # Most users use $550-$750, so use 550 as default
                                bankroll = 550.0
                                
                                # Recalculate with default bankroll
                                cls = classify_middle_type(side_a, side_b, bankroll)
                                
                                # Update values
                                bet.total_stake = cls['total_stake']
                                bet.expected_profit = cls['profit_scenario_2']  # Jackpot profit (both bets win)
                                
                                logger.info(f"  Recalculated MIDDLE: stake=${bet.total_stake:.2f}, jackpot=${bet.expected_profit:.2f}")
                        except Exception as e:
                            logger.warning(f"Could not recalculate MIDDLE for bet {bet.id}: {e}")
                
                # Update bet
                if match_name:
                    bet.match_name = match_name
                if sport_name:
                    bet.sport = sport_name
                if match_date:
                    bet.match_date = match_date
                
                fixed_count += 1
                logger.info(f"Fixed bet {bet.id}: {match_name} | {sport_name} | {match_date}")
                
            except Exception as e:
                logger.error(f"Error fixing bet {bet.id}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Successfully fixed {fixed_count}/{len(old_bets)} bets")
        
    except Exception as e:
        logger.error(f"Error in fix_old_bets: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting to fix old UserBet entries...")
    fix_old_bets()
    logger.info("Done!")
