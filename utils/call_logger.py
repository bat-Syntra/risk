"""
Call Logger for ML/LLM Data Collection
OPTIMIZED: Asynchronous, non-blocking, lightweight
"""
import asyncio
from datetime import datetime, timedelta
import hashlib
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CallLogger:
    """
    Lightweight async logger for arbitrage calls
    NO performance impact on bot - uses background queue
    """
    
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1000)  # Prevent memory overflow
        self.running = False
        self._worker_task = None
        
    async def start(self):
        """Start background worker"""
        if not self.running:
            self.running = True
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("📊 Call Logger started (background mode)")
    
    async def stop(self):
        """Stop background worker"""
        self.running = False
        if self._worker_task:
            self._worker_task.cancel()
            logger.info("📊 Call Logger stopped")
    
    async def log_call(
        self,
        call_type: str,
        sport: str,
        team_a: str,
        team_b: str,
        book_a: str,
        book_b: str,
        odds_a: float,
        odds_b: float,
        roi_percent: float,
        stake_a: float = 0,
        stake_b: float = 0,
        market: str = "moneyline",
        match_date: Optional[datetime] = None,
        users_notified: int = 0
    ):
        """
        Log a call to ML database (ASYNC - non-blocking)
        
        This runs in background and NEVER blocks the bot!
        """
        try:
            # Create compact call data
            call_data = {
                'call_id': self._generate_call_id(team_a, team_b, book_a, book_b, odds_a, odds_b),
                'call_type': call_type,
                'sport': sport,
                'team_a': team_a[:100],  # Truncate to save space
                'team_b': team_b[:100],
                'match_date': match_date,
                'book_a': book_a,
                'book_b': book_b,
                'market': market,
                'odds_a': round(odds_a, 2),
                'odds_b': round(odds_b, 2),
                'roi_percent': round(roi_percent, 2),
                'stake_a': round(stake_a, 2) if stake_a else None,
                'stake_b': round(stake_b, 2) if stake_b else None,
                'profit_expected': round((stake_a + stake_b) * roi_percent / 100, 2) if stake_a and stake_b else None,
                'users_notified': users_notified,
                'sent_at': datetime.now()
            }
            
            # Add to queue (non-blocking)
            if not self.queue.full():
                await self.queue.put(call_data)
            else:
                # Queue full - skip (better than blocking bot)
                logger.warning("⚠️ Call logger queue full - skipping call")
                
        except Exception as e:
            # NEVER let logging crash the bot!
            logger.error(f"Error logging call: {e}")
    
    async def increment_click(self, call_id: str):
        """
        Increment click counter for a call (ASYNC)
        """
        try:
            update_data = {
                'action': 'increment_click',
                'call_id': call_id
            }
            if not self.queue.full():
                await self.queue.put(update_data)
        except Exception as e:
            logger.error(f"Error incrementing click: {e}")
    
    async def update_result(self, call_id: str, outcome: str, profit_actual: float):
        """
        Update call result when match finishes (ASYNC)
        """
        try:
            update_data = {
                'action': 'update_result',
                'call_id': call_id,
                'outcome': outcome,
                'profit_actual': round(profit_actual, 2)
            }
            if not self.queue.full():
                await self.queue.put(update_data)
        except Exception as e:
            logger.error(f"Error updating result: {e}")
    
    async def _process_queue(self):
        """
        Background worker - processes queue WITHOUT blocking bot
        """
        from database import SessionLocal
        
        while self.running:
            try:
                # Wait for item (non-blocking for bot)
                call_data = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                
                # Process in background (separate DB session)
                await self._save_to_db(call_data)
                
                # Small delay to avoid DB overload
                await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                # No items - that's fine
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in call logger worker: {e}")
                await asyncio.sleep(1)  # Prevent rapid errors
    
    async def _save_to_db(self, data: dict):
        """
        Save to database (runs in background thread)
        """
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            if data.get('action') == 'increment_click':
                # Update click count
                db.execute(
                    """UPDATE arbitrage_calls 
                       SET users_clicked = users_clicked + 1 
                       WHERE call_id = ?""",
                    (data['call_id'],)
                )
            elif data.get('action') == 'update_result':
                # Update result
                db.execute(
                    """UPDATE arbitrage_calls 
                       SET outcome = ?, profit_actual = ? 
                       WHERE call_id = ?""",
                    (data['outcome'], data['profit_actual'], data['call_id'])
                )
            else:
                # Insert new call
                db.execute(
                    """INSERT OR IGNORE INTO arbitrage_calls 
                       (call_id, call_type, sport, team_a, team_b, match_date,
                        book_a, book_b, market, odds_a, odds_b, roi_percent,
                        stake_a, stake_b, profit_expected, users_notified, sent_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data['call_id'], data['call_type'], data['sport'],
                        data['team_a'], data['team_b'], data['match_date'],
                        data['book_a'], data['book_b'], data['market'],
                        data['odds_a'], data['odds_b'], data['roi_percent'],
                        data['stake_a'], data['stake_b'], data['profit_expected'],
                        data['users_notified'], data['sent_at']
                    )
                )
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving call to DB: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _generate_call_id(self, team_a: str, team_b: str, book_a: str, book_b: str, odds_a: float, odds_b: float) -> str:
        """
        Generate unique call ID (hash)
        """
        unique_string = f"{team_a}_{team_b}_{book_a}_{book_b}_{odds_a}_{odds_b}_{datetime.now().strftime('%Y%m%d%H')}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    async def cleanup_old_data(self, days_to_keep: int = 365):
        """
        Auto-cleanup old data to keep DB light (runs monthly)
        """
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            result = db.execute(
                "DELETE FROM arbitrage_calls WHERE sent_at < ?",
                (cutoff_date,)
            )
            
            deleted = result.rowcount
            db.commit()
            
            if deleted > 0:
                logger.info(f"🗑️ Cleaned up {deleted} old calls (>{days_to_keep} days)")
                
        except Exception as e:
            logger.error(f"Error cleaning up old calls: {e}")
        finally:
            db.close()


# Global singleton instance
_call_logger_instance = None


def get_call_logger() -> CallLogger:
    """Get global CallLogger instance"""
    global _call_logger_instance
    if _call_logger_instance is None:
        _call_logger_instance = CallLogger()
    return _call_logger_instance
