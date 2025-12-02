"""
Handler pour gérer les confirmations en attente - BLOQUE l'accès au menu
si des confirmations sont nécessaires
"""
import logging
import asyncio
from datetime import date, datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from sqlalchemy import and_

from database import SessionLocal
from models.bet import UserBet
from models.user import User

logger = logging.getLogger(__name__)
router = Router()

# Track users who have been notified today (reset daily)
_notified_today = {}
_last_reset_date = None


def reset_user_notification(user_id: int):
    """
    Reset the notification flag for a user so they can access the menu again
    Call this after a bet is confirmed
    """
    global _notified_today
    if user_id in _notified_today:
        # Check if user still has pending confirmations
        pending_count = check_pending_confirmations_count(user_id)
        if pending_count == 0:
            del _notified_today[user_id]
            logger.info(f"✅ User {user_id} unblocked - all confirmations done")


def check_pending_confirmations_count(user_id: int) -> int:
    """
    Check how many confirmations are pending for a user
    Returns: number of pending confirmations (only ready for confirmation)
    """
    db = SessionLocal()
    try:
        today = date.today()
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == user_id,
                UserBet.status == 'pending'
            )
        ).all()
        
        # Filter to only ready bets:
        # 1. Match date is known and PASSED (day after match or later)
        # 2. No match date, but bet was placed YESTERDAY or before (not today!)
        ready_count = 0
        for bet in pending_bets:
            logger.info(f"[CHECK] Bet {bet.id}: match_date={bet.match_date} (type={type(bet.match_date)}), bet_date={bet.bet_date} (type={type(bet.bet_date)}), today={today} (type={type(today)})")
            
            # Case 1: Match date is known and already passed
            if bet.match_date and bet.match_date < today:  # Strict < to wait until day AFTER match
                ready_count += 1
                logger.info(f"[CHECK] Bet {bet.id} READY (match_date < today)")
            # Case 2: No match date, but bet was placed YESTERDAY or before (not today!)
            elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                ready_count += 1
                logger.info(f"[CHECK] Bet {bet.id} READY (bet_date < today)")
            else:
                logger.info(f"[CHECK] Bet {bet.id} NOT READY")
        
        logger.info(f"[CHECK] TOTAL READY: {ready_count}/{len(pending_bets)}")
        
        # 🔴 Notify web clients via WebSocket if confirmations are ready
        if ready_count > 0:
            try:
                from api.web_api import notify_new_confirmation
                asyncio.create_task(notify_new_confirmation(user_id, ready_count))
            except Exception as e:
                logger.debug(f"Could not send WebSocket notification: {e}")
        
        return ready_count
    except Exception as e:
        logger.error(f"Error checking pending confirmations: {e}")
        return 0
    finally:
        db.close()


async def block_if_pending_confirmations(message: types.Message) -> bool:
    """
    Redirige vers /confirmations si des confirmations sont en attente
    Returns: True if redirected, False if OK to continue
    """
    user_id = message.from_user.id
    pending_count = check_pending_confirmations_count(user_id)
    
    if pending_count == 0:
        return False  # No confirmations needed - show menu
    
    # Auto-redirect to /confirmations command
    await cmd_confirmations(message)
    return True  # Blocked - redirected to confirmations


