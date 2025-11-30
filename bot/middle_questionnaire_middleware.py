"""
Middleware qui bloque toutes les commandes/actions si l'utilisateur a des middle bets en attente de confirmation.
"""

import logging
from datetime import date
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from aiogram.enums import ParseMode
from sqlalchemy import and_

from database import SessionLocal
from models.bet import UserBet
from models.user import User

logger = logging.getLogger(__name__)


class MiddleQuestionnaireMiddleware(BaseMiddleware):
    """
    Middleware qui force l'utilisateur à répondre aux questionnaires de middle bets
    avant de pouvoir utiliser le bot.
    """
    
    # Commands/callbacks qui sont toujours autorisées (pour le questionnaire lui-même)
    ALLOWED_CALLBACKS = {
        'middle_outcome_',  # Les callbacks du questionnaire middle
        'arb_outcome_',  # Les callbacks du questionnaire arbitrage
        'ev_outcome_',  # Les callbacks du questionnaire good EV
        'match_passed_',  # Les callbacks pour confirmer si le match est passé
        'noop',  # Callback vide
    }
    
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Intercepte tous les messages/callbacks et vérifie si l'utilisateur a des middle bets en attente.
        """
        
        # Récupérer l'user_id
        user_id = None
        if isinstance(event, types.Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            
            # Check if this is an allowed callback (middle questionnaire responses)
            if event.data:
                for allowed in self.ALLOWED_CALLBACKS:
                    if event.data.startswith(allowed):
                        # Allow middle questionnaire callbacks to pass through
                        return await handler(event, data)
        
        if not user_id:
            # Si pas d'user_id, laisser passer
            return await handler(event, data)
        
        # Vérifier si l'utilisateur a des bets en attente de confirmation (TOUS types)
        db = SessionLocal()
        try:
            today = date.today()
            pending_bets = db.query(UserBet).filter(
                and_(
                    UserBet.user_id == user_id,
                    UserBet.status == 'pending',
                    UserBet.match_date <= today
                )
            ).all()
            
            if pending_bets:
                # L'utilisateur a des bets en attente!
                # Ne plus bloquer - juste montrer un warning dans les callbacks
                
                # Get user language
                user = db.query(User).filter(User.telegram_id == user_id).first()
                lang = user.language if user else 'en'
                
                total_pending = len(pending_bets)
                
                # Show non-blocking alert for callbacks only
                if isinstance(event, types.CallbackQuery):
                    if lang == 'fr':
                        alert_msg = f"⚠️ {total_pending} confirmation(s) en attente!\nUtilise /confirmations pour les voir."
                    else:
                        alert_msg = f"⚠️ {total_pending} confirmation(s) pending!\nUse /confirmations to view them."
                    
                    await event.answer(alert_msg, show_alert=False)  # Non-blocking toast
                
                # Log for monitoring
                logger.info(f"User {user_id} has {total_pending} pending confirmations - showing reminder")
        
        except Exception as e:
            logger.error(f"Error in MiddleQuestionnaireMiddleware: {e}")
            # En cas d'erreur, laisser passer pour ne pas bloquer le bot
            return await handler(event, data)
        finally:
            db.close()
        
        # Pas de bet en attente, laisser passer normalement
        return await handler(event, data)
