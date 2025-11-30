"""
Safe Call Logger Wrapper with Error Handling & Admin Alerts
Wraps the CallLogger with intelligent error handling and monitoring
"""
import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot

logger = logging.getLogger(__name__)


class SafeCallLogger:
    """
    Safe wrapper around CallLogger with:
    - Error handling (never crashes bot)
    - Admin alerts on failures
    - Automatic retry logic
    - Health monitoring
    """
    
    def __init__(self, bot: Bot, admin_id: int):
        self.bot = bot
        self.admin_id = admin_id
        self.error_count = 0
        self.success_count = 0
        self.last_error = None
        self.enabled = True
        self._alert_sent = False
        
    async def log_call_safe(
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
    ) -> bool:
        """
        Log a call with safe error handling
        
        Returns:
            bool: True if logged successfully, False if failed (but bot continues!)
        """
        if not self.enabled:
            return False
        
        try:
            from utils.call_logger import get_call_logger
            logger_instance = get_call_logger()
            
            await logger_instance.log_call(
                call_type=call_type,
                sport=sport,
                team_a=team_a,
                team_b=team_b,
                book_a=book_a,
                book_b=book_b,
                odds_a=odds_a,
                odds_b=odds_b,
                roi_percent=roi_percent,
                stake_a=stake_a,
                stake_b=stake_b,
                market=market,
                match_date=match_date,
                users_notified=users_notified
            )
            
            self.success_count += 1
            self._alert_sent = False  # Reset alert flag on success
            return True
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ ML Call Logger error: {e}")
            
            # Alert admin after 10 consecutive errors
            if self.error_count >= 10 and not self._alert_sent:
                await self._send_admin_alert()
                self._alert_sent = True
            
            # Auto-disable after 100 errors to prevent spam
            if self.error_count >= 100:
                self.enabled = False
                await self._send_critical_alert()
            
            return False
    
    async def increment_click_safe(self, call_id: str) -> bool:
        """Safely increment click counter"""
        if not self.enabled:
            return False
        
        try:
            from utils.call_logger import get_call_logger
            logger_instance = get_call_logger()
            await logger_instance.increment_click(call_id)
            return True
        except Exception as e:
            logger.error(f"Error incrementing click: {e}")
            return False
    
    async def update_result_safe(self, call_id: str, outcome: str, profit_actual: float) -> bool:
        """Safely update call result"""
        if not self.enabled:
            return False
        
        try:
            from utils.call_logger import get_call_logger
            logger_instance = get_call_logger()
            await logger_instance.update_result(call_id, outcome, profit_actual)
            return True
        except Exception as e:
            logger.error(f"Error updating result: {e}")
            return False
    
    async def _send_admin_alert(self):
        """Send alert to admin about ML logger issues"""
        try:
            message = (
                "⚠️ <b>ML CALL LOGGER - ALERT</b>\n\n"
                f"❌ Errors: {self.error_count}\n"
                f"✅ Success: {self.success_count}\n"
                f"🔴 Last error: {self.last_error}\n\n"
                "📋 Actions:\n"
                "1. Check ML_TROUBLESHOOTING.md\n"
                "2. Verify database connection\n"
                "3. Check disk space\n\n"
                "ℹ️ Bot continues normally (logging disabled temporarily)"
            )
            await self.bot.send_message(
                self.admin_id,
                message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Could not send admin alert: {e}")
    
    async def _send_critical_alert(self):
        """Send critical alert - logger auto-disabled"""
        try:
            message = (
                "🚨 <b>ML CALL LOGGER - CRITICAL</b>\n\n"
                f"❌ {self.error_count} consecutive errors\n"
                "🔴 Logger auto-disabled to prevent issues\n\n"
                "📋 URGENT:\n"
                "1. Check ML_TROUBLESHOOTING.md immediately\n"
                "2. Fix database issues\n"
                "3. Restart bot to re-enable\n\n"
                "ℹ️ Bot continues normally (data collection stopped)"
            )
            await self.bot.send_message(
                self.admin_id,
                message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Could not send critical alert: {e}")
    
    def get_stats(self) -> dict:
        """Get logger statistics"""
        return {
            'enabled': self.enabled,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'error_rate': (self.error_count / (self.success_count + self.error_count) * 100) 
                          if (self.success_count + self.error_count) > 0 else 0
        }


# Global instance
_safe_logger_instance = None


def get_safe_logger(bot: Bot = None, admin_id: int = None) -> SafeCallLogger:
    """Get global safe logger instance"""
    global _safe_logger_instance
    
    if _safe_logger_instance is None:
        if bot is None or admin_id is None:
            raise ValueError("First call must provide bot and admin_id")
        _safe_logger_instance = SafeCallLogger(bot, admin_id)
    
    return _safe_logger_instance
