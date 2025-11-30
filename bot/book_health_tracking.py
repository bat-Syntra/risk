"""
Book Health Auto-Tracking
Automatically tracks bets when users click "I BET"
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict
from decimal import Decimal

from database import SessionLocal
from models.user import User
from models.bet import UserBet
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)

# Import ML tracker
try:
    from bot.ml_event_tracker import ml_tracker
    ML_TRACKING_ENABLED = True
except ImportError:
    ML_TRACKING_ENABLED = False
    logger.warning("ML tracking not available")


class BetTrackingIntegration:
    """Auto-tracking for Book Health when users place bets"""
    
    async def log_bet_placement(
        self, 
        user_id: str, 
        bet_id: str,
        casino: str,
        bet_type: str = None,  # 'arbitrage', 'middle', 'plus_ev'
        sport: str = None,
        market_type: str = None,
        odds: float = None,
        stake: float = None,
        is_recreational: bool = False
    ):
        """Log a bet placement for Book Health tracking"""
        logger.info(f"📝 Logging bet for Book Health: {user_id} @ {casino}")
        
        db = SessionLocal()
        try:
            # Check if user has Book Health profile for this casino
            has_profile = db.execute(sql_text("""
                SELECT 1 FROM user_casino_profiles
                WHERE user_id = :user_id AND casino = :casino
            """), {"user_id": user_id, "casino": casino}).first()
            
            if not has_profile:
                # User doesn't have profile - don't track yet
                logger.info(f"No Book Health profile for {user_id} @ {casino}")
                return False
            
            # Determine bet source type
            if is_recreational:
                source_type = 'recreational'
            elif bet_type in ['arbitrage', 'middle', 'plus_ev']:
                source_type = bet_type
            else:
                source_type = 'plus_ev'  # Default
            
            # Check if stake is rounded
            stake_rounded = False
            if stake:
                if stake % 5 == 0 or stake % 10 == 0:
                    stake_rounded = True
            
            # Get user's current bankroll
            user = db.query(User).filter(User.telegram_id == int(user_id)).first()
            bankroll = None
            if user:
                # Try to get from preferences
                pref = db.execute(sql_text("""
                    SELECT bankroll FROM user_preferences
                    WHERE user_id = :user_id
                """), {"user_id": user_id}).first()
                if pref:
                    bankroll = pref.bankroll
            
            # Insert into bet_analytics
            analytics_id = str(uuid.uuid4())
            db.execute(sql_text("""
                INSERT INTO bet_analytics (
                    analytics_id, user_id, bet_id, casino, bet_source_type,
                    sport, market_type, bet_placed_at, stake_amount,
                    stake_rounded, odds_at_bet, bankroll_at_time
                ) VALUES (
                    :id, :user_id, :bet_id, :casino, :source_type,
                    :sport, :market, :placed_at, :stake,
                    :rounded, :odds, :bankroll
                )
            """), {
                "id": analytics_id,
                "user_id": user_id,
                "bet_id": bet_id,
                "casino": casino,
                "source_type": source_type,
                "sport": sport,
                "market": market_type,
                "placed_at": datetime.utcnow(),
                "stake": stake or 0,
                "rounded": stake_rounded,
                "odds": odds,
                "bankroll": bankroll
            })
            
            db.commit()
            
            # Track for ML
            if ML_TRACKING_ENABLED:
                try:
                    await ml_tracker.track_event(
                        'bet_placed',
                        {
                            'bet_id': bet_id,
                            'casino': casino,
                            'bet_type': source_type,
                            'sport': sport,
                            'market': market_type,
                            'odds': odds,
                            'stake': stake or 0,
                            'is_recreational': is_recreational
                        },
                        user_id=user_id,
                        importance=7,
                        tags=['betting', 'book_health', casino, source_type]
                    )
                except Exception as e:
                    logger.error(f"ML tracking failed: {e}")
            
            logger.info(f"✅ Bet tracked for Book Health: {analytics_id}")
            
            # Check if we should calculate score (every 10 bets)
            bet_count = db.execute(sql_text("""
                SELECT COUNT(*) as count FROM bet_analytics
                WHERE user_id = :user_id AND casino = :casino
            """), {"user_id": user_id, "casino": casino}).first()
            
            if bet_count and bet_count.count % 10 == 0:
                # Calculate score in background
                from bot.book_health_scoring import BookHealthScoring
                scorer = BookHealthScoring()
                score_data = scorer.calculate_health_score(user_id, casino)
                
                # Check if critical
                if score_data.get('risk_level') in ['CRITICAL', 'HIGH_RISK']:
                    # Should send alert
                    return {'alert_needed': True, 'score_data': score_data}
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking bet: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def update_bet_result(self, bet_id: str, result: str, profit_loss: float = None):
        """Update bet result after game completes"""
        db = SessionLocal()
        try:
            db.execute(sql_text("""
                UPDATE bet_analytics
                SET result = :result,
                    profit_loss = :profit_loss
                WHERE bet_id = :bet_id
            """), {
                "bet_id": bet_id,
                "result": result,  # 'won', 'lost', 'push', 'void'
                "profit_loss": profit_loss
            })
            
            db.commit()
            logger.info(f"✅ Updated bet result: {bet_id} -> {result}")
            
        except Exception as e:
            logger.error(f"Error updating bet result: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def update_clv(self, bet_id: str, closing_odds: float):
        """Update CLV (Closing Line Value) for a bet"""
        db = SessionLocal()
        try:
            # Get original odds
            bet_data = db.execute(sql_text("""
                SELECT odds_at_bet FROM bet_analytics
                WHERE bet_id = :bet_id
            """), {"bet_id": bet_id}).first()
            
            if bet_data and bet_data.odds_at_bet:
                # Calculate CLV
                # CLV = (closing_odds - bet_odds) / bet_odds
                clv = (closing_odds - float(bet_data.odds_at_bet)) / float(bet_data.odds_at_bet)
                
                db.execute(sql_text("""
                    UPDATE bet_analytics
                    SET closing_odds = :closing,
                        clv = :clv
                    WHERE bet_id = :bet_id
                """), {
                    "bet_id": bet_id,
                    "closing": closing_odds,
                    "clv": clv
                })
                
                db.commit()
                logger.info(f"✅ Updated CLV: {bet_id} -> {clv:.4f}")
            
        except Exception as e:
            logger.error(f"Error updating CLV: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def mark_as_recreational(self, bet_id: str):
        """Mark a bet as recreational"""
        db = SessionLocal()
        try:
            # Update bet_analytics
            db.execute(sql_text("""
                UPDATE bet_analytics
                SET bet_source_type = 'recreational'
                WHERE bet_id = :bet_id
            """), {"bet_id": bet_id})
            
            # Also add to recreational_bets table
            db.execute(sql_text("""
                INSERT INTO recreational_bets (bet_id, user_id, tagged_at)
                SELECT :bet_id, user_id, :now
                FROM bet_analytics
                WHERE bet_id = :bet_id
                ON CONFLICT (bet_id) DO NOTHING
            """), {
                "bet_id": bet_id,
                "now": datetime.utcnow()
            })
            
            db.commit()
            logger.info(f"✅ Marked as recreational: {bet_id}")
            
        except Exception as e:
            logger.error(f"Error marking as recreational: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_tracking_stats(self, user_id: str, casino: str) -> Dict:
        """Get tracking statistics for user-casino pair"""
        db = SessionLocal()
        try:
            stats = db.execute(sql_text("""
                SELECT 
                    COUNT(*) as total_bets,
                    COUNT(CASE WHEN result = 'won' THEN 1 END) as wins,
                    COUNT(CASE WHEN result = 'lost' THEN 1 END) as losses,
                    AVG(stake_amount) as avg_stake,
                    SUM(profit_loss) as total_profit,
                    COUNT(CASE WHEN bet_source_type = 'recreational' THEN 1 END) as rec_bets,
                    COUNT(CASE WHEN bet_source_type IN ('arbitrage', 'middle', 'plus_ev') THEN 1 END) as sharp_bets
                FROM bet_analytics
                WHERE user_id = :user_id AND casino = :casino
            """), {"user_id": user_id, "casino": casino}).first()
            
            if stats:
                return {
                    'total_bets': stats.total_bets or 0,
                    'wins': stats.wins or 0,
                    'losses': stats.losses or 0,
                    'avg_stake': float(stats.avg_stake) if stats.avg_stake else 0,
                    'total_profit': float(stats.total_profit) if stats.total_profit else 0,
                    'rec_bets': stats.rec_bets or 0,
                    'sharp_bets': stats.sharp_bets or 0,
                    'win_rate': (stats.wins / (stats.wins + stats.losses)) if (stats.wins + stats.losses) > 0 else 0
                }
            
            return {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'avg_stake': 0,
                'total_profit': 0,
                'rec_bets': 0,
                'sharp_bets': 0,
                'win_rate': 0
            }
            
        finally:
            db.close()


# Singleton instance
bet_tracker = BetTrackingIntegration()


async def track_parlay_bet(user_id: str, parlay_data: Dict, casino: str, is_recreational: bool = False):
    """Track a parlay bet for Book Health"""
    # For parlays, we track each leg separately
    legs = parlay_data.get('legs', [])
    
    for leg in legs:
        await bet_tracker.log_bet_placement(
            user_id=user_id,
            bet_id=leg.get('bet_id', str(uuid.uuid4())),
            casino=casino,
            bet_type=leg.get('type', 'plus_ev'),
            sport=leg.get('sport'),
            market_type=leg.get('market'),
            odds=leg.get('odds'),
            stake=leg.get('stake'),
            is_recreational=is_recreational
        )


async def track_single_bet(user_id: str, bet_data: Dict, casino: str, is_recreational: bool = False):
    """Track a single bet for Book Health"""
    await bet_tracker.log_bet_placement(
        user_id=user_id,
        bet_id=bet_data.get('bet_id', str(uuid.uuid4())),
        casino=casino,
        bet_type=bet_data.get('type', 'plus_ev'),
        sport=bet_data.get('sport'),
        market_type=bet_data.get('market'),
        odds=bet_data.get('odds'),
        stake=bet_data.get('stake'),
        is_recreational=is_recreational
    )
