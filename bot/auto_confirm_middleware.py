"""
Autoconfirm middleware: on first interaction after midnight, if user has
unconfirmed stats for yesterday (and at least one I BET), prompt confirmation
and block the action until answered.
"""
from typing import Any, Awaitable, Callable, Dict
from datetime import date, timedelta

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler

from database import SessionLocal
from models.bet import DailyStats
from models.user import User
from bot import daily_confirmation


class AutoconfirmMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # DISABLED: Confirmation system now web-only
        return await handler(event, data)
        
        # OLD CODE BELOW (disabled)
        # Resolve user_id from message or callback
        user_id = None
        if isinstance(event, Message):
            try:
                user_id = event.from_user.id
            except Exception:
                user_id = None
        elif isinstance(event, CallbackQuery):
            try:
                user_id = event.from_user.id
            except Exception:
                user_id = None
        else:
            # pass other event types
            return await handler(event, data)

        if not user_id:
            return await handler(event, data)

        # Do not intercept confirmation actions themselves to avoid loops
        cbdata = None
        try:
            if isinstance(event, CallbackQuery):
                cbdata = (event.data or "")
        except Exception:
            cbdata = None
        
        # 🎯 Allow confirmation callbacks + BET callbacks to pass through
        ALLOWED_CALLBACKS = (
            "confirm_yes_", "confirm_no_",
            "good_ev_bet_", "middle_bet_", "i_bet_",  # 🎯 BET RECORDING CALLBACKS
            "undo_bet_",  # Allow undoing bets too
        )
        if cbdata:
            for allowed in ALLOWED_CALLBACKS:
                if cbdata.startswith(allowed):
                    return await handler(event, data)

        # IMPORTANT:
        # - We only block CALLBACKS (buttons, menus) for daily confirmations.
        # - We NEVER block plain messages, otherwise flows that require the
        #   user to type numbers (add bet, corrections, etc.) would break.
        if isinstance(event, Message):
            return await handler(event, data)

        # Also don't block if user is already in the middle of any FSM flow
        # (onboarding, corrections, add bet, etc.). They're answering questions.
        state = data.get("state")
        if state:
            try:
                current_state = await state.get_state()
                if current_state:
                    return await handler(event, data)
            except Exception:
                pass

        # Check ALL unconfirmed stats (oldest first = chronological order)
        # User must confirm each day one by one before accessing the bot via callbacks.
        db = SessionLocal()
        try:
            stats = (
                db.query(DailyStats)
                .filter(
                    DailyStats.user_id == user_id,
                    DailyStats.total_bets > 0,
                    DailyStats.confirmed == False,
                )
                .order_by(DailyStats.date.asc())  # Oldest first
                .first()
            )
        finally:
            db.close()

        if stats is None:
            # nothing to confirm  
            return await handler(event, data)
        
        # Send prompt via daily_confirmation helper (uses stored bot instance)
        try:
            await daily_confirmation.send_confirmation_request(user_id, stats)
        except Exception:
            # As a fallback, ignore errors and proceed
            pass

        # Block the original handler until user confirms (for this callback)
        raise CancelHandler()
