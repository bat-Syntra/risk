"""
Book Health Cron Jobs
Automated tasks for score calculation and alerts
"""
import logging
import asyncio
from datetime import datetime, timedelta, date
from aiogram import Bot

from database import SessionLocal
from bot.book_health_scoring import BookHealthScoring
from bot.book_health_tracking import bet_tracker
from sqlalchemy import text as sql_text

logger = logging.getLogger(__name__)


class BookHealthCronJobs:
    """Automated tasks for Book Health system"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scorer = BookHealthScoring()
    
    async def daily_score_calculation(self):
        """Calculate scores for all active users (runs at 2 AM)"""
        logger.info("🏥 Running daily Book Health score calculation...")
        
        db = SessionLocal()
        try:
            # Get all active users with profiles
            profiles = db.execute(sql_text("""
                SELECT DISTINCT user_id, casino
                FROM user_casino_profiles
                WHERE is_limited = false
            """)).fetchall()
            
            calculated = 0
            alerts_sent = 0
            
            for profile in profiles:
                try:
                    # Calculate score
                    score_data = self.scorer.calculate_health_score(
                        profile.user_id, 
                        profile.casino
                    )
                    
                    # Skip if insufficient data
                    if score_data['risk_level'] in ['NO_PROFILE', 'INSUFFICIENT_DATA']:
                        continue
                    
                    calculated += 1
                    
                    # Check for critical scores
                    if score_data['risk_level'] in ['CRITICAL', 'HIGH_RISK']:
                        await self.send_critical_alert(
                            profile.user_id,
                            profile.casino,
                            score_data
                        )
                        alerts_sent += 1
                    
                except Exception as e:
                    logger.error(f"Error calculating score for {profile.user_id} @ {profile.casino}: {e}")
            
            logger.info(f"✅ Calculated {calculated} scores, sent {alerts_sent} alerts")
            
        finally:
            db.close()
    
    async def update_bet_results(self):
        """Update bet results from completed games (runs every 6 hours)"""
        logger.info("🔄 Updating bet results...")
        
        db = SessionLocal()
        try:
            # Get pending bets that have results
            pending = db.execute(sql_text("""
                SELECT ba.analytics_id, ba.bet_id, ba.stake_amount, ba.odds_at_bet
                FROM bet_analytics ba
                WHERE ba.result IS NULL
                  AND ba.bet_placed_at < :cutoff
            """), {
                "cutoff": datetime.utcnow() - timedelta(hours=4)  # Games should be done after 4 hours
            }).fetchall()
            
            updated = 0
            
            for bet in pending:
                # Check if we have result from main bet table
                bet_result = db.execute(sql_text("""
                    SELECT status FROM user_bets
                    WHERE bet_id = :bet_id
                """), {"bet_id": bet.bet_id}).first()
                
                if bet_result and bet_result.status in ['won', 'lost', 'push', 'void']:
                    # Calculate profit/loss
                    if bet_result.status == 'won':
                        profit = float(bet.stake_amount) * (float(bet.odds_at_bet) - 1)
                    elif bet_result.status == 'lost':
                        profit = -float(bet.stake_amount)
                    else:
                        profit = 0
                    
                    # Update bet_analytics
                    db.execute(sql_text("""
                        UPDATE bet_analytics
                        SET result = :result,
                            profit_loss = :profit
                        WHERE analytics_id = :id
                    """), {
                        "id": bet.analytics_id,
                        "result": bet_result.status,
                        "profit": profit
                    })
                    
                    updated += 1
            
            db.commit()
            logger.info(f"✅ Updated {updated} bet results")
            
        finally:
            db.close()
    
    async def weekly_report(self):
        """Send weekly Book Health reports (runs Sunday 3 AM)"""
        logger.info("📊 Generating weekly Book Health reports...")
        
        db = SessionLocal()
        try:
            # Get all users with profiles
            users = db.execute(sql_text("""
                SELECT DISTINCT user_id FROM user_casino_profiles
            """)).fetchall()
            
            sent = 0
            
            for user in users:
                try:
                    await self.send_weekly_report(user.user_id)
                    sent += 1
                except Exception as e:
                    logger.error(f"Error sending report to {user.user_id}: {e}")
            
            logger.info(f"✅ Sent {sent} weekly reports")
            
        finally:
            db.close()
    
    async def send_critical_alert(self, user_id: str, casino: str, score_data: dict):
        """Send alert for critical scores"""
        try:
            # Get user's Telegram ID
            db = SessionLocal()
            user = db.execute(sql_text("""
                SELECT telegram_id FROM users
                WHERE telegram_id = :user_id
            """), {"user_id": int(user_id)}).first()
            db.close()
            
            if not user:
                return
            
            emoji = '⛔' if score_data['risk_level'] == 'CRITICAL' else '🔴'
            
            text = f"""
{emoji} <b>ALERTE BOOK HEALTH</b>

