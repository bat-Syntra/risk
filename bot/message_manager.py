"""
Message manager for keeping the Telegram UI clean (aiogram v3)
- Edits existing menu messages on callbacks
- Deletes user command messages
- Ensures only one bot menu message per chat/user
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional
from aiogram import Bot
from aiogram import types
from aiogram.enums import ParseMode


class BotMessageManager:
    """Keeps interface clean by editing or replacing messages."""

    # user_id -> (chat_id, message_id)
    _last_messages: Dict[int, Tuple[int, int]] = {}

    @staticmethod
    async def send_or_edit(
        event: types.Message | types.CallbackQuery,
        text: str,
        reply_markup: Optional[types.InlineKeyboardMarkup] = None,
        parse_mode: ParseMode | str = ParseMode.HTML,
    ) -> None:
        """Send a new message or edit the existing one depending on event type.

        Rules:
        - If CallbackQuery: answer() then edit the message in place.
        - If Message (command): delete user's command, delete previous bot menu, send new one.
        """
        if isinstance(event, types.CallbackQuery):
            query = event
            try:
                await query.answer()
            except Exception:
                pass
            try:
                await query.message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                # Track edited message as last bot message
                if query.from_user:
                    BotMessageManager._last_messages[query.from_user.id] = (
                        query.message.chat.id,
                        query.message.message_id,
                    )
                return
            except Exception as e:
                # If edit fails, delete old message and send new one
                bot: Bot = query.bot
                chat_id = query.message.chat.id
                
                # Try to delete the old message first
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
                except Exception:
                    pass
                
                # Send new message
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                if query.from_user:
                    BotMessageManager._last_messages[query.from_user.id] = (chat_id, sent.message_id)
                return

        # Message case
        if isinstance(event, types.Message):
            message = event
            bot: Bot = message.bot

            # 1) delete user's command message
            try:
                await message.delete()
            except Exception:
                pass

            # 2) delete previous bot menu message for this user
            try:
                if message.from_user and message.from_user.id in BotMessageManager._last_messages:
                    chat_id, last_id = BotMessageManager._last_messages[message.from_user.id]
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=last_id)
                    except Exception:
                        pass
            except Exception:
                pass

            # 3) send new menu message
            sent = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )

            # 4) store last bot message id
            if message.from_user:
                BotMessageManager._last_messages[message.from_user.id] = (message.chat.id, sent.message_id)
