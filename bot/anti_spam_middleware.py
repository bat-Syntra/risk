"""
Anti-Spam Middleware for Telegram Bot
Prevents users from spamming buttons and receiving duplicate responses
"""

import time
from typing import Dict, Tuple, Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
import logging

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    """
    Middleware to prevent callback query spam.
    If a user clicks the same button multiple times quickly, only process it once.
    """
    
    def __init__(self, timeout: float = 2.0):
        """
        Args:
            timeout: Time in seconds to block duplicate callbacks (default: 2 seconds)
        """
        super().__init__()
        self.timeout = timeout
        # Store last callback time per user+data: {(user_id, callback_data): timestamp}
        self.last_callbacks: Dict[Tuple[int, str], float] = {}
        # Store currently processing callbacks to block parallel duplicates
        self.processing: set = set()
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Process callback and check for spam"""
        
        # event is already a CallbackQuery when registered on dp.callback_query.middleware()
        callback: CallbackQuery = event
        user_id = callback.from_user.id
        callback_data = callback.data
        
        # Create unique key for this user+callback combination
        key = (user_id, callback_data)
        current_time = time.time()
        
        # FIRST: Check if this exact callback is ALREADY being processed (parallel click)
        if key in self.processing:
            logger.warning(
                f"🚫 PARALLEL SPAM BLOCKED: User {user_id} clicked '{callback_data}' "
                f"while still processing (INSTANT BLOCK)"
            )
            await callback.answer("⏳ Traitement en cours...", show_alert=False)
            return None  # Block immediately
        
        # SECOND: Check if this callback was recently processed
        if key in self.last_callbacks:
            last_time = self.last_callbacks[key]
            time_diff = current_time - last_time
            
            # If less than timeout seconds have passed, ignore (spam detected)
            if time_diff < self.timeout:
                logger.warning(
                    f"⚠️ SPAM DETECTED: User {user_id} clicked '{callback_data}' "
                    f"again after only {time_diff:.2f}s (blocked)"
                )
                # Answer the callback silently to remove loading state
                await callback.answer()
                return None  # Don't process the handler
        
        # Mark as processing
        self.processing.add(key)
        
        try:
            # Process the callback normally
            result = await handler(event, data)
            
            # Update last callback time AFTER processing
            self.last_callbacks[key] = time.time()
            
            return result
        finally:
            # Always remove from processing set
            self.processing.discard(key)
            
            # Clean up old entries (older than 10 seconds)
            self._cleanup_old_entries(time.time())
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries to prevent memory leak"""
        keys_to_remove = [
            key for key, timestamp in self.last_callbacks.items()
            if current_time - timestamp > 5.0  # Clean up after 5 seconds
        ]
        for key in keys_to_remove:
            del self.last_callbacks[key]
