"""
Bonus Marketing Campaign - Automated daily messages for users with active bonus
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import DATABASE_URL
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class BonusMarketingCampaign:
    """Send daily marketing messages to users with active bonus"""
    
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.engine = create_engine(DATABASE_URL)
    
    async def get_users_with_active_bonus(self):
        """Get all users with active bonus who haven't redeemed yet"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    bt.telegram_id,
                    bt.bonus_activated_at,
                    bt.bonus_expires_at,
                    bt.campaign_messages_sent,
                    bt.last_campaign_message_at,
                    u.language
                FROM bonus_tracking bt
                JOIN users u ON bt.telegram_id = u.telegram_id
                WHERE bt.bonus_activated_at IS NOT NULL
                    AND bt.bonus_redeemed = 0
                    AND bt.bonus_expires_at > :now
                ORDER BY bt.bonus_expires_at ASC
            """), {'now': datetime.now()})
            
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def should_send_campaign(self, user_data: dict) -> bool:
        """Determine if we should send a campaign message to this user"""
        last_sent = user_data.get('last_campaign_message_at')
        
        # Never sent - send first message after 1 day of activation
        if not last_sent:
            activation_date = user_data['bonus_activated_at']
            if isinstance(activation_date, str):
                activation_date = datetime.fromisoformat(activation_date)
            hours_since_activation = (datetime.now() - activation_date).total_seconds() / 3600
            return hours_since_activation >= 24
        
        # Already sent - send once per day maximum
        if isinstance(last_sent, str):
            last_sent = datetime.fromisoformat(last_sent)
        hours_since_last = (datetime.now() - last_sent).total_seconds() / 3600
        return hours_since_last >= 24
    
    def get_campaign_message(self, user_data: dict, message_number: int) -> tuple:
        """Get campaign message based on user data and message number"""
        lang = user_data.get('language', 'en')
        expires_at = user_data['bonus_expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        days_left = (expires_at - datetime.now()).days
        hours_left = ((expires_at - datetime.now()).seconds // 3600)
        
        # Message rotation (7 different messages for 7 days)
        if lang == 'fr':
            messages = [
                # Day 1
                (
                    "🎁 <b>RAPPEL: Ton bonus de $50 est actif!</b>\n\n"
                    f"⏰ Expire dans <b>{days_left} jours</b>\n\n"
                    "Ne laisse pas passer cette occasion!\n\n"
                    "<s>$200</s> <b>$150 CAD/mois</b>\n"
                    "Premier mois seulement 💰\n\n"
                    "Clique ci-dessous pour upgrader maintenant! 👇"
                ),
                # Day 2
                (
                    "💡 <b>Tu savais que...</b>\n\n"
                    "Les membres ALPHA font en moyenne $3,500-7,000/mois?\n\n"
                    f"⏰ Ton bonus expire dans <b>{days_left} jours</b>\n\n"
                    "Économise $50 sur ton premier mois:\n"
                    "<s>$200</s> <b>$150 CAD</b>\n\n"
                    "C'est un retour de 20x sur investissement! 🚀"
                ),
                # Day 3
                (
                    "🔥 <b>PLUS QUE QUELQUES JOURS!</b>\n\n"
                    f"⏰ Ton bonus expire dans <b>{days_left} jours</b>\n\n"
                    "Ce que tu manques en restant GRATUIT:\n"
                    "• Calls illimités (vs 5/jour)\n"
                    "• Parlays optimisés (Beta)\n"
                    "• Middle Bets + Good Odds\n"
                    "• $200-300/jour en profit potentiel\n\n"
                    "Économise $50 maintenant! 💰"
                ),
                # Day 4
                (
                    "⚠️ <b>ATTENTION!</b>\n\n"
                    f"Ton bonus de $50 expire dans <b>{days_left} jours</b>!\n\n"
                    "Chaque jour que tu attends = $100-300 de profit manqué\n\n"
                    "<s>$200</s> <b>$150 CAD/mois</b>\n\n"
                    "Ne laisse pas cette opportunité s'envoler! ⏰"
                ),
                # Day 5
                (
                    "🎯 <b>DERNIÈRE CHANCE!</b>\n\n"
                    f"⏰ <b>Expire dans {days_left} jours {hours_left}h</b>\n\n"
                    "Le rabais de $50 sur ALPHA\n"
                    "ne sera plus disponible après!\n\n"
                    "Rejoins les membres qui font\n"
                    "$3,500-7,000/mois 💰\n\n"
                    "Clique maintenant! 👇"
                ),
                # Day 6
                (
                    "⏰ <b>URGENT - EXPIRE DEMAIN!</b>\n\n"
                    f"Il te reste <b>{hours_left} heures</b>\n"
                    "pour profiter de ton bonus de $50!\n\n"
                    "<s>$200</s> <b>$150 CAD/mois</b>\n\n"
                    "Après demain, tu paies plein prix.\n\n"
                    "Ne manque pas cette chance! 🚨"
                ),
                # Day 7 (last day)
                (
                    "🚨 <b>DERNIÈRES HEURES!</b>\n\n"
                    f"⏰ Ton bonus expire dans <b>{hours_left}h</b>!\n\n"
                    "C'est ta DERNIÈRE CHANCE\n"
                    "d'économiser $50 sur ALPHA!\n\n"
                    "Après aujourd'hui = plein prix ($200/mois)\n\n"
                    "AGIS MAINTENANT! ⚡"
                )
            ]
        else:
            messages = [
                # Day 1
                (
                    "🎁 <b>REMINDER: Your $50 bonus is active!</b>\n\n"
                    f"⏰ Expires in <b>{days_left} days</b>\n\n"
                    "Don't let this opportunity slip away!\n\n"
                    "<s>$200</s> <b>$150 CAD/month</b>\n"
                    "First month only 💰\n\n"
                    "Click below to upgrade now! 👇"
                ),
                # Day 2
                (
                    "💡 <b>Did you know...</b>\n\n"
                    "ALPHA members make an average of $3,500-7,000/month?\n\n"
                    f"⏰ Your bonus expires in <b>{days_left} days</b>\n\n"
                    "Save $50 on your first month:\n"
                    "<s>$200</s> <b>$150 CAD</b>\n\n"
                    "That's a 20x return on investment! 🚀"
                ),
                # Day 3
                (
                    "🔥 <b>ONLY A FEW DAYS LEFT!</b>\n\n"
                    f"⏰ Your bonus expires in <b>{days_left} days</b>\n\n"
                    "What you're missing by staying FREE:\n"
                    "• Unlimited calls (vs 5/day)\n"
                    "• Optimized Parlays (Beta)\n"
                    "• Middle Bets + Good Odds\n"
                    "• $200-300/day potential profit\n\n"
                    "Save $50 now! 💰"
                ),
                # Day 4
                (
                    "⚠️ <b>WARNING!</b>\n\n"
                    f"Your $50 bonus expires in <b>{days_left} days</b>!\n\n"
                    "Every day you wait = $100-300 in missed profit\n\n"
                    "<s>$200</s> <b>$150 CAD/month</b>\n\n"
                    "Don't let this opportunity fly away! ⏰"
                ),
                # Day 5
                (
                    "🎯 <b>LAST CHANCE!</b>\n\n"
                    f"⏰ <b>Expires in {days_left} days {hours_left}h</b>\n\n"
                    "The $50 discount on ALPHA\n"
                    "won't be available after!\n\n"
                    "Join members making\n"
                    "$3,500-7,000/month 💰\n\n"
                    "Click now! 👇"
                ),
                # Day 6
                (
                    "⏰ <b>URGENT - EXPIRES TOMORROW!</b>\n\n"
                    f"You have <b>{hours_left} hours left</b>\n"
                    "to use your $50 bonus!\n\n"
                    "<s>$200</s> <b>$150 CAD/month</b>\n\n"
                    "After tomorrow, you pay full price.\n\n"
                    "Don't miss this chance! 🚨"
                ),
                # Day 7 (last day)
                (
                    "🚨 <b>FINAL HOURS!</b>\n\n"
                    f"⏰ Your bonus expires in <b>{hours_left}h</b>!\n\n"
                    "This is your LAST CHANCE\n"
                    "to save $50 on ALPHA!\n\n"
                    "After today = full price ($200/month)\n\n"
                    "ACT NOW! ⚡"
                )
            ]
        
        # Get the appropriate message based on number of messages sent
        message_index = min(message_number, len(messages) - 1)
        text = messages[message_index]
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Acheter ALPHA ($150)" if lang == 'fr' else "🚀 Buy ALPHA ($150)",
                callback_data="upgrade_premium"
            )],
            [InlineKeyboardButton(
                text="❌ Ne plus recevoir" if lang == 'fr' else "❌ Stop receiving",
                callback_data="bonus_unsubscribe"
            )]
        ])
        
        return text, keyboard
    
    async def send_campaign_message(self, user_data: dict):
        """Send marketing campaign message to user"""
        telegram_id = user_data['telegram_id']
        message_number = user_data.get('campaign_messages_sent', 0)
        
        try:
            text, keyboard = self.get_campaign_message(user_data, message_number)
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            # Update database
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE bonus_tracking
                    SET campaign_messages_sent = campaign_messages_sent + 1,
                        last_campaign_message_at = :now,
                        updated_at = :now
                    WHERE telegram_id = :tid
                """), {
                    'tid': telegram_id,
                    'now': datetime.now()
                })
                conn.commit()
            
            logger.info(f"✅ Campaign message #{message_number + 1} sent to user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending campaign to {telegram_id}: {e}")
            return False
    
    async def run_daily_campaign(self):
        """Run daily marketing campaign for all eligible users"""
        logger.info("🚀 Starting daily bonus marketing campaign...")
        
        users = await self.get_users_with_active_bonus()
        logger.info(f"Found {len(users)} users with active bonus")
        
        sent_count = 0
        for user_data in users:
            if await self.should_send_campaign(user_data):
                await self.send_campaign_message(user_data)
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
        
        logger.info(f"✅ Campaign completed! Sent {sent_count} messages")
        await self.bot.session.close()
    
    def close(self):
        """Close connections"""
        self.engine.dispose()


async def main():
    """Run the campaign"""
    campaign = BonusMarketingCampaign()
    try:
        await campaign.run_daily_campaign()
    finally:
        campaign.close()


if __name__ == "__main__":
    asyncio.run(main())
