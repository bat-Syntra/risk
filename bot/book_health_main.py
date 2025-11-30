"""
Book Health Monitor - Main Integration
Complete system integration with bot
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command

# Import all Book Health modules
from bot.book_health_onboarding import router as onboarding_router
from bot.book_health_dashboard import router as dashboard_router
from bot.book_health_scoring import BookHealthScoring
from bot.book_health_tracking import bet_tracker, track_parlay_bet, track_single_bet
from bot.book_health_cron import schedule_book_health_tasks

logger = logging.getLogger(__name__)

# Create main router
router = Router()

# Include sub-routers
router.include_router(onboarding_router)
router.include_router(dashboard_router)


# Integration with I BET button
async def handle_i_bet_with_book_health(
    user_id: str,
    bet_data: dict,
    casino: str,
    bet_type: str = 'plus_ev',
    is_recreational: bool = False
):
    """
    Called when user clicks I BET
    Tracks the bet for Book Health monitoring
    """
    try:
        # Track for Book Health
        result = await bet_tracker.log_bet_placement(
            user_id=str(user_id),
            bet_id=bet_data.get('bet_id'),
            casino=casino,
            bet_type=bet_type,
            sport=bet_data.get('sport'),
            market_type=bet_data.get('market_type'),
            odds=bet_data.get('odds'),
            stake=bet_data.get('stake'),
            is_recreational=is_recreational
        )
        
        # Check if alert needed
        if isinstance(result, dict) and result.get('alert_needed'):
            # Critical score detected
            logger.warning(f"⚠️ Critical Book Health score for {user_id} @ {casino}")
            # Alert will be sent by cron job
        
        return result
        
    except Exception as e:
        logger.error(f"Error tracking bet for Book Health: {e}")
        return False


# Recreational bet feature
@router.callback_query(F.data.startswith("bet_rec_"))
async def handle_recreational_bet(callback: CallbackQuery):
    """Handle recreational bet marking"""
    await callback.answer("✅ Bet marqué comme récréatif")
    
    # Extract parlay/bet ID
    bet_id = callback.data.replace("bet_rec_", "")
    
    # Mark as recreational
    await bet_tracker.mark_as_recreational(bet_id)
    
    # Log message
    logger.info(f"🎲 Recreational bet: {bet_id}")


@router.callback_query(F.data.startswith("bet_sharp_"))
async def handle_sharp_bet(callback: CallbackQuery):
    """Handle sharp bet (normal)"""
    await callback.answer("✅ Bet trackés comme sharp play")
    
    # Extract bet ID
    bet_id = callback.data.replace("bet_sharp_", "")
    
    # Log as sharp (default behavior)
    logger.info(f"📈 Sharp bet: {bet_id}")


# Export functions for external use
__all__ = [
    'router',
    'handle_i_bet_with_book_health',
    'track_parlay_bet',
    'track_single_bet',
    'schedule_book_health_tasks',
    'BookHealthScoring',
    'bet_tracker'
]


# Quick stats command for debugging
@router.message(Command("bookhealth"))
async def cmd_book_health_stats(message):
    """Quick command to check Book Health stats"""
    user_id = str(message.from_user.id)
    
    from database import SessionLocal
    from sqlalchemy import text as sql_text
    
    db = SessionLocal()
    try:
        # Check if user has profiles
        profiles = db.execute(sql_text("""
            SELECT casino FROM user_casino_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()
        
        if not profiles:
            await message.reply(
                "🏥 Tu n'as pas encore configuré Book Health.\n"
                "Va dans /stats → Book Health Monitor pour commencer!"
            )
            return
        
        text = "🏥 <b>BOOK HEALTH - QUICK STATS</b>\n\n"
        
        scorer = BookHealthScoring()
        
        for profile in profiles:
            casino = profile.casino
            
            # Get tracking stats
            stats = await bet_tracker.get_tracking_stats(user_id, casino)
            
            text += f"<b>{casino}:</b>\n"
            text += f"• Bets trackés: {stats['total_bets']}\n"
            
            if stats['total_bets'] >= 10:
                # Calculate score
                score_data = scorer.calculate_health_score(user_id, casino)
                if score_data['risk_level'] not in ['NO_PROFILE', 'INSUFFICIENT_DATA']:
                    text += f"• Score: {score_data['score']:.0f}/100\n"
                    text += f"• Risk: {score_data['risk_level']}\n"
            else:
                text += f"• Score: En attente ({stats['total_bets']}/10 bets)\n"
            
            text += "\n"
        
        await message.reply(text, parse_mode='HTML')
        
    finally:
        db.close()
