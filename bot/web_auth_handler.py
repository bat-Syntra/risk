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

WEB_API_URL = "https://smartrisk0.xyz/api/auth/check"

@router.message(Command("start"))
async def cmd_start_with_auth(message: types.Message):
    """Handle /start command with auth code"""
    logger.info(f"🔍 /start received from user {message.from_user.id}")
    
    args = message.text.split()
    
    # Check if auth code is provided (web login)
    if len(args) > 1 and args[1].startswith("auth_"):
        # Generate a unique session token
        import base64
        import json
        import hashlib
        import time
        
        timestamp = int(time.time())
        session_id = hashlib.sha256(f"{message.from_user.id}_{timestamp}".encode()).hexdigest()[:16]
        
        token_data = {
            "tid": message.from_user.id,
            "user": message.from_user.username or f"User{message.from_user.id}",
            "ts": timestamp,
            "sid": session_id  # Unique session ID
        }
        token = base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()
        
        # Save session to database (invalidates previous sessions)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
            if user:
                user.web_session_id = session_id  # Only this session is valid now
                db.commit()
        finally:
            db.close()
        
        # Send direct link to dashboard
        dashboard_url = f"https://smartrisk0.xyz/auth/callback?token={token}"
        
        await message.reply(
            "✅ <b>Authentication Successful!</b>\n\n"
            f"👉 <a href='{dashboard_url}'>Click here to open Dashboard</a>\n\n"
            "<i>Or copy this link:</i>\n"
            f"<code>{dashboard_url}</code>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return
    
    # Normal start command
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
                "https://smartrisk0.xyz\n\n"
                "Utilise /help pour voir toutes les commandes."
            )
        else:
            text = (
                "🎯 <b>Welcome to Risk0!</b>\n\n"
                "I'm your arbitrage alerts assistant.\n\n"
                "📱 <b>Connect to Dashboard:</b>\n"
                "https://smartrisk0.xyz\n\n"
                "Use /help to see all commands."
            )
        
        await message.reply(text, parse_mode=ParseMode.HTML)
    finally:
        db.close()
