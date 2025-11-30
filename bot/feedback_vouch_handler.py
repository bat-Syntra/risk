"""
Feedback and Vouch system for bet confirmations
Allows users to clear messages, give feedback, and vouch for winning bets
"""
import logging
import asyncio
from datetime import datetime, date
from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models.bet import UserBet
from models.user import User
from models.feedback import UserFeedback, UserVouch
from sqlalchemy import and_, desc
import os
from config import ADMIN_CHAT_ID

router = Router()
logger = logging.getLogger(__name__)


# FSM States for feedback
class FeedbackStates(StatesGroup):
    waiting_good_feedback = State()
    waiting_bad_feedback = State()

# Admin IDs from environment (same logic as admin_handlers.py)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DEFAULT_OWNER_ID = 8213628656
if DEFAULT_OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(DEFAULT_OWNER_ID)
if ADMIN_CHAT_ID and int(ADMIN_CHAT_ID) not in ADMIN_IDS:
    try:
        if int(ADMIN_CHAT_ID) != 0:
            ADMIN_IDS.append(int(ADMIN_CHAT_ID))
    except Exception:
        pass

# Use first admin ID for notifications
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0


@router.callback_query(F.data.startswith("clear_msg_"))
async def callback_clear_message(callback: types.CallbackQuery):
    """
    Clear (delete) a confirmation message after user has seen it
    Format: clear_msg_<bet_id>
    """
    await callback.answer("🗑️ Message supprimé / Message deleted")
    
    try:
        # Delete the message
        await callback.message.delete()
        logger.info(f"Deleted confirmation message for user {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Error deleting message: {e}")


