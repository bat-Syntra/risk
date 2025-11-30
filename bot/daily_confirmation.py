"""
Daily confirmation system for bet tracking
Sends confirmation requests after midnight and handles user responses
"""
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional
from aiogram import Bot, F, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from models.user import User
from models.bet import DailyStats, ConversationState, UserBet
from bot.bet_handlers import BetCorrectionStates

router = Router()
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None
bot_instance = None


def init_daily_confirmation_scheduler(bot: Bot):
    """
    Initialize the daily confirmation system
    
    NOTE: We DON'T use automatic scheduler at 00:05 anymore.
    Instead, the AutoconfirmMiddleware intercepts all user interactions
    after midnight and prompts them to confirm before allowing access.
    This ensures 100% response rate as it's BLOCKING.
    
    Args:
        bot: Telegram Bot instance
    """
    global bot_instance
    bot_instance = bot
    
    # NO SCHEDULER - Middleware handles everything on-demand
    logger.info("✅ Daily confirmation system initialized (middleware-based, blocking)")


async def send_daily_confirmations():
    """
    Send confirmation requests to users for yesterday's bets
    """
    if not bot_instance:
        logger.error("Bot instance not initialized")
        return
    
    yesterday = (datetime.now() - timedelta(days=1)).date()
    
    db = SessionLocal()
    try:
        # Find users with unconfirmed stats from yesterday
        pending_stats = db.query(DailyStats).filter(
            DailyStats.date == yesterday,
            DailyStats.confirmed == False,
            DailyStats.total_bets > 0  # Only users who actually bet
        ).all()
        
        logger.info(f"📨 Sending {len(pending_stats)} daily confirmations for {yesterday}")
        
        for stats in pending_stats:
            try:
                await send_confirmation_request(stats.user_id, stats)
            except Exception as e:
                logger.error(f"Error sending confirmation to {stats.user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in send_daily_confirmations: {e}")
    finally:
        db.close()


