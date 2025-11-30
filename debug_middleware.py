"""
Debug middleware pour voir tous les callbacks
"""
import logging
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from typing import Any, Callable, Dict, Awaitable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebugCallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        
        # Log callback data
        callback_data = event.data if event else "None"
        user_id = event.from_user.id if event and event.from_user else "Unknown"
        
        logger.info(f"🔍 CALLBACK RECEIVED:")
        logger.info(f"  - User: {user_id}")
        logger.info(f"  - Data: {callback_data}")
        logger.info(f"  - Message ID: {event.message.message_id if event and event.message else 'None'}")
        
        # Log to file too
        with open("callback_debug.log", "a") as f:
            f.write(f"CALLBACK: User={user_id}, Data={callback_data}\n")
        
        # Continue to handler
        return await handler(event, data)
