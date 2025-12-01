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
from models.user import User, TierLevel

logger = logging.getLogger(__name__)
router = Router()

WEB_API_URL = "https://smartrisk0.xyz/api/auth/check"

from aiogram.filters import CommandStart

@router.message(CommandStart(deep_link=True))
async def cmd_start_with_auth(message: types.Message):
    """Handle /start command with auth code ONLY"""
    args = message.text.split()
    
    # Only handle if auth code is provided (web login)
    if len(args) <= 1 or not args[1].startswith("auth_"):
        return  # Let handlers.py handle normal /start
    
    # Extract the auth code (remove "auth_" prefix)
    auth_code = args[1].replace("auth_", "")
    logger.info(f"🔍 Web auth /start received from user {message.from_user.id} with code {auth_code}")
    
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
    
    # Check if user is ALPHA tier or admin
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.reply(
                "❌ <b>Access Denied</b>\n\n"
                "You need to be a registered user first.\n"
                "Use /start in the bot to register.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Only PREMIUM tier, free_access, or admin can access web dashboard
        is_admin = message.from_user.id in [6029059837, 8213628656, 8004919557]  # Admin IDs
        is_premium = user.tier == TierLevel.PREMIUM or user.free_access
        
        if not is_admin and not is_premium:
            await message.reply(
                "❌ <b>ALPHA Access Required</b>\n\n"
                "🔒 The web dashboard is exclusively available for <b>ALPHA</b> members.\n\n"
                "💎 Upgrade to ALPHA to unlock:\n"
                "• Full web dashboard access\n"
                "• Real-time alerts\n"
                "• Advanced analytics\n"
                "• Priority support\n\n"
                "Use /subscribe to upgrade!",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Save session (invalidates previous sessions)
        user.web_session_id = session_id  # Only this session is valid now
        db.commit()
    finally:
        db.close()
    
    # Notify web API for polling to work (browser auto-redirect)
    await authenticate_user(
        message.from_user.id,
        message.from_user.username,
        auth_code
    )
    
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

