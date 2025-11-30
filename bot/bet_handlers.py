"""
Bet tracking handlers for Telegram bot
Handles I BET button, stats display, confirmations, and corrections
"""
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Optional
from aiogram import Bot, F, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from sqlalchemy import func

from database import SessionLocal
from models.user import User, TierLevel
from models.bet import UserBet, DailyStats, ConversationState
from models.drop_event import DropEvent

router = Router()
logger = logging.getLogger(__name__)

# Track user editing state: {user_id: {'bet_id': int, 'field': 'amount'|'profit'}}
USER_EDIT_STATE = {}

# Safe callback answer to avoid TelegramBadRequest when query is too old or already answered
async def safe_callback_answer(callback: types.CallbackQuery, text: str = "", show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception:
        # Ignore stale/invalid query errors silently
        pass


# FSM States for bet corrections and edits
class BetCorrectionStates(StatesGroup):
    awaiting_bet_count = State()
    awaiting_total_stake = State()
    awaiting_profit = State()

class BetEditStates(StatesGroup):
    awaiting_stake = State()
    awaiting_profit = State()


@router.callback_query(F.data.startswith("i_bet_"))
async def callback_i_bet(callback: types.CallbackQuery):
    """
    Handle 'I BET' button click for ARBITRAGE
    Format: i_bet_{drop_event_id}_{total_stake}_{expected_profit}
    """
    logger.info(f"🎯 DEBUG: i_bet handler called with data={callback.data}")
    await safe_callback_answer(callback)
    logger.info(f"🎯 DEBUG: Callback answered")
    
    try:
        parts = callback.data.split('_')
        drop_event_id = int(parts[2])
        total_stake = float(parts[3])
        expected_profit = float(parts[4])
        logger.info(f"🎯 DEBUG: Parsed - drop_event_id={drop_event_id}, stake={total_stake}, profit={expected_profit}")
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid i_bet callback data: {callback.data}, error: {e}")
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    today = date.today()
    
    db = SessionLocal()
    try:
        # Get DropEvent to determine bet_type
        from models.drop_event import DropEvent
        drop_event = None
        
        if drop_event_id > 0:
            drop_event = db.query(DropEvent).filter(DropEvent.id == drop_event_id).first()
        
        # Fallback: if drop_event_id = 0, try to find in last calls by searching all recent drops
        if not drop_event and drop_event_id == 0:
            # Get most recent arbitrage drop (since button was just clicked, it's likely recent)
            drop_event = db.query(DropEvent).filter(DropEvent.bet_type == 'arbitrage').order_by(DropEvent.received_at.desc()).first()
            if drop_event:
                logger.info(f"⚠️ drop_event_id was 0, using most recent arbitrage drop: {drop_event.id}")
        
        # Detect actual bet_type from drop event
        bet_type = 'arbitrage'  # default
        if drop_event:
            bet_type = drop_event.bet_type or 'arbitrage'
        
        # Extract match info for ALL bet types
        match_name = None
        sport_name = None
        match_date = None
        
        if drop_event:
            match_name = drop_event.match or None
            sport_name = drop_event.league or None
            
            # Try to parse commence_time from drop
            try:
                drop_data = drop_event.payload if drop_event.payload else {}
                commence_time = drop_data.get('commence_time')
                if commence_time:
                    from datetime import datetime
                    dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    match_date = dt.date()
            except Exception as e:
                logger.warning(f"Could not parse commence_time: {e}")
        
        logger.info(f"🎯 DEBUG: Got match_name={match_name}, bet_type={bet_type}")
        
        # Check if already bet on this call
        # For good_ev/middle, use event_hash; for arbitrage, use drop_event_id
        if bet_type in ['good_ev', 'middle']:
            event_hash = f"{bet_type}_{drop_event.event_id if drop_event else drop_event_id}"
            existing = db.query(UserBet).filter(
                UserBet.user_id == user_id,
                UserBet.event_hash == event_hash,
                UserBet.bet_type == bet_type
            ).first()
        else:
            existing = db.query(UserBet).filter(
                UserBet.user_id == user_id,
                UserBet.drop_event_id == drop_event_id,
                UserBet.bet_type == bet_type
            ).first()
        
        logger.info(f"🎯 DEBUG: Existing bet check - existing={existing is not None}")
        
        if existing:
            logger.info(f"🎯 DEBUG: Bet already exists, showing alert")
            await safe_callback_answer(callback, "✅ Déjà enregistré", show_alert=True)
            return
        
        # Create bet record with correct bet_type
        if bet_type in ['good_ev', 'middle']:
            event_hash = f"{bet_type}_{drop_event.event_id if drop_event else drop_event_id}"
            user_bet = UserBet(
                user_id=user_id,
                drop_event_id=drop_event_id,
                event_hash=event_hash,
                bet_type=bet_type,
                bet_date=today,
                match_name=match_name,
                sport=sport_name,
                match_date=match_date,
                total_stake=total_stake,
                expected_profit=expected_profit,
                status='pending'
            )
        else:
            user_bet = UserBet(
                user_id=user_id,
                drop_event_id=drop_event_id,
                bet_type=bet_type,
                bet_date=today,
                match_name=match_name,
                sport=sport_name,
                match_date=match_date,
                total_stake=total_stake,
                expected_profit=expected_profit,
                status='pending'
            )
        db.add(user_bet)
        
        # Update or create daily stats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today
        ).first()
        
        if daily_stat:
            daily_stat.total_bets += 1
            daily_stat.total_staked += total_stake
            daily_stat.total_profit += expected_profit
        else:
            daily_stat = DailyStats(
                user_id=user_id,
                date=today,
                total_bets=1,
                total_staked=total_stake,
                total_profit=expected_profit,
                confirmed=False
            )
            db.add(daily_stat)
        
        # Update user's bet counters based on bet_type
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            if bet_type == 'good_ev':
                user.good_ev_bets = (user.good_ev_bets or 0) + 1
            elif bet_type == 'middle':
                user.middle_bets = (user.middle_bets or 0) + 1
            # No specific counter for arbitrage, uses total_bets
        
        db.commit()
        db.flush()  # Get the bet ID
        bet_id = user_bet.id
        logger.info(f"🎯 DEBUG: Bet recorded with ID={bet_id}")
        
        # Fetch user language
        lang = user.language if user else 'en'
        logger.info(f"🎯 DEBUG: User language={lang}")
        
        # Confirmation message with THIS BET + daily totals
        bet_type_display = {
            'arbitrage': 'ARBITRAGE',
            'good_ev': 'GOOD EV',
            'middle': 'MIDDLE'
        }.get(bet_type, 'BET')
        
        if lang == 'fr':
            confirmation = (
                f"\n\n✅ <b>BET {bet_type_display} ENREGISTRÉ!</b>\n\n"
                f"📊 <b>Ce pari:</b>\n"
                f"• Misé: ${total_stake:.2f}\n"
                f"• Profit prévu: ${expected_profit:+.2f}\n\n"
                f"📊 <b>Aujourd'hui (total):</b>\n"
                f"• Paris: {daily_stat.total_bets}\n"
                f"• Misé total: ${daily_stat.total_staked:.2f}\n"
                f"• Profit total: ${daily_stat.total_profit:+.2f}"
            )
            undo_text = "❌ Erreur, je n'ai pas parié"
        else:
            confirmation = (
                f"\n\n✅ <b>BET {bet_type_display} RECORDED!</b>\n\n"
                f"📊 <b>This bet:</b>\n"
                f"• Staked: ${total_stake:.2f}\n"
                f"• Expected profit: ${expected_profit:+.2f}\n\n"
                f"📊 <b>Today (total):</b>\n"
                f"• Bets: {daily_stat.total_bets}\n"
                f"• Total staked: ${daily_stat.total_staked:.2f}\n"
                f"• Total profit: ${daily_stat.total_profit:+.2f}"
            )
            undo_text = "❌ Mistake, I didn't bet"
        
        # Build new keyboard: keep existing, mark I BET as checked, add undo row
        existing_kb = []
        try:
            if callback.message.reply_markup and getattr(callback.message.reply_markup, 'inline_keyboard', None):
                existing_kb = callback.message.reply_markup.inline_keyboard
        except Exception:
            existing_kb = []

        new_kb = []
        for row in existing_kb or []:
            new_row = []
            for btn in row:
                try:
                    cb = getattr(btn, 'callback_data', None)
                    url = getattr(btn, 'url', None)
                    text = getattr(btn, 'text', '')
                except Exception:
                    cb = None
                    url = None
                    text = ''

                if cb and cb.startswith("i_bet_"):
                    # Mark as checked, keep same callback
                    if lang == 'fr':
                        checked_text = "✅ " + text.replace("💰 ", "")
                    else:
                        checked_text = "✅ " + text.replace("💰 ", "")
                    new_row.append(InlineKeyboardButton(text=checked_text, callback_data=cb))
                else:
                    if url:
                        new_row.append(InlineKeyboardButton(text=text, url=url))
                    elif cb:
                        new_row.append(InlineKeyboardButton(text=text, callback_data=cb))
                    else:
                        # Fallback: keep as is
                        new_row.append(InlineKeyboardButton(text=text, callback_data="noop"))
            if new_row:
                new_kb.append(new_row)

        # Append undo row
        new_kb.append([InlineKeyboardButton(text=undo_text, callback_data=f"undo_bet_{bet_id}")])

        # Update message (text + modified keyboard)
        logger.info(f"🎯 DEBUG: About to edit message, new_kb has {len(new_kb)} rows")
        try:
            original_text = callback.message.text or callback.message.caption or ""
            logger.info(f"🎯 DEBUG: Original text length={len(original_text)}, confirmation length={len(confirmation)}")
            await callback.message.edit_text(
                original_text + confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
            logger.info(f"🎯 DEBUG: ✅ Message edited successfully!")
        except Exception as e:
            logger.error(f"🎯 DEBUG: ❌ Failed to edit message: {e}")
            # If edit fails, send new message preserving keyboard behavior
            await callback.message.answer(
                confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
            logger.info(f"🎯 DEBUG: Sent new message instead")
        
    except Exception as e:
        logger.error(f"Error recording bet: {e}")
        await safe_callback_answer(callback, "❌ Erreur lors de l'enregistrement", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("undo_bet_"))
async def callback_undo_bet(callback: types.CallbackQuery):
    """
    Undo a bet that was recorded by mistake
    Format: undo_bet_{bet_id}
    """
    await callback.answer()
    
    try:
        bet_id = int(callback.data.split('_')[2])
    except (IndexError, ValueError):
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        # Find the bet
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await safe_callback_answer(callback, "❌ Bet non trouvé", show_alert=True)
            return
        
        # Update daily stats (subtract this bet)
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == bet.bet_date
        ).first()
        
        if daily_stat:
            daily_stat.total_bets -= 1
            daily_stat.total_staked -= bet.total_stake
            daily_stat.total_profit -= bet.expected_profit
            
            # Remove stats if no more bets that day
            if daily_stat.total_bets <= 0:
                db.delete(daily_stat)
        
        # Delete the bet
        db.delete(bet)
        db.commit()
        
        # Get language
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Rebuild keyboard: remove undo row and revert I BET button text
        new_kb = []
        try:
            existing = callback.message.reply_markup.inline_keyboard if (callback.message.reply_markup and getattr(callback.message.reply_markup, 'inline_keyboard', None)) else []
        except Exception:
            existing = []
        for row in (existing or []):
            new_row = []
            for btn in row:
                try:
                    cb = getattr(btn, 'callback_data', None)
                    url = getattr(btn, 'url', None)
                    text = getattr(btn, 'text', '')
                except Exception:
                    cb = None
                    url = None
                    text = ''
                # Skip any undo button rows
                if cb and cb.startswith('undo_bet_'):
                    continue
                # Revert the I BET label from "✅ ..." back to original
                if cb and cb.startswith('i_bet_'):
                    base_text = text.replace('✅', '').strip()
                    if not base_text.startswith('💰'):
                        base_text = '💰 ' + base_text
                    new_row.append(InlineKeyboardButton(text=base_text, callback_data=cb))
                else:
                    if url:
                        new_row.append(InlineKeyboardButton(text=text, url=url))
                    elif cb:
                        new_row.append(InlineKeyboardButton(text=text, callback_data=cb))
            if new_row:
                new_kb.append(new_row)

        # Prepare text: remove appended confirmation lines if present
        def _strip_confirmation(txt: str) -> str:
            # Search for any confirmation marker (all bet types)
            markers = [
                "✅ BET ARBITRAGE ENREGISTRÉ!",
                "✅ BET MIDDLE ENREGISTRÉ!",
                "✅ BET GOOD EV ENREGISTRÉ!",
                "✅ BET ARBITRAGE RECORDED!",
                "✅ BET MIDDLE RECORDED!",
                "✅ BET GOOD EV RECORDED!",
                "✅ BET ENREGISTRÉ!",  # Generic
                "✅ BET RECORDED!",  # Generic
            ]
            for m in markers:
                idx = txt.find(m)
                if idx != -1:
                    # Cut everything from 2 chars before marker (removes \n\n before it)
                    return txt[:max(0, idx-2)].rstrip()
            return txt
        new_text = _strip_confirmation(callback.message.text or callback.message.caption or "")

        # Apply text+markup update (keeps the call, removes confirm, updates buttons)
        try:
            await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb))
        except Exception:
            # Fallback: markup-only update
            try:
                await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb))
            except Exception:
                pass

        # Small toast
        await safe_callback_answer(callback, "✅ Bet cancelled" if lang != 'fr' else "✅ Bet annulé", show_alert=False)
        
    except Exception as e:
        logger.error(f"Error undoing bet: {e}")
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("my_stats"))
async def callback_my_stats(callback: types.CallbackQuery):
    """
    Show professional dashboard with complete statistics
    Supports month filtering: my_stats or my_stats_YYYY_MM
    """
    # Parse month filter from callback_data
    filter_month = None
    if callback.data != "my_stats" and "_" in callback.data:
        parts = callback.data.split("_", 2)  # my_stats_YYYY_MM
        if len(parts) == 3:
            filter_month = parts[2]  # YYYY_MM
    
    # Use the new professional dashboard
    from .dashboard_stats import show_dashboard_stats
    await show_dashboard_stats(callback, filter_month=filter_month)
    return
    
    # OLD CODE BELOW (kept for reference)
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_start = today.replace(day=1)
        
        # Today stats
        today_stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today
        ).first()
        
        # Week stats
        week_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= week_ago
        ).first()
        
        # Month stats
        month_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= month_start
        ).first()
        
        # All-time stats
        all_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user_id
        ).first()
        
        # Extract values with defaults
        today_bets = today_stats.total_bets if today_stats else 0
        today_staked = today_stats.total_staked if today_stats else 0.0
        today_profit = today_stats.total_profit if today_stats else 0.0
        
        week_bets = int(week_stats[0] or 0)
        week_staked = float(week_stats[1] or 0.0)
        week_profit = float(week_stats[2] or 0.0)
        
        month_bets = int(month_stats[0] or 0)
        month_staked = float(month_stats[1] or 0.0)
        month_profit = float(month_stats[2] or 0.0)
        
        all_bets = int(all_stats[0] or 0)
        all_staked = float(all_stats[1] or 0.0)
        all_profit = float(all_stats[2] or 0.0)
        
        # Calculate ROI
        roi_today = (today_profit / today_staked * 100) if today_staked > 0 else 0
        roi_week = (week_profit / week_staked * 100) if week_staked > 0 else 0
        roi_month = (month_profit / month_staked * 100) if month_staked > 0 else 0
        roi_all = (all_profit / all_staked * 100) if all_staked > 0 else 0
        
        # Calculate stats by type from UserBet table
        from sqlalchemy import case
        
        # Arbitrage stats
        arb_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'arbitrage'
        ).first()
        
        arb_bets = int(arb_stats[0] or 0)
        arb_net = float(arb_stats[1] or 0.0)
        
        # Good EV stats
        good_ev_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev'
        ).first()
        
        good_ev_bets = int(good_ev_stats[0] or 0)
        good_ev_net = float(good_ev_stats[1] or 0.0)
        
        # Middle stats
        middle_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle'
        ).first()
        
        middle_bets = int(middle_stats[0] or 0)
        middle_net = float(middle_stats[1] or 0.0)
        
        # Calculate profit/loss split for display
        # (Note: actual_profit can be negative, representing losses)
        arb_profit = arb_net if arb_net > 0 else 0.0
        arb_loss = arb_net if arb_net < 0 else 0.0
        
        good_ev_profit = good_ev_net if good_ev_net > 0 else 0.0
        good_ev_loss = good_ev_net if good_ev_net < 0 else 0.0
        
        middle_profit = middle_net if middle_net > 0 else 0.0
        middle_loss = middle_net if middle_net < 0 else 0.0
        
        if lang == 'fr':
            stats_text = (
                f"📊 <b>VOS STATISTIQUES</b>\n\n"
                f"<b>📅 Aujourd'hui:</b>\n"
                f"• Bets: {today_bets}\n"
                f"• Misé: ${today_staked:.2f}\n"
                f"• Profit: ${today_profit:.2f}\n"
                f"• ROI: {roi_today:.1f}%\n\n"
                f"<b>📆 7 derniers jours:</b>\n"
                f"• Bets: {week_bets}\n"
                f"• Misé: ${week_staked:.2f}\n"
                f"• Profit: ${week_profit:.2f}\n"
                f"• ROI: {roi_week:.1f}%\n\n"
                f"<b>📊 Ce mois:</b>\n"
                f"• Bets: {month_bets}\n"
                f"• Misé: ${month_staked:.2f}\n"
                f"• Profit: ${month_profit:.2f}\n"
                f"• ROI: {roi_month:.1f}%\n\n"
                f"<b>🏆 Total:</b>\n"
                f"• Bets: {all_bets}\n"
                f"• Misé: ${all_staked:.2f}\n"
                f"• Profit: ${all_profit:.2f}\n"
                f"• ROI: {roi_all:.1f}%\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>📈 STATS PAR TYPE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>📈 Arbitrage:</b>\n"
                f"• Bets: {arb_bets}\n"
                f"• Profit: ${arb_profit:.2f}\n"
                f"• Perte: ${arb_loss:.2f}\n"
                f"• Net: ${arb_net:.2f}\n\n"
                f"<b>💎 Good EV:</b>\n"
                f"• Bets: {good_ev_bets}\n"
                f"• Profit: ${good_ev_profit:.2f}\n"
                f"• Perte: ${good_ev_loss:.2f}\n"
                f"• Net: ${good_ev_net:.2f}\n\n"
                f"<b>🎯 Middle:</b>\n"
                f"• Bets: {middle_bets}\n"
                f"• Profit: ${middle_profit:.2f}\n"
                f"• Perte: ${middle_loss:.2f}\n"
                f"• Net: ${middle_net:.2f}"
            )
        else:
            stats_text = (
                f"📊 <b>YOUR STATISTICS</b>\n\n"
                f"<b>📅 Today:</b>\n"
                f"• Bets: {today_bets}\n"
                f"• Staked: ${today_staked:.2f}\n"
                f"• Profit: ${today_profit:.2f}\n"
                f"• ROI: {roi_today:.1f}%\n\n"
                f"<b>📆 Last 7 days:</b>\n"
                f"• Bets: {week_bets}\n"
                f"• Staked: ${week_staked:.2f}\n"
                f"• Profit: ${week_profit:.2f}\n"
                f"• ROI: {roi_week:.1f}%\n\n"
                f"<b>📊 This month:</b>\n"
                f"• Bets: {month_bets}\n"
                f"• Staked: ${month_staked:.2f}\n"
                f"• Profit: ${month_profit:.2f}\n"
                f"• ROI: {roi_month:.1f}%\n\n"
                f"<b>🏆 All-time:</b>\n"
                f"• Bets: {all_bets}\n"
                f"• Staked: ${all_staked:.2f}\n"
                f"• Profit: ${all_profit:.2f}\n"
                f"• ROI: {roi_all:.1f}%\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>📈 STATS BY TYPE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>📈 Arbitrage:</b>\n"
                f"• Bets: {arb_bets}\n"
                f"• Profit: ${arb_profit:.2f}\n"
                f"• Loss: ${arb_loss:.2f}\n"
                f"• Net: ${arb_net:.2f}\n\n"
                f"<b>💎 Good EV:</b>\n"
                f"• Bets: {good_ev_bets}\n"
                f"• Profit: ${good_ev_profit:.2f}\n"
                f"• Loss: ${good_ev_loss:.2f}\n"
                f"• Net: ${good_ev_net:.2f}\n\n"
                f"<b>🎯 Middle:</b>\n"
                f"• Bets: {middle_bets}\n"
                f"• Profit: ${middle_profit:.2f}\n"
                f"• Loss: ${middle_loss:.2f}\n"
                f"• Net: ${middle_net:.2f}"
            )
        
        # Add Mes Bets button (will show categories menu)
        my_bets_text = "📜 Mes Bets" if lang == 'fr' else "📜 My Bets"
        keyboard = [
            [InlineKeyboardButton(text=my_bets_text, callback_data="my_bets")],
            [InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")]
        ]
        
        try:
            await callback.message.edit_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception:
            await callback.message.answer(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
    except Exception as e:
        logger.error(f"Error in callback_my_stats: {e}")
        await callback.answer("❌ Error retrieving stats", show_alert=True)
    finally:
        db.close()


# REMOVED: i_bet_menu and i_bet_category handlers - now using my_bets and bet_category instead to avoid duplication


# Import stats functions
from .dashboard_stats import show_complete_stats, show_advanced_stats_menu, show_advanced_performance


@router.callback_query(F.data == "view_full_stats")
async def callback_view_full_stats(callback: types.CallbackQuery):
    """Show complete stats - Level 1 (ALPHA only)"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Check if user has ALPHA access
        if not user or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir les statistiques complètes."
                if lang == 'fr' else
                "Activate ALPHA to view full statistics."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="my_stats")],
            ]
            await callback.message.edit_text(
                f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return
    finally:
        db.close()
    
    await show_complete_stats(callback)


@router.callback_query(F.data == "advanced_stats_menu")
async def callback_advanced_stats_menu(callback: types.CallbackQuery):
    """Show advanced stats menu - Level 2 (ALPHA only)"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Check if user has ALPHA access
        if not user or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir les statistiques avancées."
                if lang == 'fr' else
                "Activate ALPHA to view advanced statistics."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="view_full_stats")],
            ]
            await callback.message.edit_text(
                f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return
    finally:
        db.close()
    
    await show_advanced_stats_menu(callback)


@router.callback_query(F.data == "adv_performance")
async def callback_adv_performance(callback: types.CallbackQuery):
    """Show detailed performance (ALPHA only)"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Check if user has ALPHA access
        if not user or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir les performances détaillées."
                if lang == 'fr' else
                "Activate ALPHA to view detailed performance."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="advanced_stats_menu")],
            ]
            await callback.message.edit_text(
                f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return
    finally:
        db.close()
    
    await show_advanced_performance(callback)


@router.callback_query(F.data == "adv_bookmakers")
async def callback_adv_bookmakers(callback: types.CallbackQuery):
    """Show REAL bookmaker analysis (ALPHA only)"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Check if user has ALPHA access
        if not user or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir l'analyse des bookmakers."
                if lang == 'fr' else
                "Activate ALPHA to view bookmaker analysis."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="advanced_stats_menu")],
            ]
            await callback.message.edit_text(
                f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return
        
        # Get all user bets
        all_bets = db.query(UserBet).filter(UserBet.user_id == user_id).all()
        
        if not all_bets:
            text = "📊 Aucun bet enregistré" if lang == 'fr' else "📊 No bets recorded yet"
            keyboard = [[InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="advanced_stats_menu"
            )]]
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            return
        
        # Group bets by bookmaker (extract from bet metadata/description)
        bookmaker_stats = {}
        
        for bet in all_bets:
            # Extract bookmakers from drop_event payload
            if bet.drop_event_id:
                drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
                if drop and drop.payload and isinstance(drop.payload, dict):
                    # Extract casino names from outcomes
                    outcomes = drop.payload.get('outcomes', [])
                    for outcome in outcomes:
                        if 'casino' in outcome:
                            bookmaker = outcome['casino']
                            
                            if bookmaker not in bookmaker_stats:
                                bookmaker_stats[bookmaker] = {
                                    'bets': 0,
                                    'profit': 0,
                                    'staked': 0
                                }
                            
                            # Attribute profit proportionally if multiple bookmakers
                            profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
                            profit_share = profit / len(outcomes) if len(outcomes) > 0 else profit
                            stake_share = bet.total_stake / len(outcomes) if len(outcomes) > 0 else bet.total_stake
                            
                            bookmaker_stats[bookmaker]['bets'] += 1
                            bookmaker_stats[bookmaker]['profit'] += profit_share
                            bookmaker_stats[bookmaker]['staked'] += stake_share
        
        # Build message
        if lang == 'fr':
            text = "🏢 <b>ANALYSE PAR BOOKMAKER</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += "💡 <b>Note:</b> Analyse enrichie avec Book Health Monitor\n\n"
        else:
            text = "🏢 <b>BOOKMAKER ANALYSIS</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += "💡 <b>Note:</b> Analysis enriched with Book Health Monitor\n\n"
        
        # Get Book Health data for this user
        from sqlalchemy import text as sql_text
        health_data = {}
        try:
            health_results = db.execute(sql_text("""
                SELECT casino, total_score, risk_level, estimated_months_until_limit, is_limited
                FROM book_health_scores bhs
                JOIN user_casino_profiles ucp ON bhs.user_id = ucp.user_id AND bhs.casino = ucp.casino
                WHERE bhs.user_id = :user_id
                AND bhs.calculation_date = (
                    SELECT MAX(calculation_date) 
                    FROM book_health_scores 
                    WHERE user_id = :user_id AND casino = bhs.casino
                )
            """), {"user_id": str(user_id)}).fetchall()
            
            for row in health_results:
                health_data[row.casino] = {
                    'score': row.total_score,
                    'risk_level': row.risk_level,
                    'months_until_limit': row.estimated_months_until_limit,
                    'is_limited': row.is_limited
                }
        except Exception as e:
            logger.error(f"Error fetching Book Health data: {e}")
        
        # Sort by profit
        sorted_bookmakers = sorted(bookmaker_stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        
        # Risk level emojis
        risk_emojis = {
            'SAFE': '🟢',
            'LOW': '🟡',
            'MEDIUM': '🟠',
            'HIGH': '🔴',
            'VERY_HIGH': '⛔',
            'INSUFFICIENT_DATA': '⚪'
        }
        
        for casino, stats in sorted_bookmakers[:10]:
            roi = (stats['profit'] / stats['staked'] * 100) if stats['staked'] > 0 else 0
            profit_emoji = "🔥" if roi > 8 else "✅" if roi > 5 else "📈" if roi > 0 else "📉"
            
            # Get health info
            health = health_data.get(casino, {})
            risk_emoji = risk_emojis.get(health.get('risk_level', ''), '⚪')
            
            text += f"{profit_emoji} <b>{casino}</b> {risk_emoji}\n"
            text += f"   • Bets: {stats['bets']} | ROI: {roi:.1f}%\n"
            text += f"   • Profit: ${stats['profit']:+.2f}\n"
            
            # Add Book Health info if available
            if health:
                if health.get('is_limited'):
                    text += f"   ⚠️ <b>LIMITÉ</b>\n"
                elif health.get('months_until_limit'):
                    months = health['months_until_limit']
                    if months < 3:
                        text += f"   ⚠️ Limite prévue: {months:.1f} mois\n"
                    elif months < 6:
                        text += f"   ⚡ Limite prévue: {months:.1f} mois\n"
                    else:
                        text += f"   ✅ Santé: {health['score']}/100\n"
                else:
                    text += f"   📊 Score santé: {health.get('score', 0)}/100\n"
            else:
                text += f"   ℹ️ Book Health: non configuré\n"
            
            text += "\n"
        
        # Add legend
        if lang == 'fr':
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "🟢 SAFE | 🟡 LOW | 🟠 MEDIUM | 🔴 HIGH | ⛔ TRÈS HAUT\n"
            text += "💡 <i>Configure Book Health Monitor pour plus de détails</i>"
        else:
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "🟢 SAFE | 🟡 LOW | 🟠 MEDIUM | 🔴 HIGH | ⛔ VERY HIGH\n"
            text += "💡 <i>Configure Book Health Monitor for more details</i>"
        
        keyboard = [[InlineKeyboardButton(
            text="◀️ Menu Avancé" if lang == 'fr' else "◀️ Advanced Menu",
            callback_data="advanced_stats_menu"
        )]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    
    finally:
        db.close()


@router.callback_query(F.data == "adv_sports")
async def callback_adv_sports(callback: types.CallbackQuery):
    """Show REAL sport analysis"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get all user bets with drop events
        all_bets = db.query(UserBet).filter(UserBet.user_id == user_id).all()
        
        if not all_bets:
            text = "📊 Aucun bet enregistré" if lang == 'fr' else "📊 No bets recorded yet"
            keyboard = [[InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="advanced_stats_menu"
            )]]
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            return
        
        # Group bets by sport
        sport_stats = {}
        unknown_bets = 0
        unknown_profit = 0
        
        for bet in all_bets:
            # Extract sport from drop_event's league field with multiple fallbacks
            sport = None
            if bet.drop_event_id:
                drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
                if drop:
                    # Try league first
                    if drop.league:
                        sport = drop.league
                    # Fallback: try to extract from payload
                    elif drop.payload and isinstance(drop.payload, dict):
                        sport = drop.payload.get('league') or drop.payload.get('sport')
            
            # Track unknown bets separately
            if not sport:
                unknown_bets += 1
                profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
                unknown_profit += profit
                continue
            
            if sport not in sport_stats:
                sport_stats[sport] = {
                    'bets': 0,
                    'profit': 0,
                    'staked': 0
                }
            
            sport_stats[sport]['bets'] += 1
            profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
            sport_stats[sport]['profit'] += profit
            sport_stats[sport]['staked'] += bet.total_stake
        
        # Build message
        sport_emojis = {
            'NBA': '🏀', 'NHL': '🏒', 'NFL': '🏈', 'MLB': '⚾',
            'UFC': '🥊', 'Soccer': '⚽', 'Tennis': '🎾', 'Golf': '⛳',
            'Basketball': '🏀', 'Hockey': '🏒', 'Football': '🏈', 'Baseball': '⚾'
        }
        
        if lang == 'fr':
            text = "🏀 <b>ANALYSE PAR SPORT</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += "📊 <b>Performance par sport:</b>\n\n"
        else:
            text = "🏀 <b>SPORT ANALYSIS</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += "📊 <b>Performance by sport:</b>\n\n"
        
        # Sort by profit
        sorted_sports = sorted(sport_stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        
        for sport, stats in sorted_sports:
            emoji = sport_emojis.get(sport, '🎯')
            roi = (stats['profit'] / stats['staked'] * 100) if stats['staked'] > 0 else 0
            perf_emoji = "🔥" if roi > 8 else "✅" if roi > 5 else "📈" if roi > 0 else "📉"
            
            text += f"{emoji} <b>{sport}</b> {perf_emoji}\n"
            text += f"   • Bets: {stats['bets']} | ROI: {roi:.1f}%\n"
            text += f"   • Profit: ${stats['profit']:+.2f}\n\n"
        
        # Add unknown bets info if any
        if unknown_bets > 0:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            if lang == 'fr':
                text += f"❓ <b>{unknown_bets} bet(s) non catégorisé(s)</b>\n"
                text += f"   • Profit: ${unknown_profit:+.2f}\n"
                text += f"   • <i>Bets sans info de sport</i>\n\n"
            else:
                text += f"❓ <b>{unknown_bets} uncategorized bet(s)</b>\n"
                text += f"   • Profit: ${unknown_profit:+.2f}\n"
                text += f"   • <i>Bets without sport info</i>\n\n"
        
        keyboard = [[InlineKeyboardButton(
            text="◀️ Menu Avancé" if lang == 'fr' else "◀️ Advanced Menu",
            callback_data="advanced_stats_menu"
        )]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    
    finally:
        db.close()


@router.callback_query(F.data == "view_charts")
async def callback_view_charts(callback: types.CallbackQuery):
    """
    Show charts and analytics page (ALPHA only)
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Check if user has ALPHA access
        if not user or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir les graphiques et analyses."
                if lang == 'fr' else
                "Activate ALPHA to view charts and analytics."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="my_stats")],
            ]
            await callback.message.edit_text(
                f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return
        
        # Calculate data for REAL last 7 days with current date (LIVE from UserBet)
        last_7_days = []
        today = date.today()
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            
            # Calculate LIVE profit from UserBet table (not DailyStats)
            day_profit = db.query(func.sum(UserBet.expected_profit)).filter(
                UserBet.user_id == user_id,
                func.date(UserBet.bet_date) == day
            ).scalar() or 0.0
            
            last_7_days.append((day.strftime('%d'), day_profit, day))
        
        # Build IMPROVED ASCII chart with proper scaling
        profits = [p for _, p, _ in last_7_days]
        max_profit = max(profits) if profits else 100
        min_profit = min(profits) if profits else 0
        
        # Ensure positive range for display
        if max_profit <= 0:
            max_profit = 10
        if min_profit >= 0:
            min_profit = -10
        
        chart_height = 8
        chart_lines = []
        
        # Generate chart from top to bottom
        for row in range(chart_height, -1, -1):
            threshold = min_profit + (max_profit - min_profit) * row / chart_height
            line = f"    ${threshold:5.0f}│"
            
            for day_label, profit, _ in last_7_days:
                # Check if this profit should be plotted at this height
                lower = min_profit + (max_profit - min_profit) * (row - 0.5) / chart_height if row > 0 else min_profit - 100
                upper = min_profit + (max_profit - min_profit) * (row + 0.5) / chart_height if row < chart_height else max_profit + 100
                
                if lower <= profit <= upper:
                    line += " ● "
                elif profit > threshold:
                    line += " │ "
                else:
                    line += "   "
            
            chart_lines.append(line)
        
        chart_text = "\n".join(chart_lines)
        
        # Stats by type
        arb_profit = db.query(func.sum(UserBet.expected_profit)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'arbitrage'
        ).scalar() or 0
        
        ev_profit = db.query(func.sum(UserBet.expected_profit)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev'
        ).scalar() or 0
        
        middle_profit = db.query(func.sum(UserBet.expected_profit)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle'
        ).scalar() or 0
        
        total = abs(arb_profit) + abs(ev_profit) + abs(middle_profit)
        arb_pct = (abs(arb_profit) / total * 100) if total > 0 else 0
        ev_pct = (abs(ev_profit) / total * 100) if total > 0 else 0
        middle_pct = (abs(middle_profit) / total * 100) if total > 0 else 0
        
        if lang == 'fr':
            text = (
                f"╔══════════════════════════════════════╗\n"
                f"║         📈 <b>ANALYTICS PRO</b>             ║\n"
                f"╚══════════════════════════════════════╝\n\n"
                f"📊 <b>PROFIT PAR JOUR (7 derniers jours)</b>\n\n"
                f"{chart_text}\n"
                f"        └{'─'*21}\n"
                f"         {'  '.join(d for d, _, _ in last_7_days)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎲 <b>RÉPARTITION PAR TYPE</b>\n\n"
                f"⚖️  Arbitrage  {'█' * int(arb_pct/10)}{'░' * (10-int(arb_pct/10))} {arb_pct:.0f}% (${arb_profit:+.2f})\n"
                f"💎  Good +EV   {'█' * int(ev_pct/10)}{'░' * (10-int(ev_pct/10))} {ev_pct:.0f}% (${ev_profit:+.2f})\n"
                f"🎯  Middle     {'█' * int(middle_pct/10)}{'░' * (10-int(middle_pct/10))} {middle_pct:.0f}% (${middle_profit:+.2f})\n"
            )
        else:
            text = (
                f"╔══════════════════════════════════════╗\n"
                f"║         📈 <b>ANALYTICS PRO</b>             ║\n"
                f"╚══════════════════════════════════════╝\n\n"
                f"📊 <b>PROFIT BY DAY (Last 7 days)</b>\n\n"
                f"{chart_text}\n"
                f"        └{'─'*21}\n"
                f"         {'  '.join(d for d, _, _ in last_7_days)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎲 <b>DISTRIBUTION BY TYPE</b>\n\n"
                f"⚖️  Arbitrage  {'█' * int(arb_pct/10)}{'░' * (10-int(arb_pct/10))} {arb_pct:.0f}% (${arb_profit:+.2f})\n"
                f"💎  Good +EV   {'█' * int(ev_pct/10)}{'░' * (10-int(ev_pct/10))} {ev_pct:.0f}% (${ev_profit:+.2f})\n"
                f"🎯  Middle     {'█' * int(middle_pct/10)}{'░' * (10-int(middle_pct/10))} {middle_pct:.0f}% (${middle_profit:+.2f})\n"
            )
        
        keyboard = [
            [
                InlineKeyboardButton(text="◀️ Stats", callback_data="my_stats"),
                InlineKeyboardButton(text="📋 Bets", callback_data="my_bets")
            ],
            [InlineKeyboardButton(text="⚙️ Menu", callback_data="main_menu")]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in view_charts: {e}")
        await callback.answer("❌ Error loading charts", show_alert=True)
    finally:
        db.close()


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Command to show stats"""
    try:
        await message.delete()
    except Exception:
        pass
    
    # Simulate callback for code reuse
    callback_data = types.CallbackQuery(
        id="stats_cmd",
        from_user=message.from_user,
        chat_instance="stats",
        data="my_stats"
    )
    callback_data.message = message
    callback_data.answer = lambda text="", show_alert=False: None
    
    await callback_my_stats(callback_data)


@router.callback_query(F.data == "my_bets")
async def callback_my_bets(callback: types.CallbackQuery):
    """
    Show menu with 3 categories: Arbitrage, Good EV, Middle
    Replaces i_bet_menu to avoid duplication
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Count bets by type
        arb_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'arbitrage'
        ).scalar() or 0
        
        good_ev_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev'
        ).scalar() or 0
        
        middle_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle'
        ).scalar() or 0
        
        # Get last 10 bets for history
        from bot.dashboard_stats import format_bet_history_card
        
        last_10_bets = db.query(UserBet).filter(
            UserBet.user_id == user_id
        ).order_by(UserBet.created_at.desc()).limit(10).all()
        
        # Build bet history
        history_section = ""
        if last_10_bets:
            history_title = "📋 <b>HISTORIQUE DES BETS</b>" if lang == 'fr' else "📋 <b>BET HISTORY</b>"
            history_section = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{history_title}\n\n"
            
            for bet in last_10_bets:
                history_section += format_bet_history_card(bet, db, lang) + "\n"
        
        if lang == 'fr':
            menu_text = (
                f"📜 <b>MES BETS</b>\n\n"
                f"📈 <b>Arbitrage:</b> {arb_count} bet(s)\n"
                f"💎 <b>Good EV:</b> {good_ev_count} bet(s)\n"
                f"🎯 <b>Middle:</b> {middle_count} bet(s)"
                f"{history_section}"
            )
        else:
            menu_text = (
                f"📜 <b>MY BETS</b>\n\n"
                f"📈 <b>Arbitrage:</b> {arb_count} bet(s)\n"
                f"💎 <b>Good EV:</b> {good_ev_count} bet(s)\n"
                f"🎯 <b>Middle:</b> {middle_count} bet(s)"
                f"{history_section}"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text=f"📈 Arbitrage ({arb_count})",
                callback_data="bet_category_arbitrage"
            )],
            [InlineKeyboardButton(
                text=f"💎 Good EV ({good_ev_count})",
                callback_data="bet_category_good_ev"
            )],
            [InlineKeyboardButton(
                text=f"🎯 Middle ({middle_count})",
                callback_data="bet_category_middle"
            )],
            [InlineKeyboardButton(
                text="◀️ Stats" if lang == 'en' else "◀️ Stats",
                callback_data="my_stats"
            )]
        ]
        
        await callback.message.edit_text(
            menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_my_bets: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_category_"))
async def callback_bet_category(callback: types.CallbackQuery):
    """
    Show bets for a specific category (arbitrage, good_ev, middle)
    Replaces i_bet_category with bet_category prefix
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    category = callback.data.split("_", 2)[2]  # Extract category from callback data
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get bets for this category (limit to last 20)
        bets = db.query(UserBet).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == category
        ).order_by(UserBet.created_at.desc()).limit(20).all()
        
        # Calculate totals
        total_staked = sum(b.total_stake for b in bets)
        total_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in bets)
        
        # Category emoji and name
        category_emoji = {
            'arbitrage': '📈',
            'good_ev': '💎',
            'middle': '🎯'
        }.get(category, '💰')
        
        category_name = {
            'arbitrage': 'Arbitrage',
            'good_ev': 'Good EV',
            'middle': 'Middle'
        }.get(category, category)
        
        if lang == 'fr':
            bets_text = (
                f"{category_emoji} <b>{category_name.upper()} BETS</b>\n\n"
                f"<b>Total:</b> {len(bets)} bet(s)\n"
                f"<b>Misé:</b> ${total_staked:.2f}\n"
                f"<b>Profit:</b> ${total_profit:.2f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        else:
            bets_text = (
                f"{category_emoji} <b>{category_name.upper()} BETS</b>\n\n"
                f"<b>Total:</b> {len(bets)} bet(s)\n"
                f"<b>Staked:</b> ${total_staked:.2f}\n"
                f"<b>Profit:</b> ${total_profit:.2f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        
        # List recent bets with clickable buttons
        keyboard = []
        if bets:
            from datetime import timezone, timedelta
            et_tz = timezone(timedelta(hours=-5))
            
            for i, bet in enumerate(bets[:10], 1):  # Show last 10
                profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
                profit_emoji = "✅" if profit_val > 0 else "❌" if profit_val < 0 else "⏳"
                
                # Convert time to ET
                bet_time = bet.created_at if hasattr(bet, 'created_at') and bet.created_at else bet.bet_date
                if bet_time and hasattr(bet_time, 'tzinfo'):
                    if bet_time.tzinfo is None:
                        bet_time = bet_time.replace(tzinfo=timezone.utc)
                    bet_time_et = bet_time.astimezone(et_tz)
                    time_str = bet_time_et.strftime('%m-%d %H:%M')
                else:
                    time_str = str(bet.bet_date)
                
                # Format bet line
                bet_line = f"{profit_emoji} {time_str}: ${bet.total_stake:.0f} → ${profit_val:+.2f}"
                bets_text += f"{bet_line}\n"
                
                # Add clickable button for this bet
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{profit_emoji} {time_str} - ${profit_val:+.2f}",
                        callback_data=f"bet_detail_{bet.id}"
                    )
                ])
        else:
            bets_text += ("Aucun bet dans cette catégorie." if lang == 'fr' else "No bets in this category.")
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Mes Bets" if lang == 'fr' else "◀️ My Bets",
                callback_data="my_bets"
            )
        ])
        
        await callback.message.edit_text(
            bets_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_bet_category: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


# ========================================
# BET DETAILS & ACTIONS
# ========================================

@router.callback_query(F.data.startswith("bet_detail_"))
async def callback_bet_detail(callback: types.CallbackQuery):
    """Show detailed view of a specific bet with action buttons"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
        roi = (profit_val / bet.total_stake * 100) if bet.total_stake > 0 else 0
        status_emoji = "✅" if profit_val > 0 else "❌" if profit_val < 0 else "⏳"
        
        # Get detailed info from drop_event
        match_info = ""
        league_info = ""
        market_info = ""
        bet_type_display = bet.bet_type.upper() if bet.bet_type else "BET"
        casinos = []
        odds_info = []
        
        if bet.drop_event_id:
            drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
            if drop:
                match_info = drop.match or ""
                league_info = drop.league or ""
                market_info = drop.market or ""
                
                # Extract casinos and odds from payload
                if drop.payload and isinstance(drop.payload, dict):
                    outcomes = drop.payload.get('outcomes', [])
                    for outcome in outcomes:
                        if 'casino' in outcome:
                            casino = outcome['casino']
                            odds = outcome.get('odds', '')
                            selection = outcome.get('outcome', '')
                            casinos.append(casino)
                            if odds:
                                odds_str = f"+{odds}" if int(odds) > 0 else str(odds)
                                odds_info.append(f"{casino}: {selection} ({odds_str})")
        
        # Use created_at for exact time if available, fallback to bet_date
        bet_datetime = bet.created_at if hasattr(bet, 'created_at') and bet.created_at else bet.bet_date
        
        # Convert UTC to ET (UTC-5)
        from datetime import timezone, timedelta
        if bet_datetime:
            # Ensure timezone aware
            if bet_datetime.tzinfo is None:
                bet_datetime = bet_datetime.replace(tzinfo=timezone.utc)
            # Convert to ET
            et_tz = timezone(timedelta(hours=-5))
            bet_datetime_et = bet_datetime.astimezone(et_tz)
        else:
            bet_datetime_et = bet_datetime
        
        # Type emoji
        type_emojis = {'arbitrage': '⚖️', 'middle': '🎯', 'good_ev': '💎'}
        type_emoji = type_emojis.get(bet.bet_type, '📊')
        
        if lang == 'fr':
            text = (
                f"📋 <b>DÉTAILS DU BET</b>\n\n"
                f"{status_emoji} {bet_datetime_et.strftime('%Y-%m-%d à %H:%M:%S')} ET\n"
                f"{type_emoji} Type: <b>{bet_type_display}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            if match_info:
                text += f"🎯 <b>Match:</b> {match_info}\n"
            if league_info:
                text += f"🏆 <b>Ligue:</b> {league_info}\n"
            if market_info:
                text += f"📊 <b>Marché:</b> {market_info}\n"
            
            if odds_info:
                text += f"\n💵 <b>COTES:</b>\n"
                for odd in odds_info:
                    text += f"  • {odd}\n"
            
            text += (
                f"\n💰 <b>RÉSUMÉ FINANCIER</b>\n"
                f"• Montant misé: ${bet.total_stake:.2f}\n"
                f"• Profit net: ${profit_val:+.2f}\n"
                f"• ROI: {roi:.1f}%\n"
                f"• Retour total: ${bet.total_stake + profit_val:.2f}\n"
            )
        else:
            text = (
                f"📋 <b>BET DETAILS</b>\n\n"
                f"{status_emoji} {bet_datetime_et.strftime('%Y-%m-%d at %H:%M:%S')} ET\n"
                f"{type_emoji} Type: <b>{bet_type_display}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            if match_info:
                text += f"🎯 <b>Match:</b> {match_info}\n"
            if league_info:
                text += f"🏆 <b>League:</b> {league_info}\n"
            if market_info:
                text += f"📊 <b>Market:</b> {market_info}\n"
            
            if odds_info:
                text += f"\n💵 <b>ODDS:</b>\n"
                for odd in odds_info:
                    text += f"  • {odd}\n"
            
            text += (
                f"\n💰 <b>FINANCIAL SUMMARY</b>\n"
                f"• Staked: ${bet.total_stake:.2f}\n"
                f"• Net profit: ${profit_val:+.2f}\n"
                f"• ROI: {roi:.1f}%\n"
                f"• Total return: ${bet.total_stake + profit_val:.2f}\n"
            )
        
        # Action buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✏️ Modifier" if lang == 'fr' else "✏️ Edit",
                    callback_data=f"bet_edit_menu_{bet_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete",
                    callback_data=f"bet_delete_confirm_{bet_id}"
                )
            ],
            [InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"bet_category_{bet.bet_type}"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_bet_detail: {e}")
        await callback.answer("❌ Error loading bet details", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_edit_menu_"))
async def callback_bet_edit_menu(callback: types.CallbackQuery):
    """Show edit menu with options"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        if lang == 'fr':
            text = (
                f"✏️ <b>MODIFIER LE BET</b>\n\n"
                f"Que veux-tu modifier?\n"
            )
        else:
            text = (
                f"✏️ <b>EDIT BET</b>\n\n"
                f"What would you like to edit?\n"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="💰 Montant misé" if lang == 'fr' else "💰 Staked amount",
                callback_data=f"bet_edit_amount_{bet_id}"
            )],
            [InlineKeyboardButton(
                text="📈 Profit réalisé" if lang == 'fr' else "📈 Realized profit",
                callback_data=f"bet_edit_profit_{bet_id}"
            )],
            [InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"bet_detail_{bet_id}"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_bet_edit_menu: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_edit_amount_"))
async def callback_bet_edit_amount(callback: types.CallbackQuery):
    """Ask user for new staked amount"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        if lang == 'fr':
            text = (
                f"💰 <b>MODIFIER LE MONTANT MISÉ</b>\n\n"
                f"Montant actuel: ${bet.total_stake:.2f}\n\n"
                f"Entre le nouveau montant:\n"
                f"(Exemple: 800 ou 650.50)\n\n"
                f"👇 Réponds avec juste le chiffre"
            )
        else:
            text = (
                f"💰 <b>EDIT STAKED AMOUNT</b>\n\n"
                f"Current amount: ${bet.total_stake:.2f}\n\n"
                f"Enter the new amount:\n"
                f"(Example: 800 or 650.50)\n\n"
                f"👇 Reply with just the number"
            )
        
        # Store bet_id in user state for next message
        # We'll use callback data to track state
        keyboard = [[InlineKeyboardButton(
            text="❌ Annuler" if lang == 'fr' else "❌ Cancel",
            callback_data=f"bet_edit_menu_{bet_id}"
        )]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Store state for message handler
        USER_EDIT_STATE[user_id] = {'bet_id': bet_id, 'field': 'amount'}
        
    except Exception as e:
        logger.error(f"Error in callback_bet_edit_amount: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_edit_profit_"))
async def callback_bet_edit_profit(callback: types.CallbackQuery):
    """Ask user for new profit amount"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
        
        if lang == 'fr':
            text = (
                f"📈 <b>MODIFIER LE PROFIT</b>\n\n"
                f"Profit actuel: ${profit_val:+.2f}\n\n"
                f"Entre le nouveau profit:\n"
                f"(Exemple: 25.50 ou -10.20)\n\n"
                f"👇 Réponds avec juste le chiffre"
            )
        else:
            text = (
                f"📈 <b>EDIT PROFIT</b>\n\n"
                f"Current profit: ${profit_val:+.2f}\n\n"
                f"Enter the new profit:\n"
                f"(Example: 25.50 or -10.20)\n\n"
                f"👇 Reply with just the number"
            )
        
        keyboard = [[InlineKeyboardButton(
            text="❌ Annuler" if lang == 'fr' else "❌ Cancel",
            callback_data=f"bet_edit_menu_{bet_id}"
        )]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Store state for message handler
        USER_EDIT_STATE[user_id] = {'bet_id': bet_id, 'field': 'profit'}
        
    except Exception as e:
        logger.error(f"Error in callback_bet_edit_profit: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_delete_confirm_"))
async def callback_bet_delete_confirm(callback: types.CallbackQuery):
    """Ask for confirmation before deleting"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
        
        if lang == 'fr':
            text = (
                f"🗑️ <b>SUPPRIMER LE BET</b>\n\n"
                f"⚠️ Es-tu sûr de vouloir supprimer ce bet?\n\n"
                f"• Date: {bet.bet_date}\n"
                f"• Misé: ${bet.total_stake:.2f}\n"
                f"• Profit: ${profit_val:+.2f}\n\n"
                f"Cette action est <b>IRRÉVERSIBLE</b>!"
            )
        else:
            text = (
                f"🗑️ <b>DELETE BET</b>\n\n"
                f"⚠️ Are you sure you want to delete this bet?\n\n"
                f"• Date: {bet.bet_date}\n"
                f"• Staked: ${bet.total_stake:.2f}\n"
                f"• Profit: ${profit_val:+.2f}\n\n"
                f"This action is <b>IRREVERSIBLE</b>!"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="❌ CONFIRMER SUPPRESSION" if lang == 'fr' else "❌ CONFIRM DELETE",
                callback_data=f"bet_delete_execute_{bet_id}"
            )],
            [InlineKeyboardButton(
                text="◀️ Annuler" if lang == 'fr' else "◀️ Cancel",
                callback_data=f"bet_detail_{bet_id}"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_bet_delete_confirm: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("bet_delete_execute_"))
async def callback_bet_delete_execute(callback: types.CallbackQuery):
    """Actually delete the bet and update stats"""
    await callback.answer()
    
    bet_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        bet_type = bet.bet_type
        profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
        stake = bet.total_stake
        bet_date = bet.bet_date
        
        # Delete the bet
        db.delete(bet)
        
        # Update DailyStats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == bet_date
        ).first()
        
        if daily_stat:
            daily_stat.total_bets = max(0, (daily_stat.total_bets or 1) - 1)
            daily_stat.total_staked = max(0, (daily_stat.total_staked or stake) - stake)
            daily_stat.total_profit = (daily_stat.total_profit or profit_val) - profit_val
        
        db.commit()
        
        if lang == 'fr':
            text = (
                f"✅ <b>Bet supprimé avec succès!</b>\n\n"
                f"Le bet a été retiré de tes statistiques."
            )
        else:
            text = (
                f"✅ <b>Bet deleted successfully!</b>\n\n"
                f"The bet has been removed from your stats."
            )
        
        keyboard = [[InlineKeyboardButton(
            text="◀️ Retour à la liste" if lang == 'fr' else "◀️ Back to list",
            callback_data=f"bet_category_{bet_type}"
        )]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in callback_bet_delete_execute: {e}")
        await callback.answer("❌ Error deleting bet", show_alert=True)
        db.rollback()
    finally:
        db.close()


# ========================================
# MESSAGE HANDLER FOR EDIT INPUTS
# ========================================

@router.message(F.text)
async def handle_bet_edit_input(message: types.Message):
    """Handle numeric input for bet editing (amount or profit)"""
    user_id = message.from_user.id
    
    # Check if user is in editing state
    if user_id not in USER_EDIT_STATE:
        return  # Not editing, ignore
    
    state = USER_EDIT_STATE[user_id]
    bet_id = state['bet_id']
    field = state['field']
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(UserBet.id == bet_id, UserBet.user_id == user_id).first()
        
        if not bet:
            await message.answer("❌ Bet not found" if lang == 'en' else "❌ Bet introuvable")
            del USER_EDIT_STATE[user_id]
            return
        
        # Try to parse the number
        try:
            new_value = float(message.text.strip().replace('$', '').replace(',', ''))
        except ValueError:
            await message.answer(
                "❌ Invalid number! Please enter a valid amount (e.g., 750 or 25.50)" if lang == 'en' 
                else "❌ Nombre invalide! Entre un montant valide (ex: 750 ou 25.50)"
            )
            return
        
        if field == 'amount':
            # Update staked amount
            old_amount = bet.total_stake
            bet.total_stake = new_value
            
            # Update DailyStats
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == user_id,
                DailyStats.date == bet.bet_date
            ).first()
            
            if daily_stat:
                daily_stat.total_staked = (daily_stat.total_staked or 0) - old_amount + new_value
            
            db.commit()
            
            profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
            new_roi = (profit_val / new_value * 100) if new_value > 0 else 0
            
            if lang == 'fr':
                text = (
                    f"✅ <b>Montant mis à jour!</b>\n\n"
                    f"• Ancien: ${old_amount:.2f}\n"
                    f"• Nouveau: ${new_value:.2f}\n\n"
                    f"ROI recalculé: {new_roi:.1f}%\n"
                    f"(Profit ${profit_val:.2f} / Misé ${new_value:.2f})"
                )
            else:
                text = (
                    f"✅ <b>Amount updated!</b>\n\n"
                    f"• Old: ${old_amount:.2f}\n"
                    f"• New: ${new_value:.2f}\n\n"
                    f"ROI recalculated: {new_roi:.1f}%\n"
                    f"(Profit ${profit_val:.2f} / Staked ${new_value:.2f})"
                )
            
        else:  # field == 'profit'
            # Update profit
            old_profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
            bet.actual_profit = new_value
            
            # Update DailyStats
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == user_id,
                DailyStats.date == bet.bet_date
            ).first()
            
            if daily_stat:
                daily_stat.total_profit = (daily_stat.total_profit or 0) - old_profit + new_value
            
            db.commit()
            
            new_roi = (new_value / bet.total_stake * 100) if bet.total_stake > 0 else 0
            
            if lang == 'fr':
                text = (
                    f"✅ <b>Profit mis à jour!</b>\n\n"
                    f"• Ancien: ${old_profit:+.2f}\n"
                    f"• Nouveau: ${new_value:+.2f}\n\n"
                    f"ROI recalculé: {new_roi:.1f}%\n"
                    f"(Profit ${new_value:.2f} / Misé ${bet.total_stake:.2f})"
                )
            else:
                text = (
                    f"✅ <b>Profit updated!</b>\n\n"
                    f"• Old: ${old_profit:+.2f}\n"
                    f"• New: ${new_value:+.2f}\n\n"
                    f"ROI recalculated: {new_roi:.1f}%\n"
                    f"(Profit ${new_value:.2f} / Staked ${bet.total_stake:.2f})"
                )
        
        keyboard = [[InlineKeyboardButton(
            text="◀️ Retour aux modifications" if lang == 'fr' else "◀️ Back to edit menu",
            callback_data=f"bet_edit_menu_{bet_id}"
        )]]
        
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Clear edit state
        del USER_EDIT_STATE[user_id]
        
    except Exception as e:
        logger.error(f"Error handling bet edit input: {e}")
        await message.answer("❌ Error updating bet" if lang == 'en' else "❌ Erreur lors de la mise à jour")
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("my_bets_page"))
async def callback_my_bets_legacy(callback: types.CallbackQuery):
    """
    Legacy handler for paginated bet list (if needed in future)
    Format: my_bets_page_{page}
    """
    await callback.answer()
    
    # Parse page number
    parts = callback.data.split('_')
    page = int(parts[3]) if len(parts) > 3 else 1
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Pagination
        per_page = 10
        offset = (page - 1) * per_page
        
        # Get bets ordered by date desc
        total_bets = db.query(UserBet).filter(UserBet.user_id == user_id).count()
        bets = db.query(UserBet).filter(
            UserBet.user_id == user_id
        ).order_by(
            UserBet.created_at.desc()
        ).limit(per_page).offset(offset).all()
        
        if not bets:
            no_bets_msg = "📊 Aucun bet enregistré" if lang == 'fr' else "📊 No bets recorded"
            keyboard = [[InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")]]
            await callback.message.edit_text(
                no_bets_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return
        
        # Build message
        if lang == 'fr':
            title = f"📊 <b>MES BETS</b> (Page {page})\n\n"
        else:
            title = f"📊 <b>MY BETS</b> (Page {page})\n\n"
        
        bet_lines = []
        bet_buttons = []
        for i, bet in enumerate(bets, 1):
            # Get drop event details if available
            drop_info = ""
            if bet.drop_event_id:
                drop_event = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
                if drop_event:
                    match = drop_event.match or "N/A"
                    market = drop_event.market or ""
                    drop_info = f"{match}"
                    if market:
                        drop_info += f" - {market}"
            
            bet_date = bet.bet_date.strftime('%d/%m/%y')
            status_emoji = "✅" if bet.status == 'confirmed' else ("✏️" if bet.status == 'corrected' else "⏳")
            profit_val = bet.actual_profit if (bet.actual_profit is not None) else bet.expected_profit
            roi = (profit_val / bet.total_stake * 100) if bet.total_stake > 0 else 0
            
            if lang == 'fr':
                bet_line = (
                    f"{status_emoji} <b>Bet #{offset + i}</b> - {bet_date}\n"
                    f"   {drop_info}\n"
                    f"   💰 Misé: ${bet.total_stake:.2f}\n"
                    f"   📈 Profit: ${profit_val:.2f} (ROI {roi:.1f}%)\n"
                )
            else:
                bet_line = (
                    f"{status_emoji} <b>Bet #{offset + i}</b> - {bet_date}\n"
                    f"   {drop_info}\n"
                    f"   💰 Staked: ${bet.total_stake:.2f}\n"
                    f"   📈 Profit: ${profit_val:.2f} (ROI {roi:.1f}%)\n"
                )
            
            bet_lines.append(bet_line)
            
            # Add edit/delete buttons for each bet
            edit_text = "✏️ Modifier" if lang == 'fr' else "✏️ Edit"
            delete_text = "🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete"
            bet_buttons.append([
                InlineKeyboardButton(text=edit_text, callback_data=f"edit_bet_{bet.id}"),
                InlineKeyboardButton(text=delete_text, callback_data=f"delete_bet_{bet.id}")
            ])
        
        message_text = title + "\n".join(bet_lines)
        
        # Build keyboard with bet action buttons
        keyboard = bet_buttons.copy()
        
        # Pagination buttons
        nav_buttons = []
        
        total_pages = (total_bets + per_page - 1) // per_page
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_bets_{page-1}"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_bets_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Back to stats button
        back_text = "📊 Stats" if lang == 'en' else "📊 Stats"
        keyboard.append([InlineKeyboardButton(text=back_text, callback_data="my_stats")])
        keyboard.append([InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")])
        
        await callback.message.edit_text(
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing bets: {e}")
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("delete_bet_"))
async def callback_delete_bet(callback: types.CallbackQuery):
    """
    Delete a specific bet
    Format: delete_bet_{bet_id}
    """
    await callback.answer()
    
    try:
        bet_id = int(callback.data.split('_')[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        # Find the bet
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await callback.answer("❌ Bet non trouvé", show_alert=True)
            return
        
        # Update daily stats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == bet.bet_date
        ).first()
        
        if daily_stat:
            daily_stat.total_bets -= 1
            daily_stat.total_staked -= bet.total_stake
            daily_stat.total_profit -= bet.expected_profit
            
            if daily_stat.total_bets <= 0:
                db.delete(daily_stat)
        
        # Update User stats
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.total_bets = max(0, (user.total_bets or 0) - 1)
            user.total_profit = (user.total_profit or 0) - (bet.expected_profit or 0)
            
            if bet.bet_type == "arbitrage":
                user.arbitrage_bets = max(0, (user.arbitrage_bets or 0) - 1)
                user.arbitrage_profit = (user.arbitrage_profit or 0) - (bet.expected_profit or 0)
            elif bet.bet_type == "middle":
                user.middle_bets = max(0, (user.middle_bets or 0) - 1)
                user.middle_profit = (user.middle_profit or 0) - (bet.expected_profit or 0)
            elif bet.bet_type == "good_ev":
                user.good_ev_bets = max(0, (user.good_ev_bets or 0) - 1)
                user.good_ev_profit = (user.good_ev_profit or 0) - (bet.expected_profit or 0)
        
        # Delete the bet
        db.delete(bet)
        db.commit()
        
        await safe_callback_answer(callback, "✅ Bet supprimé!", show_alert=True)
        
        # Refresh the bet list
        await callback_my_bets(callback)
        
    except Exception as e:
        logger.error(f"Error deleting bet: {e}")
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("edit_bet_"))
async def callback_edit_bet(callback: types.CallbackQuery, state: FSMContext):
    """
    Edit a specific bet (stake and profit)
    Format: edit_bet_{bet_id}
    """
    await callback.answer()
    
    try:
        bet_id = int(callback.data.split('_')[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        # Find the bet
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await callback.answer("❌ Bet non trouvé", show_alert=True)
            return
        
        # Get language
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Set FSM state
        await state.set_state(BetEditStates.awaiting_stake)
        old_profit_val = bet.actual_profit if (bet.actual_profit is not None) else bet.expected_profit
        await state.update_data(bet_id=bet_id, old_stake=bet.total_stake, old_profit=old_profit_val)
        
        if lang == 'fr':
            prompt = (
                f"✏️ <b>Modification du Bet #{bet_id}</b>\n\n"
                f"Montant actuel: ${bet.total_stake:.2f}\n"
                f"Profit actuel: ${bet.expected_profit:.2f}\n\n"
                f"Quel est le <b>nouveau montant misé</b>?\n"
                f"(Envoyez le nombre, ex: 750)"
            )
        else:
            prompt = (
                f"✏️ <b>Edit Bet #{bet_id}</b>\n\n"
                f"Current stake: ${bet.total_stake:.2f}\n"
                f"Current profit: ${bet.expected_profit:.2f}\n\n"
                f"What is the <b>new stake amount</b>?\n"
                f"(Send the number, e.g., 750)"
            )
        
        try:
            await callback.message.edit_text(prompt, parse_mode=ParseMode.HTML)
        except Exception:
            await callback.message.answer(prompt, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error starting bet edit: {e}")
        await safe_callback_answer(callback, "❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.message(BetEditStates.awaiting_stake)
async def process_edit_stake(message: types.Message, state: FSMContext):
    """
    Process new stake amount for bet edit
    """
    text = message.text.strip()
    user_id = message.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        try:
            new_stake = float(text)
            if new_stake < 0:
                raise ValueError
            
            # Save to state
            await state.update_data(new_stake=new_stake)
            await state.set_state(BetEditStates.awaiting_profit)
            
            if lang == 'fr':
                prompt = (
                    f"✅ Nouveau montant: ${new_stake:.2f}\n\n"
                    f"Quel est le <b>nouveau profit</b>?\n"
                    f"(Envoyez le nombre, ex: 95.50)"
                )
            else:
                prompt = (
                    f"✅ New stake: ${new_stake:.2f}\n\n"
                    f"What is the <b>new profit</b>?\n"
                    f"(Send the number, e.g., 95.50)"
                )
            
            await message.answer(prompt, parse_mode=ParseMode.HTML)
            
        except ValueError:
            error_msg = "❌ Montant invalide. Envoyez un nombre (ex: 750)" if lang == 'fr' else "❌ Invalid amount. Send a number (e.g., 750)"
            await message.answer(error_msg)
            
    finally:
        db.close()


@router.message(BetEditStates.awaiting_profit)
async def process_edit_profit(message: types.Message, state: FSMContext):
    """
    Process new profit amount and update bet
    """
    text = message.text.strip()
    user_id = message.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        try:
            new_profit = float(text)
            
            # Get state data
            data = await state.get_data()
            bet_id = data.get('bet_id')
            new_stake = data.get('new_stake')
            old_stake = data.get('old_stake')
            old_profit = data.get('old_profit')
            
            # Find and update bet
            bet = db.query(UserBet).filter(
                UserBet.id == bet_id,
                UserBet.user_id == user_id
            ).first()
            
            if not bet:
                await message.answer("❌ Bet non trouvé" if lang == 'fr' else "❌ Bet not found")
                await state.clear()
                return
            
            # Update daily stats (subtract old, add new)
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == user_id,
                DailyStats.date == bet.bet_date
            ).first()
            
            if daily_stat:
                daily_stat.total_staked = daily_stat.total_staked - old_stake + new_stake
                daily_stat.total_profit = daily_stat.total_profit - old_profit + new_profit
            
            # Update bet
            bet.total_stake = new_stake
            bet.actual_profit = new_profit
            bet.status = 'corrected'
            
            db.commit()
            
            await state.clear()
            
            if lang == 'fr':
                success_msg = (
                    f"✅ <b>Bet #{bet_id} modifié!</b>\n\n"
                    f"Nouveau montant: ${new_stake:.2f}\n"
                    f"Nouveau profit: ${new_profit:.2f}"
                )
            else:
                success_msg = (
                    f"✅ <b>Bet #{bet_id} updated!</b>\n\n"
                    f"New stake: ${new_stake:.2f}\n"
                    f"New profit: ${new_profit:.2f}"
                )
            
            await message.answer(success_msg, parse_mode=ParseMode.HTML)
            
        except ValueError:
            error_msg = "❌ Montant invalide. Envoyez un nombre (ex: 95.50)" if lang == 'fr' else "❌ Invalid amount. Send a number (e.g., 95.50)"
            await message.answer(error_msg)
    
    except Exception as e:
        logger.error(f"Error updating bet: {e}")


@router.callback_query(F.data == "month_filter")
async def callback_month_filter(callback: types.CallbackQuery):
    """Show month filter selection menu"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get list of months with bets
        from datetime import date
        today = date.today()
        
        # Generate last 12 months
        months = []
        for i in range(12):
            if i == 0:
                month_date = today
            else:
                # Go back i months
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                month_date = date(year, month, 1)
            
            # Check if there are bets in this month
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = date(month_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
            
            bet_count = db.query(func.count(UserBet.id)).filter(
                UserBet.user_id == user_id,
                UserBet.bet_date >= month_start,
                UserBet.bet_date <= month_end
            ).scalar() or 0
            
            if bet_count > 0:
                months.append((month_date, bet_count))
        
        if lang == 'fr':
            text = "📅 <b>FILTRE PAR MOIS</b>\n\n"
            text += "Sélectionnez un mois pour voir ses statistiques:\n\n"
        else:
            text = "📅 <b>MONTH FILTER</b>\n\n"
            text += "Select a month to view its statistics:\n\n"
        
        keyboard = []
        for month_date, count in months:
            month_label = month_date.strftime("%B %Y")
            month_key = month_date.strftime("%Y_%m")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{month_label} ({count} bets)",
                    callback_data=f"my_stats_{month_key}"
                )
            ])
        
        # Add "All Time" option
        keyboard.append([
            InlineKeyboardButton(
                text="🗓️ Tout Temps" if lang == 'fr' else "🗓️ All Time",
                callback_data="my_stats"
            )
        ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="my_stats"
            )
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in month_filter: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()
