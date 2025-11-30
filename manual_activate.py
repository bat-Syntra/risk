#!/usr/bin/env python3
"""
Manual activation script for testing payment system
Activates user to PREMIUM and sends welcome message
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from aiogram import Bot
from aiogram.enums import ParseMode

load_dotenv()

# Direct DB connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///arbitrage_bot.db")
engine = create_engine(DATABASE_URL)

async def activate_user(telegram_id: int):
    """Manually activate user to PREMIUM"""
    bot_token = os.getenv("BOT_TOKEN")
    admin_id = os.getenv("ADMIN_CHAT_ID")
    
    try:
        with engine.connect() as conn:
            # Get user
            result = conn.execute(
                text("SELECT username, language FROM users WHERE telegram_id = :tid"),
                {"tid": telegram_id}
            ).fetchone()
            
            if not result:
                print(f"❌ User {telegram_id} not found!")
                return False
            
            username = result[0] or "Member"
            lang = result[1] or "en"
            
            # Activate to PREMIUM
            sub_start = datetime.now()
            sub_end = sub_start + timedelta(days=30)
            
            conn.execute(
                text("""
                    UPDATE users 
                    SET tier = 'PREMIUM',
                        subscription_start = :start,
                        subscription_end = :end
                    WHERE telegram_id = :tid
                """),
                {"tid": telegram_id, "start": sub_start, "end": sub_end}
            )
            conn.commit()
            
            print(f"✅ User {telegram_id} activated to PREMIUM!")
            print(f"   Expires: {sub_end.strftime('%Y-%m-%d')}")
        
        # Send welcome message to user
        bot = Bot(token=bot_token)
        
        welcome_text = (
            "🎉 <b>Bienvenue en PREMIUM!</b>\n\n"
            "Ton accès est actif pendant <b>30 jours</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>TU AS MAINTENANT ACCÈS À:</b>\n\n"
            "✅ Good Odds (+EV garanti)\n"
            "✅ Middle Bets (loterie)\n"
            "✅ Optimized Parlays\n"
            "✅ Guides complets\n"
            "✅ Support prioritaire\n"
            "✅ Stats avancées\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>IMPORTANT:</b>\n"
            "Lis le guide /learn pour maximiser tes profits!\n\n"
            "💰 Ton ROI commence maintenant! 🚀"
        ) if lang == "fr" else (
            "🎉 <b>Welcome to PREMIUM!</b>\n\n"
            "Your access is active for <b>30 days</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>YOU NOW HAVE ACCESS TO:</b>\n\n"
            "✅ Good Odds (guaranteed +EV)\n"
            "✅ Middle Bets (lottery)\n"
            "✅ Optimized Parlays\n"
            "✅ Complete guides\n"
            "✅ Priority support\n"
            "✅ Advanced stats\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>IMPORTANT:</b>\n"
            "Read the /learn guide to maximize your profits!\n\n"
            "💰 Your ROI starts now! 🚀"
        )
        
        await bot.send_message(telegram_id, welcome_text, parse_mode=ParseMode.HTML)
        print(f"✅ Welcome message sent to user!")
        
        # Notify admin
        if admin_id:
            admin_text = (
                "🎉 <b>NOUVEAU MEMBRE ALPHA!</b>\n\n"
                f"👤 User: @{username}\n"
                f"🆔 ID: <code>{telegram_id}</code>\n"
                f"📅 Expire: {user.subscription_end.strftime('%Y-%m-%d')}\n\n"
                f"💰 Paiement reçu via NOWPayments ✅\n"
                f"🔥 Membre activé manuellement (test)"
            )
            await bot.send_message(int(admin_id), admin_text, parse_mode=ParseMode.HTML)
            print(f"✅ Admin notification sent!")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Activate test account
    telegram_id = 8004919557
    print(f"🚀 Activating user {telegram_id}...")
    asyncio.run(activate_user(telegram_id))
