"""
ML Event Tracking System
Captures all user actions for machine learning
"""
import logging
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, List

from database import SessionLocal
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)


class MLEventTracker:
    """Comprehensive event tracking for ML/LLM training"""
    
    def __init__(self):
        self.session_cache = {}  # Cache active sessions
    
    async def track_event(
        self,
        event_type: str,
        event_data: Dict,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        importance: int = 5,
        tags: List[str] = None,
        source: str = 'telegram_bot'
    ):
        """
        Track any event in the system
        
        Args:
            event_type: Type of event (e.g., 'bet_placed', 'limit_reported')
            event_data: Event details as dict
            user_id: User who triggered event
            session_id: Current session ID
            importance: 1-10 scale (10 = critical for ML)
            tags: List of tags for filtering
            source: Where event came from
        """
        db = SessionLocal()
        try:
            event_id = str(uuid.uuid4())
            category = self._categorize_event(event_type)
            
            db.execute(sql_text("""
                INSERT INTO system_events (
                    event_id, event_type, event_category, user_id,
                    session_id, event_data, importance_score, tags, source
                ) VALUES (
                    :event_id, :event_type, :category, :user_id,
                    :session_id, :event_data, :importance, :tags, :source
                )
            """), {
                "event_id": event_id,
                "event_type": event_type,
                "category": category,
                "user_id": user_id,
                "session_id": session_id,
                "event_data": json.dumps(event_data),
                "importance": importance,
                "tags": json.dumps(tags or []),
                "source": source
            })
            
            db.commit()
            logger.info(f"📊 Event tracked: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def start_session(
        self,
        user_id: str,
        device_type: str = 'mobile',
        platform: str = 'telegram'
    ) -> str:
        """Start a user behavior session"""
        session_id = str(uuid.uuid4())
        
        db = SessionLocal()
        try:
            db.execute(sql_text("""
                INSERT INTO user_behavior_sessions (
                    session_id, user_id, device_type, platform, started_at
                ) VALUES (:session_id, :user_id, :device, :platform, :now)
            """), {
                "session_id": session_id,
                "user_id": user_id,
                "device": device_type,
                "platform": platform,
                "now": datetime.utcnow()
            })
            
            db.commit()
            
            # Cache session
            self.session_cache[user_id] = {
                'session_id': session_id,
                'started_at': datetime.utcnow()
            }
            
            logger.info(f"🚀 Session started: {session_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            db.rollback()
        finally:
            db.close()
        
        return session_id
    
    async def end_session(self, session_id: str):
        """End a user session"""
        db = SessionLocal()
        try:
            db.execute(sql_text("""
                UPDATE user_behavior_sessions
                SET ended_at = :now,
                    duration_seconds = (
                        CAST((julianday(:now) - julianday(started_at)) * 86400 AS INTEGER)
                    )
                WHERE session_id = :session_id
            """), {
                "session_id": session_id,
                "now": datetime.utcnow()
            })
            
            db.commit()
            logger.info(f"🏁 Session ended: {session_id}")
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def track_bet_decision(
        self,
        user_id: str,
        decision: str,
        parlay_data: Dict,
        user_context: Dict,
        decision_time: float = None,
        stake: float = None
    ):
        """
        Track user's decision on a bet opportunity
        
        Args:
            user_id: User ID
            decision: 'bet', 'skip', 'save', 'ignore'
            parlay_data: Full parlay details
            user_context: User's state at decision time
            decision_time: Seconds to make decision
            stake: Amount bet (if decision was 'bet')
        """
        db = SessionLocal()
        try:
            decision_id = str(uuid.uuid4())
            
            db.execute(sql_text("""
                INSERT INTO bet_decisions (
                    decision_id, user_id, parlay_data, user_context,
                    decision, decision_time_seconds, actual_stake,
                    presented_at, decided_at
                ) VALUES (
                    :id, :user_id, :parlay, :context,
                    :decision, :time, :stake,
                    :presented, :decided
                )
            """), {
                "id": decision_id,
                "user_id": user_id,
                "parlay": json.dumps(parlay_data),
                "context": json.dumps(user_context),
                "decision": decision,
                "time": decision_time,
                "stake": stake,
                "presented": datetime.utcnow(),
                "decided": datetime.utcnow()
            })
            
            db.commit()
            
            # Also track as event
            await self.track_event(
                'bet_decision',
                {
                    'decision': decision,
                    'stake': stake,
                    'parlay_odds': parlay_data.get('odds'),
                    'decision_time': decision_time
                },
                user_id=user_id,
                importance=8 if decision == 'bet' else 5,
                tags=['betting', 'decision', decision]
            )
            
            logger.info(f"🎯 Bet decision tracked: {decision} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking bet decision: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def update_bet_result(
        self,
        decision_id: str,
        result: str,
        profit_loss: float,
        roi: float
    ):
        """Update bet decision with actual outcome"""
        db = SessionLocal()
        try:
            db.execute(sql_text("""
                UPDATE bet_decisions
                SET bet_result = :result,
                    profit_loss = :profit,
                    roi = :roi
                WHERE decision_id = :id
            """), {
                "result": result,
                "profit": profit_loss,
                "roi": roi,
                "id": decision_id
            })
            
            db.commit()
            logger.info(f"✅ Bet result updated: {decision_id} -> {result}")
            
        except Exception as e:
            logger.error(f"Error updating bet result: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _categorize_event(self, event_type: str) -> str:
        """Categorize event for better organization"""
        categories = {
            'user_registered': 'user_lifecycle',
            'user_login': 'user_action',
            'bet_placed': 'user_action',
            'bet_skipped': 'user_action',
            'bet_decision': 'user_action',
            'parlay_viewed': 'user_action',
            'message_sent': 'user_action',
            'command_used': 'user_action',
            
            'limit_reported': 'critical_event',
            'profile_created': 'user_lifecycle',
            'subscription_started': 'revenue',
            'subscription_cancelled': 'churn',
            
            'health_score_calculated': 'system',
            'features_computed': 'system',
            'casino_analyzed': 'ml',
            
            'error_occurred': 'error'
        }
        
        return categories.get(event_type, 'other')
    
    async def get_user_session_stats(self, user_id: str) -> Dict:
        """Get session statistics for a user"""
        db = SessionLocal()
        try:
            result = db.execute(sql_text("""
                SELECT 
                    COUNT(*) as total_sessions,
                    AVG(duration_seconds) as avg_duration,
                    SUM(messages_sent) as total_messages,
                    SUM(bets_clicked) as total_bets_clicked
                FROM user_behavior_sessions
                WHERE user_id = :user_id
            """), {"user_id": user_id}).first()
            
            if result:
                return {
                    'total_sessions': result.total_sessions or 0,
                    'avg_duration': result.avg_duration or 0,
                    'total_messages': result.total_messages or 0,
                    'total_bets_clicked': result.total_bets_clicked or 0
                }
            
            return {}
            
        finally:
            db.close()
    
    async def get_decision_stats(self, user_id: str) -> Dict:
        """Get betting decision statistics"""
        db = SessionLocal()
        try:
            result = db.execute(sql_text("""
                SELECT 
                    COUNT(*) as total_decisions,
                    SUM(CASE WHEN decision = 'bet' THEN 1 ELSE 0 END) as bets_placed,
                    SUM(CASE WHEN decision = 'skip' THEN 1 ELSE 0 END) as bets_skipped,
                    AVG(decision_time_seconds) as avg_decision_time
                FROM bet_decisions
                WHERE user_id = :user_id
            """), {"user_id": user_id}).first()
            
            if result and result.total_decisions:
                return {
                    'total_decisions': result.total_decisions,
                    'bets_placed': result.bets_placed or 0,
                    'bets_skipped': result.bets_skipped or 0,
                    'bet_rate': (result.bets_placed or 0) / result.total_decisions,
                    'avg_decision_time': result.avg_decision_time or 0
                }
            
            return {}
            
        finally:
            db.close()


# Global instance
ml_tracker = MLEventTracker()


# Helper functions for easy integration
async def track_user_action(
    action: str,
    user_id: str,
    details: Dict = None,
    importance: int = 5
):
    """Quick helper to track user actions"""
    await ml_tracker.track_event(
        event_type=action,
        event_data=details or {},
        user_id=user_id,
        importance=importance,
        tags=['user_action', action]
    )


async def track_critical_event(
    event: str,
    user_id: str,
    details: Dict
):
    """Quick helper for critical events"""
    await ml_tracker.track_event(
        event_type=event,
        event_data=details,
        user_id=user_id,
        importance=10,
        tags=['critical', event]
    )
