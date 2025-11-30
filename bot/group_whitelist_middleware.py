"""
Group Whitelist Middleware - Bot only works in private chats and whitelisted admin group
"""
import os
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

logger = logging.getLogger(__name__)

# Admin group ID from environment (set this in .env as ADMIN_GROUP_ID)
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID", "")


class GroupWhitelistMiddleware(BaseMiddleware):
    """
    Middleware that blocks bot from responding in groups except the whitelisted admin group.
    Bot will work in:
    - Private chats (chat type = 'private')
    - Admin group (if ADMIN_GROUP_ID is set)
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Get message or callback query
        if event.message:
            chat = event.message.chat
        elif event.callback_query and event.callback_query.message:
            chat = event.callback_query.message.chat
        else:
            # No chat to check, allow
            return await handler(event, data)
        
        chat_type = chat.type
        chat_id = chat.id
        
        # Allow private chats
        if chat_type == "private":
            return await handler(event, data)
        
        # Check if this is the admin group
        if ADMIN_GROUP_ID and str(chat_id) == str(ADMIN_GROUP_ID):
            logger.info(f"✅ Admin group message allowed: {chat_id}")
            return await handler(event, data)
        
        # Block all other groups/supergroups/channels
        if chat_type in ["group", "supergroup", "channel"]:
            logger.warning(f"🚫 Blocked message from unauthorized group: {chat_id} ({chat.title})")
            
            # Log the group ID in a clear format for easy configuration
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"📋 GROUP ID TO ADD TO .env:")
            logger.info(f"ADMIN_GROUP_ID={chat_id}")
            logger.info(f"Group Name: {chat.title}")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Optionally send a warning message
            if event.message:
                try:
                    await event.message.answer(
                        "⛔ <b>Groupe non autorisé</b>\n\n"
                        "Ce bot ne fonctionne que:\n"
                        "• En chat privé\n"
                        "• Dans le groupe admin autorisé\n\n"
                        f"📋 <b>Group ID:</b> <code>{chat_id}</code>\n"
                        f"Copie ce ID et envoie-le à @ZEROR1SK pour autoriser ce groupe.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            
            # Don't call the handler - block the message
            return
        
        # Default: allow
        return await handler(event, data)