@router.callback_query(F.data == "start_confirmations")
async def start_confirmations(callback: types.CallbackQuery):
    """
    Lance le processus de confirmation - envoie tous les questionnaires
    """
    await callback.answer("📨 Envoi des questionnaires...")
    
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        # Get user language
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Find pending bets ready for confirmation
        today = date.today()
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == user_id,
                UserBet.status == 'pending'
            )
        ).all()
        
        # Filter to ready bets
        ready_bets = []
        for bet in pending_bets:
            if bet.match_date and bet.match_date < today:
                ready_bets.append(bet)
            elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                ready_bets.append(bet)
        
        if not ready_bets:
            if lang == 'fr':
                await callback.message.edit_text(
                    "✅ <b>Aucune confirmation en attente!</b>\n\n"
                    "Tous tes bets sont à jour. 💚",
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.message.edit_text(
                    "✅ <b>No pending confirmations!</b>\n\n"
                    "All your bets are up to date. 💚",
                    parse_mode=ParseMode.HTML
                )
            # Reset notification tracking so user can access menu
            global _notified_today
            if user_id in _notified_today:
                del _notified_today[user_id]
            return
        
        # Send questionnaires
        from bot.intelligent_questionnaire import send_bet_questionnaire
        
        sent_count = 0
        for bet in ready_bets[:20]:  # Max 20 à la fois
            try:
                await send_bet_questionnaire(callback.bot, bet, lang)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending questionnaire for bet {bet.id}: {e}")
        
        # Confirmation message
        if lang == 'fr':
            await callback.message.edit_text(
                f"✅ <b>{sent_count} questionnaire(s) envoyé(s)!</b>\n\n"
                f"📝 Réponds à chaque questionnaire.\n"
                f"Une fois terminé, l'accès au menu sera rétabli. 🔓",
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                f"✅ <b>{sent_count} questionnaire(s) sent!</b>\n\n"
                f"📝 Answer each questionnaire.\n"
                f"Once done, menu access will be restored. 🔓",
                parse_mode=ParseMode.HTML
            )
        
        # Don't reset notification yet - user must confirm all bets first
        
    except Exception as e:
        logger.error(f"Error in start_confirmations: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.message(Command("confirmations"))
async def cmd_confirmations(message: types.Message):
    """
    Affiche toutes les confirmations en attente et propose de les renvoyer
    """
    logger.info(f"📋 /confirmations called by user {message.from_user.id}")
    user_id = message.from_user.id
    
    db = SessionLocal()
    try:
        # Get user language
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Find all pending bets (including those without match_date)
        today = date.today()
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == user_id,
                UserBet.status == 'pending'
            )
        ).all()
        
        # Separate into ready vs not ready
        ready_bets = []
        future_bets = []
        
        for bet in pending_bets:
            if bet.match_date and bet.match_date <= today:
                ready_bets.append(bet)
            elif bet.match_date is None:
                # No date - needs confirmation
                ready_bets.append(bet)
            else:
                # Future match
                future_bets.append(bet)
        
        if not ready_bets and not future_bets:
            # No pending confirmations
            if lang == 'fr':
                await message.answer(
                    "✅ <b>Aucune confirmation en attente!</b>\n\n"
                    "Tous tes bets sont à jour. 💚",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    "✅ <b>No pending confirmations!</b>\n\n"
                    "All your bets are up to date. 💚",
                    parse_mode=ParseMode.HTML
                )
            return
        
        # Build message
        if lang == 'fr':
            text = "📋 <b>CONFIRMATIONS EN ATTENTE</b>\n\n"
            
            if ready_bets:
                text += f"⚠️ <b>{len(ready_bets)} confirmation(s) nécessaire(s):</b>\n"
                for bet in ready_bets[:5]:  # Show max 5
                    bet_emoji = "🎲" if bet.bet_type == 'middle' else "✅" if bet.bet_type == 'arbitrage' else "📈"
                    match = bet.match_name or "Match"
                    text += f"• {bet_emoji} {match} (${bet.total_stake:.0f})\n"
                if len(ready_bets) > 5:
                    text += f"  ... et {len(ready_bets) - 5} autre(s)\n"
                text += "\n"
            
            if future_bets:
                text += f"📅 <b>{len(future_bets)} match(s) à venir:</b>\n"
                text += f"(Confirmation nécessaire après le match)\n\n"
            
            text += "💡 Clique sur le bouton pour recevoir tous les questionnaires!"
            
            btn = types.InlineKeyboardButton(
                text="📨 Envoyer tous les questionnaires",
                callback_data="resend_all_questionnaires"
            )
        else:
            text = "📋 <b>PENDING CONFIRMATIONS</b>\n\n"
            
            if ready_bets:
                text += f"⚠️ <b>{len(ready_bets)} confirmation(s) needed:</b>\n"
                for bet in ready_bets[:5]:  # Show max 5
                    bet_emoji = "🎲" if bet.bet_type == 'middle' else "✅" if bet.bet_type == 'arbitrage' else "📈"
                    match = bet.match_name or "Match"
                    text += f"• {bet_emoji} {match} (${bet.total_stake:.0f})\n"
                if len(ready_bets) > 5:
                    text += f"  ... and {len(ready_bets) - 5} more\n"
                text += "\n"
            
            if future_bets:
                text += f"📅 <b>{len(future_bets)} upcoming match(es):</b>\n"
                text += f"(Confirmation needed after match)\n\n"
            
            text += "💡 Click the button to receive all questionnaires!"
            
            btn = types.InlineKeyboardButton(
                text="📨 Send all questionnaires",
                callback_data="resend_all_questionnaires"
            )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in cmd_confirmations: {e}")
        await message.answer("❌ Erreur" if lang == 'fr' else "❌ Error")
    finally:
        db.close()


@router.callback_query(F.data == "resend_all_questionnaires")
async def resend_all_questionnaires(callback: types.CallbackQuery):
    """
    Renvoie tous les questionnaires en attente
    """
    await callback.answer("📨 Envoi des questionnaires...")
    
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        # Get user language
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Find pending bets ready for confirmation
        today = date.today()
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.user_id == user_id,
                UserBet.status == 'pending'
            )
        ).all()
        
        # Filter to ready bets
        ready_bets = []
        for bet in pending_bets:
            if bet.match_date and bet.match_date < today:
                ready_bets.append(bet)
            elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                ready_bets.append(bet)
        
        if not ready_bets:
            if lang == 'fr':
                await callback.message.edit_text(
                    "✅ <b>Aucune confirmation en attente!</b>\n\n"
                    "Tous tes bets sont à jour. 💚",
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.message.edit_text(
                    "✅ <b>No pending confirmations!</b>\n\n"
                    "All your bets are up to date. 💚",
                    parse_mode=ParseMode.HTML
                )
            return
        
        # Send questionnaires for READY bets only (not pending_bets!)
        from bot.intelligent_questionnaire import send_bet_questionnaire
        
        sent_count = 0
        for bet in ready_bets[:10]:  # Max 10 à la fois pour ne pas spammer
            try:
                await send_bet_questionnaire(callback.bot, bet, lang)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending questionnaire for bet {bet.id}: {e}")
        
        # Confirmation message
        if lang == 'fr':
            await callback.message.edit_text(
                f"✅ <b>{sent_count} questionnaire(s) envoyé(s)!</b>\n\n"
                f"Réponds-y pour débloquer l'accès complet au bot.",
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                f"✅ <b>{sent_count} questionnaire(s) sent!</b>\n\n"
                f"Answer them to unlock full bot access.",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Error in resend_all_questionnaires: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()