🏢 Casino: <b>{casino}</b>
📊 Score: <b>{score_data['score']:.0f}/100</b>
🚨 Statut: <b>{score_data['risk_level']}</b>

⏳ Limite estimée: {self._format_estimate(score_data.get('estimated_months'))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔴 ACTIONS URGENTES:</b>
"""
            
            # Add top recommendations
            recommendations = score_data.get('recommendations', [])
            for rec in recommendations[:3]:
                if rec['priority'] in ['CRITICAL', 'HIGH']:
                    text += f"\n• {rec['text']}\n"
            
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Clique pour voir détails complets</i>
"""
            
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Voir Détails", callback_data=f"health_details_{casino}")],
                [InlineKeyboardButton(text="✅ J'ai compris", callback_data="alert_acknowledged")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error sending critical alert: {e}")
    
    async def send_weekly_report(self, user_id: str):
        """Send weekly report to user"""
        try:
            # Get all casinos for user
            db = SessionLocal()
            profiles = db.execute(sql_text("""
                SELECT casino, is_limited FROM user_casino_profiles
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchall()
            
            if not profiles:
                db.close()
                return
            
            # Get user's Telegram ID
            user = db.execute(sql_text("""
                SELECT telegram_id FROM users
                WHERE telegram_id = :user_id
            """), {"user_id": int(user_id)}).first()
            
            if not user:
                db.close()
                return
            
            text = """
📊 <b>RAPPORT HEBDOMADAIRE - BOOK HEALTH</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            
            has_data = False
            
            for profile in profiles:
                if profile.is_limited:
                    continue
                
                # Get latest score
                score = db.execute(sql_text("""
                    SELECT total_score, risk_level, score_change_7d
                    FROM book_health_scores
                    WHERE user_id = :user_id AND casino = :casino
                    ORDER BY calculation_date DESC
                    LIMIT 1
                """), {"user_id": user_id, "casino": profile.casino}).first()
                
                if score:
                    has_data = True
                    emoji = self._get_risk_emoji(score.risk_level)
                    trend = self._get_trend_arrow(score.score_change_7d)
                    
                    text += f"""
🏢 <b>{profile.casino}</b>
Score: {score.total_score:.0f}/100 {emoji}
Tendance: {trend} {self._format_change(score.score_change_7d)}

"""
            
            db.close()
            
            if not has_data:
                return
            
            text += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Continue à tracker tes paris pour des prédictions plus précises!</i>
"""
            
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Voir Dashboard", callback_data="book_health_dashboard")]
            ])
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error sending weekly report: {e}")
    
    def _format_estimate(self, months):
        if months is None:
            return 'N/A'
        if months < 1:
            return 'Quelques semaines'
        if months < 2:
            return '1-2 mois'
        if months < 6:
            return f'{months:.0f} mois'
        if months < 12:
            return f'{months:.0f} mois'
        if months < 24:
            return '1-2 ans'
        return '2+ ans'
    
    def _get_risk_emoji(self, risk_level):
        return {
            'SAFE': '🟢',
            'MONITOR': '🟡',
            'WARNING': '🟠',
            'HIGH_RISK': '🔴',
            'CRITICAL': '⛔'
        }.get(risk_level, '❓')
    
    def _get_trend_arrow(self, change):
        if change is None:
            return ''
        if abs(change) < 2:
            return '→'
        if change > 0:
            return '↗️'
        return '↘️'
    
    def _format_change(self, change):
        if change is None:
            return ''
        sign = '+' if change > 0 else ''
        return f"{sign}{change:.0f}"


# Task scheduling functions
async def schedule_book_health_tasks(bot: Bot):
    """Schedule all Book Health cron jobs"""
    cron = BookHealthCronJobs(bot)
    
    while True:
        now = datetime.now()
        
        # Daily score calculation at 2 AM
        if now.hour == 2 and now.minute == 0:
            asyncio.create_task(cron.daily_score_calculation())
            await asyncio.sleep(60)  # Wait a minute to avoid duplicate
        
        # Update bet results every 6 hours
        if now.hour % 6 == 0 and now.minute == 0:
            asyncio.create_task(cron.update_bet_results())
            await asyncio.sleep(60)
        
        # Weekly report on Sunday at 3 AM
        if now.weekday() == 6 and now.hour == 3 and now.minute == 0:
            asyncio.create_task(cron.weekly_report())
            await asyncio.sleep(60)
        
        # Sleep for 30 seconds before checking again
        await asyncio.sleep(30)
