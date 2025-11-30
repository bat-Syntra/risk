"""
ArbitrageBot Canada - Version Simplifiée
Tu forward manuellement les messages de Nonoriribot à ce bot
"""
import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI, Request
import uvicorn

# Import handlers
from bot import handlers, admin_handlers

# Import core modules
from core.parser import ArbitrageParser
from core.calculator import ArbitrageCalculator
from core.tiers import TierManager, TierLevel
from core.casinos import get_casino, get_casino_logo, get_casino_referral_link

# Import existing utils
from config import BOT_TOKEN, ADMIN_CHAT_ID

# Database
from database import SessionLocal, init_db
from models.user import User

# Initialize
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# Include routers
dp.include_router(handlers.router)
dp.include_router(admin_handlers.router)

# Parser
parser = ArbitrageParser()


async def send_alert_to_users(arb_data: dict):
    """
    Send arbitrage alert to all eligible users based on their tier
    """
    db = SessionLocal()
    
    try:
        # Get all active users
        users = db.query(User).filter(
            User.is_active == True,
            User.is_banned == False,
            User.notifications_enabled == True
        ).all()
        
        for user in users:
            # Check if user can view this alert
            if not TierManager.can_view_alert(user.tier, arb_data['arb_percentage']):
                continue
            
            # Check daily alert limit
            features = TierManager.get_features(user.tier)
            max_alerts = features.get('max_alerts_per_day', 5)
            
            if not user.can_receive_alert_today(max_alerts):
                continue
            
            # Apply delay for FREE tier
            delay = TierManager.get_alert_delay(user.tier)
            
            if delay > 0:
                # Schedule delayed send
                asyncio.create_task(
                    send_delayed_alert(user.telegram_id, user.tier, arb_data, delay)
                )
            else:
                # Send immediately
                await send_alert_to_user(user.telegram_id, user.tier, arb_data)
            
            # Increment alert count
            user.increment_alert_count()
        
        db.commit()
    
    finally:
        db.close()


async def send_delayed_alert(user_id: int, tier: TierLevel, arb_data: dict, delay_minutes: int):
    """Send alert after delay"""
    await asyncio.sleep(delay_minutes * 60)
    await send_alert_to_user(user_id, tier, arb_data)


async def send_alert_to_user(user_id: int, tier: TierLevel, arb_data: dict):
    """Send formatted arbitrage alert to a user"""
    calculator = ArbitrageCalculator()
    
    # Get user's default bankroll
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        bankroll = user.default_bankroll if user else 400.0
    finally:
        db.close()
    
    # Extract odds
    odds_list = [outcome['odds'] for outcome in arb_data['outcomes']]
    
    # Calculate SAFE mode
    safe_calc = calculator.calculate_safe_stakes(bankroll, odds_list)
    
    if not safe_calc.get('has_arbitrage'):
        return  # Skip if no arbitrage
    
    # Build message
    message_text = (
        f"🚨 <b>ARBITRAGE ALERT - {arb_data['arb_percentage']}%</b> 🚨\n\n"
        f"🏟️ <b>{arb_data['match']}</b>\n"
        f"⚽ {arb_data['league']} - {arb_data['market']}\n\n"
        f"💰 <b>Bankroll: ${bankroll}</b>\n"
        f"✅ <b>Profit Garanti: ${safe_calc['profit']:.2f}</b>\n\n"
    )
    
    # Add each outcome
    for i, outcome_data in enumerate(arb_data['outcomes']):
        casino_name = outcome_data['casino']
        logo = get_casino_logo(casino_name)
        odds = outcome_data['odds']
        odds_str = f"+{odds}" if odds > 0 else str(odds)
        stake = safe_calc['stakes'][i]
        return_amount = safe_calc['returns'][i]
        
        message_text += (
            f"{logo} <b>[{casino_name}]</b> {outcome_data['outcome']} @ {odds_str}\n"
            f"💵 Miser: <code>${stake:.2f}</code> → Retour: ${return_amount:.2f}\n\n"
        )
    
    # Build inline keyboard
    keyboard = []
    
    # Casino referral links (BRONZE+)
    features = TierManager.get_features(tier)
    if features.get('referral_links'):
        casino_buttons = []
        for outcome_data in arb_data['outcomes']:
            casino_name = outcome_data['casino']
            logo = get_casino_logo(casino_name)
            referral_link = get_casino_referral_link(casino_name)
            
            if referral_link:
                casino_buttons.append(
                    InlineKeyboardButton(
                        text=f"{logo} {casino_name}",
                        url=referral_link
                    )
                )
        
        if casino_buttons:
            keyboard.append(casino_buttons)
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to send alert to {user_id}: {e}")


# ===== HANDLER POUR MESSAGES FORWARDÉS =====

@dp.message(F.forward_from)
async def handle_forwarded_message(message: Message):
    """
    Handler pour les messages forwardés
    Si tu forward un message de Nonoriribot, le bot le parse et distribue
    """
    # Seulement si c'est toi qui forward
    if message.from_user.id != int(ADMIN_CHAT_ID):
        return
    
    text = message.text or message.caption
    if not text:
        return
    
    print(f"\n📨 Message forwardé reçu")
    print(f"{'='*60}")
    print(text[:200] + "..." if len(text) > 200 else text)
    print(f"{'='*60}")
    
    # Parse le message
    parsed = parser.parse(text)
    
    if parsed:
        print(f"✅ Message parsé:")
        print(f"   Arbitrage: {parsed['arb_percentage']}%")
        print(f"   Match: {parsed['match']}")
        print(f"   Outcomes: {len(parsed['outcomes'])}")
        
        # Distribuer aux users
        await send_alert_to_users(parsed)
        
        # Confirmation à toi
        await message.reply(
            f"✅ Alerte distribuée!\n"
            f"📊 {parsed['arb_percentage']}% - {parsed['match']}",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply("⚠️ Message non parsé (pas une alerte d'arbitrage?)")


# ===== FastAPI Endpoints (optionnel) =====

@app.post("/public/drop")
async def receive_drop(req: Request):
    """Receive arbitrage drop from external source"""
    d = await req.json()
    eid = d.get("event_id")
    if not eid:
        return {"ok": False, "error": "missing event_id"}
    
    # Send to users
    await send_alert_to_users(d)
    
    return {"ok": True}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ===== Startup =====

async def on_startup():
    """Initialize database on startup"""
    print("🚀 Initializing database...")
    init_db()
    print("✅ Database initialized")


async def runner():
    """Main runner"""
    print("✅ ArbitrageBot Canada - Version Simplifiée")
    print("📨 Forward les messages de Nonoriribot directement au bot!")
    
    # Initialize DB
    await on_startup()
    
    async def serve():
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    # Run both FastAPI and Telegram bot
    await asyncio.gather(
        serve(),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    asyncio.run(runner())
