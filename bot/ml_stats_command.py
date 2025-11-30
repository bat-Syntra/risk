"""
ML Stats Command for Admin
Check ML Call Logger health and statistics
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from database import SessionLocal
from sqlalchemy import text as sql_text
import os

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    try:
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            return user_id == int(admin_chat_id)
        return False
    except:
        return False


@router.message(Command("ml_stats"))
async def cmd_ml_stats(message: types.Message):
    """Show ML Call Logger statistics"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin only command")
        return
    
    try:
        from utils.safe_call_logger import get_safe_logger, _safe_logger_instance
        
        # Get logger stats
        if _safe_logger_instance is None:
            await message.answer(
                "⚠️ <b>ML Logger not initialized</b>\n\n"
                "Logger will be initialized on next bot restart.\n"
                "Bot is running normally.",
                parse_mode=ParseMode.HTML
            )
            return
        
        safe_logger = _safe_logger_instance
        stats = safe_logger.get_stats()
        
        # Get DB stats
        db = SessionLocal()
        try:
            result = db.execute(sql_text("""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(DISTINCT sport) as sports_count,
                    COUNT(DISTINCT call_type) as types_count,
                    SUM(CASE WHEN users_clicked > 0 THEN 1 ELSE 0 END) as calls_with_clicks,
                    AVG(roi_percent) as avg_roi,
                    MIN(sent_at) as first_call,
                    MAX(sent_at) as last_call
                FROM arbitrage_calls
            """)).fetchone()
            
            # Handle empty table (result could be None or have None values)
            if result and result[0] is not None:
                db_stats = {
                    'total_calls': result[0] or 0,
                    'sports_count': result[1] or 0,
                    'types_count': result[2] or 0,
                    'calls_with_clicks': result[3] or 0,
                    'avg_roi': round(result[4], 2) if result[4] else 0,
                    'first_call': result[5] if result[5] else 'N/A',
                    'last_call': result[6] if result[6] else 'N/A'
                }
            else:
                # Table is empty
                db_stats = {
                    'total_calls': 0,
                    'sports_count': 0,
                    'types_count': 0,
                    'calls_with_clicks': 0,
                    'avg_roi': 0,
                    'first_call': 'N/A',
                    'last_call': 'N/A'
                }
        finally:
            db.close()
        
        # Build message
        status_emoji = "✅" if stats['enabled'] else "❌"
        error_rate = stats['error_rate']
        health_emoji = "🟢" if error_rate < 5 else "🟡" if error_rate < 20 else "🔴"
        
        text = (
            f"📊 <b>ML CALL LOGGER - STATS</b>\n\n"
            f"{status_emoji} <b>Status:</b> {'Enabled' if stats['enabled'] else 'DISABLED'}\n"
            f"{health_emoji} <b>Health:</b> {100 - error_rate:.1f}%\n\n"
            
            f"📈 <b>LOGGER PERFORMANCE</b>\n"
            f"✅ Success: {stats['success_count']}\n"
            f"❌ Errors: {stats['error_count']}\n"
            f"📊 Error rate: {error_rate:.1f}%\n"
        )
        
        if stats['last_error']:
            text += f"🔴 Last error: {stats['last_error'][:100]}\n"
        
        text += (
            f"\n💾 <b>DATABASE STATS</b>\n"
            f"📞 Total calls logged: {db_stats['total_calls']}\n"
            f"🏀 Sports covered: {db_stats['sports_count']}\n"
            f"📋 Call types: {db_stats['types_count']}\n"
            f"👆 Calls with clicks: {db_stats['calls_with_clicks']}\n"
            f"💰 Average ROI: {db_stats['avg_roi']}%\n\n"
        )
        
        if db_stats['first_call'] != 'N/A':
            text += (
                f"📅 <b>TIMELINE</b>\n"
                f"🥇 First call: {db_stats['first_call'][:19]}\n"
                f"🕐 Last call: {db_stats['last_call'][:19]}\n\n"
            )
        
        # Recommendations
        if error_rate > 20:
            text += (
                f"⚠️ <b>WARNING:</b> High error rate!\n"
                f"Check ML_TROUBLESHOOTING.md\n\n"
            )
        elif error_rate > 5:
            text += (
                f"💡 <b>TIP:</b> Monitor errors\n"
                f"Some logging issues detected\n\n"
            )
        else:
            text += f"✅ <b>ALL SYSTEMS NOMINAL</b>\n\n"
        
        text += (
            f"📋 <b>QUICK ACTIONS</b>\n"
            f"• /ml_test - Test logging\n"
            f"• Check ML_TROUBLESHOOTING.md for issues"
        )
        
        await message.answer(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Error getting ML stats</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Check ML_TROUBLESHOOTING.md",
            parse_mode=ParseMode.HTML
        )


@router.message(Command("ml_test"))
async def cmd_ml_test(message: types.Message):
    """Test ML logging with a fake call"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin only command")
        return
    
    try:
        from utils.safe_call_logger import _safe_logger_instance
        from datetime import datetime
        
        if _safe_logger_instance is None:
            await message.answer(
                "⚠️ <b>ML Logger not initialized</b>\n\n"
                "Logger will be initialized on next bot restart.\n"
                "Bot is running normally.",
                parse_mode=ParseMode.HTML
            )
            return
        
        safe_logger = _safe_logger_instance
        
        # Log test call
        success = await safe_logger.log_call_safe(
            call_type='arbitrage',
            sport='TEST',
            team_a='Test Team A',
            team_b='Test Team B',
            book_a='TestBook1',
            book_b='TestBook2',
            odds_a=-110,
            odds_b=+105,
            roi_percent=2.5,
            stake_a=100,
            stake_b=100,
            users_notified=1
        )
        
        if success:
            await message.answer(
                "✅ <b>ML LOGGING TEST - SUCCESS</b>\n\n"
                "Test call logged successfully!\n\n"
                "Check database:\n"
                "<code>SELECT * FROM arbitrage_calls WHERE sport='TEST';</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                "❌ <b>ML LOGGING TEST - FAILED</b>\n\n"
                "Could not log test call\n\n"
                "Check ML_TROUBLESHOOTING.md",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        await message.answer(
            f"❌ <b>ML TEST ERROR</b>\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.HTML
        )