async def send_confirmation_request(user_id: int, stats: DailyStats):
    """
    Send confirmation request to a specific user
    
    Args:
        user_id: User's Telegram ID
        stats: DailyStats object for the day
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        date_str = stats.date.strftime('%d/%m/%Y')
        
        if lang == 'fr':
            message = (
                f"📊 <b>CONFIRMATION QUOTIDIENNE</b>\n\n"
                f"Date: {date_str}\n\n"
                f"Selon mes données:\n"
                f"• Nombre de bets: {stats.total_bets}\n"
                f"• Total misé: ${stats.total_staked:.2f}\n"
                f"• Profit prévu: ${stats.total_profit:.2f}\n\n"
                f"<b>Ces données sont-elles correctes?</b>"
            )
            btn_yes = "✅ Oui, c'est bon!"
            btn_no = "❌ Non, corriger"
        else:
            message = (
                f"📊 <b>DAILY CONFIRMATION</b>\n\n"
                f"Date: {date_str}\n\n"
                f"According to my data:\n"
                f"• Number of bets: {stats.total_bets}\n"
                f"• Total staked: ${stats.total_staked:.2f}\n"
                f"• Expected profit: ${stats.total_profit:.2f}\n\n"
                f"<b>Is this data correct?</b>"
            )
            btn_yes = "✅ Yes, correct!"
            btn_no = "❌ No, fix it"
        
        keyboard = [
            [
                InlineKeyboardButton(text=btn_yes, callback_data=f"confirm_yes_{stats.date}"),
                InlineKeyboardButton(text=btn_no, callback_data=f"confirm_no_{stats.date}")
            ]
        ]
        
        await bot_instance.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error sending confirmation request to {user_id}: {e}")
        raise
    finally:
        db.close()


@router.callback_query(F.data.startswith("confirm_yes_"))
async def callback_confirm_yes(callback: types.CallbackQuery):
    """
    User confirms the stats are correct
    """
    await callback.answer("✅ Confirmé!" if callback.from_user.language_code == 'fr' else "✅ Confirmed!")
    
    date_str = callback.data.split('_')[2]
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == date_obj
        ).first()
        
        if stats:
            stats.confirmed = True
            
            # 🔥 AUTO-SYNC: Create missing UserBet records if they don't exist
            existing_bets = db.query(UserBet).filter(
                UserBet.user_id == user_id,
                UserBet.bet_date == date_obj
            ).count()
            
            expected_bets = stats.total_bets
            missing = expected_bets - existing_bets
            
            if missing > 0:
                logger.info(f"🔄 Auto-creating {missing} missing UserBet(s) for user {user_id} on {date_obj}")
                
                # Create missing bets with average stake/profit
                avg_stake = stats.total_staked / expected_bets if expected_bets > 0 else stats.total_staked
                avg_profit = stats.total_profit / expected_bets if expected_bets > 0 else stats.total_profit
                
                for i in range(missing):
                    user_bet = UserBet(
                        user_id=user_id,
                        drop_event_id=None,
                        bet_type='arbitrage',  # Default assumption
                        bet_date=date_obj,
                        total_stake=avg_stake,
                        expected_profit=avg_profit,
                        actual_profit=avg_profit,  # Mark as realized
                        status='completed'
                    )
                    db.add(user_bet)
                    logger.info(f"  ✅ Created UserBet #{i+1}: ${avg_stake} → ${avg_profit:+.2f}")
            
            db.commit()
            
            lang = callback.from_user.language_code
            if lang == 'fr':
                confirmation_text = "\n\n✅ <b>Confirmé! Stats enregistrées.</b>"
                if missing > 0:
                    confirmation_text += f"\n(🔄 {missing} bet(s) synchronisé(s))"
            else:
                confirmation_text = "\n\n✅ <b>Confirmed! Stats recorded.</b>"
                if missing > 0:
                    confirmation_text += f"\n(🔄 {missing} bet(s) synced)"
            
            try:
                await callback.message.edit_text(
                    callback.message.text + confirmation_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                await callback.message.answer(confirmation_text, parse_mode=ParseMode.HTML)
        else:
            await callback.answer("❌ Stats non trouvées", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error confirming stats: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("confirm_no_"))
async def callback_confirm_no(callback: types.CallbackQuery, state: FSMContext):
    """
    User wants to correct the stats → start conversation
    """
    await callback.answer()
    
    date_str = callback.data.split('_')[2]
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    # Save conversation state
    db = SessionLocal()
    try:
        conv_state = db.query(ConversationState).filter(
            ConversationState.user_id == user_id
        ).first()
        
        context = {'date': date_str}
        
        if conv_state:
            conv_state.state = 'awaiting_bet_count'
            conv_state.context = context
        else:
            conv_state = ConversationState(
                user_id=user_id,
                state='awaiting_bet_count',
                context=context
            )
            db.add(conv_state)
        
        db.commit()
        
        # Set FSM state
        await state.set_state(BetCorrectionStates.awaiting_bet_count)
        await state.update_data(date=date_str)
        
        lang = callback.from_user.language_code
        if lang == 'fr':
            prompt = (
                "📝 <b>Correction des stats</b>\n\n"
                "Combien de bets avez-vous réellement fait ce jour-là?\n"
                "Envoyez juste le nombre (ex: 5)"
            )
        else:
            prompt = (
                "📝 <b>Stats correction</b>\n\n"
                "How many bets did you actually make that day?\n"
                "Just send the number (e.g., 5)"
            )
        
        try:
            await callback.message.edit_text(prompt, parse_mode=ParseMode.HTML)
        except Exception:
            await callback.message.answer(prompt, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logger.error(f"Error starting correction: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.message(BetCorrectionStates.awaiting_bet_count)
async def process_bet_count(message: types.Message, state: FSMContext):
    """
    Process bet count input from user
    """
    text = message.text.strip()
    lang = message.from_user.language_code
    
    try:
        bet_count = int(text)
        if bet_count < 0:
            raise ValueError
        
        # Save to state and move to next step
        await state.update_data(bet_count=bet_count)
        await state.set_state(BetCorrectionStates.awaiting_total_stake)
        
        if lang == 'fr':
            prompt = (
                f"✅ {bet_count} bet(s)\n\n"
                f"Quel était le <b>montant total misé</b>?\n"
                f"(Somme de tous les stakes, ex: 1500)"
            )
        else:
            prompt = (
                f"✅ {bet_count} bet(s)\n\n"
                f"What was the <b>total amount staked</b>?\n"
                f"(Sum of all stakes, e.g., 1500)"
            )
        
        await message.answer(prompt, parse_mode=ParseMode.HTML)
        
    except ValueError:
        error_msg = "❌ Veuillez entrer un nombre valide (ex: 5)" if lang == 'fr' else "❌ Please enter a valid number (e.g., 5)"
        await message.answer(error_msg)


@router.message(BetCorrectionStates.awaiting_total_stake)
async def process_total_stake(message: types.Message, state: FSMContext):
    """
    Process total stake input from user
    """
    text = message.text.strip()
    lang = message.from_user.language_code
    
    try:
        total_stake = float(text)
        if total_stake < 0:
            raise ValueError
        
        # Save to state and move to next step
        await state.update_data(total_stake=total_stake)
        await state.set_state(BetCorrectionStates.awaiting_profit)
        
        if lang == 'fr':
            prompt = (
                f"✅ ${total_stake:.2f} misé\n\n"
                f"Quel était le <b>profit total réel</b>?\n"
                f"(Gains - Pertes, peut être négatif, ex: 250 ou -50)"
            )
        else:
            prompt = (
                f"✅ ${total_stake:.2f} staked\n\n"
                f"What was the <b>actual total profit</b>?\n"
                f"(Wins - Losses, can be negative, e.g., 250 or -50)"
            )
        
        await message.answer(prompt, parse_mode=ParseMode.HTML)
        
    except ValueError:
        error_msg = "❌ Veuillez entrer un montant valide (ex: 1500)" if lang == 'fr' else "❌ Please enter a valid amount (e.g., 1500)"
        await message.answer(error_msg)


@router.message(BetCorrectionStates.awaiting_profit)
async def process_profit(message: types.Message, state: FSMContext):
    """
    Process profit input from user and update stats
    """
    text = message.text.strip()
    lang = message.from_user.language_code
    user_id = message.from_user.id
    
    try:
        profit = float(text)
        
        # Get all collected data
        data = await state.get_data()
        date_str = data.get('date')
        bet_count = data.get('bet_count')
        total_stake = data.get('total_stake')
        
        if not all([date_str, bet_count is not None, total_stake is not None]):
            raise ValueError("Missing data")
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Update database
        db = SessionLocal()
        try:
            stats = db.query(DailyStats).filter(
                DailyStats.user_id == user_id,
                DailyStats.date == date_obj
            ).first()
            
            if stats:
                stats.total_bets = bet_count
                stats.total_staked = total_stake
                stats.total_profit = profit
                stats.confirmed = True
                db.commit()
                
                # Clear conversation state
                conv_state = db.query(ConversationState).filter(
                    ConversationState.user_id == user_id
                ).first()
                if conv_state:
                    db.delete(conv_state)
                    db.commit()
                
                # Clear FSM state
                await state.clear()
                
                if lang == 'fr':
                    summary = (
                        f"✅ <b>Stats mises à jour!</b>\n\n"
                        f"📊 Résumé:\n"
                        f"• Bets: {bet_count}\n"
                        f"• Misé: ${total_stake:.2f}\n"
                        f"• Profit: ${profit:.2f}\n\n"
                        f"Merci!"
                    )
                else:
                    summary = (
                        f"✅ <b>Stats updated!</b>\n\n"
                        f"📊 Summary:\n"
                        f"• Bets: {bet_count}\n"
                        f"• Staked: ${total_stake:.2f}\n"
                        f"• Profit: ${profit:.2f}\n\n"
                        f"Thank you!"
                    )
                
                await message.answer(summary, parse_mode=ParseMode.HTML)
            else:
                error_msg = "❌ Stats non trouvées" if lang == 'fr' else "❌ Stats not found"
                await message.answer(error_msg)
                await state.clear()
                
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
            error_msg = "❌ Erreur lors de la mise à jour" if lang == 'fr' else "❌ Error updating stats"
            await message.answer(error_msg)
            db.rollback()
        finally:
            db.close()
        
    except ValueError:
        error_msg = "❌ Veuillez entrer un montant valide (ex: 250 ou -50)" if lang == 'fr' else "❌ Please enter a valid amount (e.g., 250 or -50)"
        await message.answer(error_msg)
