"""
Web Authentication Handler for Risk0 Bot
Handles authentication requests from the web dashboard
"""
import re
import aiohttp
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from database import SessionLocal
from models.user import User

logger = logging.getLogger(__name__)
router = Router()

WEB_API_URL = "https://risk-web-pearl.vercel.app/api/auth/check"

@router.message(Command("start"))
async def cmd_start_with_auth(message: types.Message):
    """Handle /start command with auth code"""
    logger.info(f"🔍 /start received from user {message.from_user.id}")
    logger.info(f"🔍 Full message text: {message.text}")
    
    args = message.text.split()
    logger.info(f"🔍 Args: {args}")
    
    # Check if auth code is provided
    if len(args) > 1 and args[1].startswith("auth_"):
        auth_code = args[1].replace("auth_", "")
        logger.info(f"🔑 Auth code detected: {auth_code}")
        
        # Authenticate the user
        logger.info(f"🌐 Calling web API to authenticate user {message.from_user.id}")
        await authenticate_user(message.from_user.id, message.from_user.username, auth_code)
        
        # Send success message
        await message.reply(
            "✅ <b>Authentication Successful!</b>\n\n"
            "You're now connected to the Risk0 Dashboard.\n"
            "You can close this chat and return to the web app.",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"✅ Auth success message sent to {message.from_user.id}")
        return
    
    # Normal start command
    logger.info(f"📝 Normal /start command, no auth code")
    await handle_normal_start(message)

async def authenticate_user(telegram_id: int, username: str, auth_code: str):
    """Send authentication to web API"""
    try:
        payload = {
            "code": auth_code,
            "telegramId": telegram_id,
            "username": username or f"User{telegram_id}"
        }
        logger.info(f"🌐 Sending POST to {WEB_API_URL}")
        logger.info(f"🌐 Payload: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEB_API_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_text = await response.text()
                logger.info(f"🌐 Response status: {response.status}")
                logger.info(f"🌐 Response body: {response_text}")
                
                if response.status == 200:
                    logger.info(f"✅ User {telegram_id} authenticated successfully")
                else:
                    logger.error(f"❌ Failed to authenticate user {telegram_id}: {response.status} - {response_text}")
    except Exception as e:
        logger.error(f"❌ Error authenticating user: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def handle_normal_start(message: types.Message):
    """Handle normal /start command"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            db.add(user)
            db.commit()
        
        lang = user.language if user else 'en'
        
        if lang == 'fr':
            text = (
                "🎯 <b>Bienvenue sur Risk0!</b>\n\n"
                "Je suis ton assistant pour les alertes d'arbitrage.\n\n"
                "📱 <b>Connecte-toi au Dashboard:</b>\n"
                "https://risk-web-pearl.vercel.app\n\n"
                "Utilise /help pour voir toutes les commandes."
            )
        else:
            text = (
                "🎯 <b>Welcome to Risk0!</b>\n\n"
                "I'm your arbitrage alerts assistant.\n\n"
                "📱 <b>Connect to Dashboard:</b>\n"
                "https://risk-web-pearl.vercel.app\n\n"
                "Use /help to see all commands."
            )
        
        await message.reply(text, parse_mode=ParseMode.HTML)
    finally:
        db.close()