@router.callback_query(F.data.startswith("feedback_"))
async def callback_feedback(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle feedback button click - Ask user to write their feedback
    Format: feedback_<bet_id>_<type> where type = 'good' or 'bad'
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 3:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[1])
        feedback_type = parts[2]  # 'good' or 'bad'
        
        if feedback_type not in ['good', 'bad']:
            await callback.answer("❌ Type invalide", show_alert=True)
            return
        
        db = SessionLocal()
        try:
            # Get bet info
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            # Get user for language
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            # Store bet_id and type in FSM state
            await state.update_data(bet_id=bet_id, feedback_type=feedback_type)
            
            logger.info(f"🔄 Setting FSM state for user {callback.from_user.id}, type={feedback_type}")
            
            # Set FSM state and ask for feedback text
            if feedback_type == 'good':
                await state.set_state(FeedbackStates.waiting_good_feedback)
                logger.info(f"✅ FSM state set to waiting_good_feedback for user {callback.from_user.id}")
                if lang == 'fr':
                    prompt = (
                        "✅ <b>Super! Écris ton feedback positif:</b>\n\n"
                        "💬 Qu'est-ce qui t'a plu? Qu'est-ce qui a bien fonctionné?\n\n"
                        "<i>Envoie ton message maintenant...</i>"
                    )
                else:
                    prompt = (
                        "✅ <b>Great! Write your positive feedback:</b>\n\n"
                        "💬 What did you like? What worked well?\n\n"
                        "<i>Send your message now...</i>"
                    )
            else:
                await state.set_state(FeedbackStates.waiting_bad_feedback)
                if lang == 'fr':
                    prompt = (
                        "📝 <b>Décris le problème rencontré:</b>\n\n"
                        "💬 Qu'est-ce qui n'a pas fonctionné? Comment peut-on améliorer?\n\n"
                        "<i>Envoie ton message maintenant...</i>"
                    )
                else:
                    prompt = (
                        "📝 <b>Describe the issue:</b>\n\n"
                        "💬 What didn't work? How can we improve?\n\n"
                        "<i>Send your message now...</i>"
                    )
            
            # Send prompt and store message IDs to delete later
            prompt_message = await callback.message.answer(prompt, parse_mode=ParseMode.HTML)
            await state.update_data(
                prompt_message_id=prompt_message.message_id,
                original_bet_message_id=callback.message.message_id,  # Save original message to delete
                chat_id=callback.message.chat.id
            )
        
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            await callback.answer("❌ Erreur lors de l'envoi du feedback", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_feedback: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.message(FeedbackStates.waiting_good_feedback)
async def handle_good_feedback_text(message: types.Message, state: FSMContext):
    """
    Handle the good feedback text message from user
    """
    logger.info(f"📨 Received GOOD feedback text from user {message.from_user.id}: {message.text[:50]}...")
    feedback_text = message.text
    
    if not feedback_text or len(feedback_text.strip()) < 3:
        await message.answer("❌ Feedback trop court. Écris au moins quelques mots!")
        return
    
    # Get stored data
    data = await state.get_data()
    bet_id = data.get('bet_id')
    prompt_message_id = data.get('prompt_message_id')
    original_bet_message_id = data.get('original_bet_message_id')
    chat_id = data.get('chat_id')
    
    db = SessionLocal()
    try:
        # Delete the original bet confirmation message (with buttons)
        if original_bet_message_id and chat_id:
            try:
                await message.bot.delete_message(chat_id, original_bet_message_id)
                logger.info(f"✅ Deleted original bet message {original_bet_message_id}")
            except Exception as e:
                logger.error(f"Could not delete original bet message: {e}")
        
        # Delete the prompt message
        if prompt_message_id:
            try:
                await message.bot.delete_message(message.chat.id, prompt_message_id)
            except Exception as e:
                logger.error(f"Could not delete prompt message: {e}")
        
        # Delete user's feedback message
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Could not delete user message: {e}")
        
        # Get bet info
        bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
        if not bet:
            await message.answer("❌ Bet non trouvé")
            await state.clear()
            return
        
        # Get user for language
        user = db.query(User).filter(User.telegram_id == bet.user_id).first()
        lang = user.language if user else 'en'
        
        # Create feedback with message
        feedback = UserFeedback(
            user_id=message.from_user.id,
            bet_id=bet_id,
            feedback_type='good',
            message=feedback_text,
            bet_type=bet.bet_type,
            bet_amount=bet.total_stake,
            profit=bet.actual_profit if bet.actual_profit else 0,
            match_info=bet.match_name or "Unknown match",
            seen_by_admin=False
        )
        db.add(feedback)
        db.commit()
        
        # Send confirmation to user (will auto-delete after 10 seconds)
        if lang == 'fr':
            response = (
                "✅ <b>Merci pour ton feedback positif!</b>\n\n"
                "💬 Ton message a été envoyé à l'admin.\n"
                "Ton retour nous aide à améliorer le service. 💚"
            )
        else:
            response = (
                "✅ <b>Thanks for your positive feedback!</b>\n\n"
                "💬 Your message has been sent to admin.\n"
                "Your feedback helps us improve. 💚"
            )
        
        confirmation_msg = await message.answer(response, parse_mode=ParseMode.HTML)
        
        # Auto-delete confirmation after 10 seconds (background task - non-blocking!)
        async def delete_after_delay():
            await asyncio.sleep(10)
            try:
                await confirmation_msg.delete()
            except Exception as e:
                logger.error(f"Could not delete confirmation message: {e}")
        
        asyncio.create_task(delete_after_delay())
        
        # Notify admin
        logger.info(f"📨 Attempting to send feedback to admin. ADMIN_ID={ADMIN_ID}")
        if ADMIN_ID:
            try:
                username = message.from_user.username or f"User {message.from_user.id}"
                admin_text = (
                    f"✅ <b>NOUVEAU FEEDBACK POSITIF</b>\n\n"
                    f"👤 User: @{username}\n"
                    f"🎯 Bet Type: {bet.bet_type}\n"
                    f"💵 Amount: ${bet.total_stake:.2f}\n"
                    f"💰 Profit: ${bet.actual_profit:+.2f}\n"
                    f"⚽ Match: {bet.match_name or 'N/A'}\n\n"
                    f"💬 <b>Message:</b>\n"
                    f"<i>{feedback_text}</i>\n\n"
                    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                logger.info(f"📤 Sending feedback notification to admin {ADMIN_ID}")
                await message.bot.send_message(ADMIN_ID, admin_text, parse_mode=ParseMode.HTML)
                logger.info(f"✅ Feedback notification sent successfully to admin {ADMIN_ID}")
            except Exception as e:
                logger.error(f"❌ Error notifying admin of feedback: {e}")
        else:
            logger.error(f"❌ ADMIN_ID is not set! Cannot send feedback notification.")
    
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        await message.answer("❌ Erreur lors de l'enregistrement du feedback")
        db.rollback()
    finally:
        db.close()
        await state.clear()


@router.message(FeedbackStates.waiting_bad_feedback)
async def handle_bad_feedback_text(message: types.Message, state: FSMContext):
    """
    Handle the bad feedback text message from user
    """
    logger.info(f"📨 Received BAD feedback text from user {message.from_user.id}: {message.text[:50]}...")
    feedback_text = message.text
    
    if not feedback_text or len(feedback_text.strip()) < 3:
        await message.answer("❌ Feedback trop court. Écris au moins quelques mots!")
        return
    
    # Get stored data
    data = await state.get_data()
    bet_id = data.get('bet_id')
    prompt_message_id = data.get('prompt_message_id')
    original_bet_message_id = data.get('original_bet_message_id')
    chat_id = data.get('chat_id')
    
    db = SessionLocal()
    try:
        # Delete the original bet confirmation message (with buttons)
        if original_bet_message_id and chat_id:
            try:
                await message.bot.delete_message(chat_id, original_bet_message_id)
                logger.info(f"✅ Deleted original bet message {original_bet_message_id}")
            except Exception as e:
                logger.error(f"Could not delete original bet message: {e}")
        
        # Delete the prompt message
        if prompt_message_id:
            try:
                await message.bot.delete_message(message.chat.id, prompt_message_id)
            except Exception as e:
                logger.error(f"Could not delete prompt message: {e}")
        
        # Delete user's feedback message
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Could not delete user message: {e}")
        
        # Get bet info
        bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
        if not bet:
            await message.answer("❌ Bet non trouvé")
            await state.clear()
            return
        
        # Get user for language
        user = db.query(User).filter(User.telegram_id == bet.user_id).first()
        lang = user.language if user else 'en'
        
        # Create feedback with message
        feedback = UserFeedback(
            user_id=message.from_user.id,
            bet_id=bet_id,
            feedback_type='bad',
            message=feedback_text,
            bet_type=bet.bet_type,
            bet_amount=bet.total_stake,
            profit=bet.actual_profit if bet.actual_profit else 0,
            match_info=bet.match_name or "Unknown match",
            seen_by_admin=False
        )
        db.add(feedback)
        db.commit()
        
        # Send confirmation to user (will auto-delete after 10 seconds)
        if lang == 'fr':
            response = (
                "📝 <b>Feedback reçu</b>\n\n"
                "💬 Ton message a été envoyé à l'admin.\n"
                "Merci de nous avoir fait part de ton expérience.\n"
                "Nous allons étudier ton cas pour améliorer le service. 🔍"
            )
        else:
            response = (
                "📝 <b>Feedback received</b>\n\n"
                "💬 Your message has been sent to admin.\n"
                "Thanks for sharing your experience.\n"
                "We'll review your case to improve the service. 🔍"
            )
        
        confirmation_msg = await message.answer(response, parse_mode=ParseMode.HTML)
        
        # Auto-delete confirmation after 10 seconds (background task - non-blocking!)
        async def delete_after_delay():
            await asyncio.sleep(10)
            try:
                await confirmation_msg.delete()
            except Exception as e:
                logger.error(f"Could not delete confirmation message: {e}")
        
        asyncio.create_task(delete_after_delay())
        
        # Notify admin
        logger.info(f"📨 Attempting to send BAD feedback to admin. ADMIN_ID={ADMIN_ID}")
        if ADMIN_ID:
            try:
                username = message.from_user.username or f"User {message.from_user.id}"
                admin_text = (
                    f"⚠️ <b>NOUVEAU FEEDBACK NÉGATIF</b>\n\n"
                    f"👤 User: @{username}\n"
                    f"🎯 Bet Type: {bet.bet_type}\n"
                    f"💵 Amount: ${bet.total_stake:.2f}\n"
                    f"💰 Profit: ${bet.actual_profit:+.2f}\n"
                    f"⚽ Match: {bet.match_name or 'N/A'}\n\n"
                    f"💬 <b>Message:</b>\n"
                    f"<i>{feedback_text}</i>\n\n"
                    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                logger.info(f"📤 Sending BAD feedback notification to admin {ADMIN_ID}")
                await message.bot.send_message(ADMIN_ID, admin_text, parse_mode=ParseMode.HTML)
                logger.info(f"✅ BAD feedback notification sent successfully to admin {ADMIN_ID}")
            except Exception as e:
                logger.error(f"❌ Error notifying admin of BAD feedback: {e}")
        else:
            logger.error(f"❌ ADMIN_ID is not set! Cannot send BAD feedback notification.")
    
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        await message.answer("❌ Erreur lors de l'enregistrement du feedback")
        db.rollback()
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("vouch_"))
async def callback_vouch(callback: types.CallbackQuery):
    """
    Handle vouch button click for winning bets
    Format: vouch_<bet_id>
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 2:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[1])
        
        db = SessionLocal()
        try:
            # Get bet info
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            # Check if bet is won
            if bet.status != 'won' or not bet.actual_profit or bet.actual_profit <= 0:
                await callback.answer("❌ Ce bet n'est pas gagnant", show_alert=True)
                return
            
            # Check if vouch already exists
            existing = db.query(UserVouch).filter(UserVouch.bet_id == bet_id).first()
            if existing:
                await callback.answer("✅ Tu as déjà vouch pour ce bet!", show_alert=True)
                return
            
            # Get user for language
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            # Get sport from drop_event if available
            sport = "Unknown"
            if bet.drop_event and bet.drop_event.payload:
                sport = bet.drop_event.payload.get('sport', 'Unknown')
            
            # Create vouch
            vouch = UserVouch(
                user_id=callback.from_user.id,
                bet_id=bet_id,
                bet_type=bet.bet_type,
                bet_amount=bet.total_stake,
                profit=bet.actual_profit,
                match_info=bet.match_name or "Unknown match",
                match_date=bet.match_date,
                sport=sport,
                seen_by_admin=False
            )
            db.add(vouch)
            db.commit()
            
            # Delete the original bet confirmation message (to keep chat clean)
            try:
                await callback.message.delete()
                logger.info(f"✅ Deleted bet message after vouch for bet {bet_id}")
            except Exception as e:
                logger.error(f"Could not delete bet message after vouch: {e}")
            
            # Send confirmation to user
            if lang == 'fr':
                response = (
                    "🎉 <b>Merci pour ton VOUCH!</b>\n\n"
                    "Ton témoignage a été envoyé à l'admin. 💪"
                )
            else:
                response = (
                    "🎉 <b>Thanks for your VOUCH!</b>\n\n"
                    "Your testimonial has been sent to the admin. 💪"
                )
            
            await callback.answer(response, show_alert=True)
            
            # Send vouch to admin with varying intensity based on profit
            if ADMIN_ID:
                try:
                    username = callback.from_user.username or f"User {callback.from_user.id}"
                    profit = bet.actual_profit
                    
                    # Different messages based on profit tiers
                    if profit >= 500:
                        emoji = "🚀🎰🔥"
                        title = "VOUCH MASSIF!!! 🌟💎🔥"
                        comment = "ÉNORME GAIN! 🎰💰🚀"
                    elif profit >= 200:
                        emoji = "🔥💰"
                        title = "GROS VOUCH! 🎉🔥"
                        comment = "Beau gain! 💪"
                    elif profit >= 100:
                        emoji = "✨💰"
                        title = "VOUCH! ✅"
                        comment = "Bon profit! ✅"
                    elif profit >= 50:
                        emoji = "✅💚"
                        title = "Vouch 👍"
                        comment = "Solid win! 💚"
                    else:
                        emoji = "✅"
                        title = "Vouch"
                        comment = "Nice! ✅"
                    
                    admin_text = (
                        f"{emoji} <b>{title}</b>\n\n"
                        f"👤 @{username}\n"
                        f"💰 <b>Profit: ${profit:+.2f}</b>\n"
                        f"💵 Mise: ${bet.total_stake:.2f}\n"
                        f"📈 ROI: {(profit/bet.total_stake*100):.1f}%\n"
                        f"🎯 Type: {bet.bet_type.upper()}\n"
                        f"⚽ Match: {bet.match_name or 'N/A'}\n"
                        f"🏆 {sport}\n\n"
                        f"💬 <i>{comment}</i>\n"
                        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    await callback.bot.send_message(ADMIN_ID, admin_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Error notifying admin of vouch: {e}")
        
        except Exception as e:
            logger.error(f"Error processing vouch: {e}")
            await callback.answer("❌ Erreur lors de l'envoi du vouch", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_vouch: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


def get_feedback_vouch_buttons(bet_id: int, is_winning_bet: bool = False, lang: str = 'en') -> types.InlineKeyboardMarkup:
    """
    Generate inline keyboard with Clear, Feedback, and optionally Vouch buttons
    
    Args:
        bet_id: The bet ID
        is_winning_bet: Whether this is a winning bet (shows Vouch button)
        lang: User language
    
    Returns:
        InlineKeyboardMarkup with appropriate buttons
    """
    buttons = []
    
    # Row 1: Clear button (always shown)
    if lang == 'fr':
        clear_btn = types.InlineKeyboardButton(
            text="🗑️ Supprimer ce message",
            callback_data=f"clear_msg_{bet_id}"
        )
    else:
        clear_btn = types.InlineKeyboardButton(
            text="🗑️ Clear this message",
            callback_data=f"clear_msg_{bet_id}"
        )
    buttons.append([clear_btn])
    
    # Row 2: Feedback buttons (always shown)
    if lang == 'fr':
        good_feedback_btn = types.InlineKeyboardButton(
            text="👍 Bon feedback",
            callback_data=f"feedback_{bet_id}_good"
        )
        bad_feedback_btn = types.InlineKeyboardButton(
            text="👎 Mauvais feedback",
            callback_data=f"feedback_{bet_id}_bad"
        )
    else:
        good_feedback_btn = types.InlineKeyboardButton(
            text="👍 Good feedback",
            callback_data=f"feedback_{bet_id}_good"
        )
        bad_feedback_btn = types.InlineKeyboardButton(
            text="👎 Bad feedback",
            callback_data=f"feedback_{bet_id}_bad"
        )
    buttons.append([good_feedback_btn, bad_feedback_btn])
    
    # Row 3: Vouch button (only for winning bets)
    if is_winning_bet:
        if lang == 'fr':
            vouch_btn = types.InlineKeyboardButton(
                text="🎉 VOUCH (témoigner)",
                callback_data=f"vouch_{bet_id}"
            )
        else:
            vouch_btn = types.InlineKeyboardButton(
                text="🎉 VOUCH (testimonial)",
                callback_data=f"vouch_{bet_id}"
            )
        buttons.append([vouch_btn])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)
