"""
Bet handlers for Good EV and Middle bets
These handlers track bets with potential for losses
"""
from datetime import date
from aiogram import F, types, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from database import SessionLocal
from models.user import User
from models.bet import UserBet, DailyStats
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("good_ev_bet_"))
async def callback_good_ev_bet(callback: types.CallbackQuery):
    """Handle 'I BET' for GOOD EV (Positive EV).

    Supported formats:
      - New alerts (from OddsJam bridge, with DropEvent):
            good_ev_bet_{eid}_{total_stake}_{expected_profit}
      - Legacy calculators / menus (no eid):
            good_ev_bet_{total_stake}_{expected_profit}

    Note: Expected profit is EV-based, actual result can be win or loss.
    """
    logger.info(f"🎯 GOOD EV BET HANDLER CALLED: {callback.data}")
    try:
        await callback.answer("⏳ Enregistrement...", show_alert=False)
    except Exception:
        pass  # Answer already called by middleware
    
    try:
        parts = callback.data.split('_')
        # Default
        eid = None
        if len(parts) >= 6:
            # good_ev_bet_{eid}_{total_stake}_{expected_profit}
            eid = parts[3]
            total_stake = float(parts[4])
            expected_profit = float(parts[5])
        elif len(parts) == 5:
            # Legacy: good_ev_bet_{total_stake}_{expected_profit}
            total_stake = float(parts[3])
            expected_profit = float(parts[4])
        else:
            raise IndexError("Unexpected good_ev_bet format")
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid good_ev_bet callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    today = date.today()
    
    db = SessionLocal()
    try:
        # Get drop data to extract match info, sport, date (only for new-style calls)
        from models.drop_event import DropEvent
        drop = None
        if eid:
            drop = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        
        # Extract match info
        match_name = None
        sport_name = None
        match_date = None
        
        if drop:
            match_name = drop.match or None
            sport_name = drop.league or None  # League usually contains sport info
            
            # Try to parse commence_time from drop
            try:
                drop_data = drop.payload if drop.payload else {}
                commence_time = drop_data.get('commence_time')
                if commence_time:
                    from datetime import datetime
                    dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    match_date = dt.date()
            except Exception as e:
                logger.warning(f"Could not parse commence_time for Good EV bet: {e}")
        
        # Check if already bet on this Good EV call
        # When eid is missing (legacy buttons), fall back to message_id for dedup
        if eid:
            event_hash = f"good_ev_{eid}"
        else:
            event_hash = f"good_ev_msg_{callback.message.message_id}"
        
        existing = db.query(UserBet).filter(
            UserBet.user_id == user_id,
            UserBet.event_hash == event_hash,
            UserBet.bet_type == 'good_ev'
        ).first()
        
        if existing:
            await callback.answer("✅ Déjà enregistré", show_alert=True)
            return
        
        # Create bet record with match info
        user_bet = UserBet(
            user_id=user_id,
            drop_event_id=drop.id if drop else None,
            event_hash=event_hash,
            bet_type='good_ev',
            bet_date=today,
            match_name=match_name,
            sport=sport_name,
            match_date=match_date,
            total_stake=total_stake,
            expected_profit=expected_profit,  # EV-based expected value
            actual_profit=None,  # Will be set when confirmed (can be negative!)
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
            daily_stat.total_profit += expected_profit  # Expected, not guaranteed
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
        
        # Update user's Good EV stats
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.good_ev_bets = (user.good_ev_bets or 0) + 1
        
        db.commit()
        db.flush()
        bet_id = user_bet.id
        
        # Fetch language
        lang = user.language if user else 'en'
        
        # 🎯 Calculate REAL profit if you WIN from drop data (not callback expected_profit)
        win_profit = expected_profit  # Default to callback value
        if drop and drop.payload:
            try:
                drop_data = drop.payload
                odds_str = str(drop_data.get('odds', '0')).replace('+', '')
                odds_value = int(odds_str) if odds_str else 0
                if odds_value > 0:  # American positive
                    decimal_odds = 1 + (odds_value / 100)
                elif odds_value < 0:  # American negative
                    decimal_odds = 1 + (100 / abs(odds_value))
                else:
                    decimal_odds = 2.0
                win_profit = total_stake * (decimal_odds - 1)
            except Exception as e:
                logger.warning(f"Could not calculate win profit: {e}")
        
        if lang == 'fr':
            confirmation = (
                f"\n\n✅ <b>BET GOOD EV ENREGISTRÉ!</b>\n\n"
                f"📊 <b>Ce pari:</b>\n"
                f"• Misé: ${total_stake:.2f}\n"
                f"• Profit si tu GAGNES: <b>${win_profit:.2f}</b>\n\n"
                f"📊 <b>Aujourd'hui (total):</b>\n"
                f"• Paris: {daily_stat.total_bets}\n"
                f"• Misé total: ${daily_stat.total_staked:.2f}\n"
                f"• EV total: ${daily_stat.total_profit:.2f}\n\n"
                f"⚠️ <i>Good EV: tu perds ~50% du temps, profit long terme</i>"
            )
            undo_text = "❌ Erreur, je n'ai pas parié"
        else:
            confirmation = (
                f"\n\n✅ <b>GOOD EV BET RECORDED!</b>\n\n"
                f"📊 <b>This bet:</b>\n"
                f"• Staked: ${total_stake:.2f}\n"
                f"• Profit if you WIN: <b>${win_profit:.2f}</b>\n\n"
                f"📊 <b>Today (total):</b>\n"
                f"• Bets: {daily_stat.total_bets}\n"
                f"• Total staked: ${daily_stat.total_staked:.2f}\n"
                f"• Total EV: ${daily_stat.total_profit:.2f}\n\n"
                f"⚠️ <i>Good EV: you lose ~50% of time, long-term profit</i>"
            )
            undo_text = "❌ Mistake, I didn't bet"
        
        # Update keyboard
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

                if cb and cb.startswith("good_ev_bet_"):
                    checked_text = "✅ " + text.replace("💰 ", "")
                    new_row.append(InlineKeyboardButton(text=checked_text, callback_data=cb))
                else:
                    if url:
                        new_row.append(InlineKeyboardButton(text=text, url=url))
                    elif cb:
                        new_row.append(InlineKeyboardButton(text=text, callback_data=cb))
                    else:
                        new_row.append(InlineKeyboardButton(text=text, callback_data="noop"))
            if new_row:
                new_kb.append(new_row)

        new_kb.append([InlineKeyboardButton(text=undo_text, callback_data=f"undo_bet_{bet_id}")])

        try:
            await callback.message.edit_text(
                callback.message.text + confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
        except Exception:
            await callback.message.answer(
                confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
        
    except Exception as e:
        logger.error(f"Error recording Good EV bet: {e}")
        await callback.answer("❌ Erreur lors de l'enregistrement", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data.startswith("middle_bet_"))
async def callback_middle_bet(callback: types.CallbackQuery):
    """
    Handle 'I BET' button click for MIDDLE
    Supported formats:
      - New alerts (with DropEvent):
            middle_bet_{eid}_{total_stake}_{middle_profit}
      - Legacy calculators / menus (no eid):
            middle_bet_{total_stake}_{middle_profit}
    Note: Middle hits rarely (~15%), usually small loss
    """
    logger.info(f"🎯 MIDDLE BET HANDLER CALLED: {callback.data}")
    try:
        await callback.answer("⏳ Enregistrement...", show_alert=False)
    except Exception:
        pass  # Answer already called by middleware
    
    try:
        parts = callback.data.split('_')
        eid = None
        no_middle_profit = 0.0  # MIN profit (guaranteed)
        
        if len(parts) >= 6:
            # NEW FORMAT: middle_bet_{eid}_{total_stake}_{no_middle_profit}_{middle_profit}
            eid = parts[2]
            total_stake = float(parts[3])
            no_middle_profit = float(parts[4])
            middle_profit = float(parts[5])
        elif len(parts) >= 5:
            # OLD FORMAT: middle_bet_{eid}_{total_stake}_{middle_profit}
            # (no_middle_profit missing, will calculate from drop)
            eid = parts[2]
            total_stake = float(parts[3])
            middle_profit = float(parts[4])
        elif len(parts) == 4:
            # Legacy: middle_bet_{total_stake}_{middle_profit}
            total_stake = float(parts[2])
            middle_profit = float(parts[3])
        else:
            raise IndexError("Unexpected middle_bet format")
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid middle_bet callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
        return
    
    user_id = callback.from_user.id
    today = date.today()
    
    db = SessionLocal()
    try:
        # Get drop data to extract match info, sport, date (only for new-style calls)
        from models.drop_event import DropEvent
        drop = None
        if eid:
            drop = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        
        # Extract match info
        match_name = None
        sport_name = None
        match_date = None
        
        if drop:
            match_name = drop.match or None
            sport_name = drop.league or None
            
            # Try to parse commence_time from drop
            try:
                drop_data = drop.payload if drop.payload else {}
                commence_time = drop_data.get('commence_time')
                if commence_time:
                    from datetime import datetime
                    dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    match_date = dt.date()
            except Exception as e:
                logger.warning(f"Could not parse commence_time for Middle bet: {e}")
        
        # Check if already bet on this Middle call
        if eid:
            event_hash = f"middle_{eid}"
        else:
            event_hash = f"middle_msg_{callback.message.message_id}"
        
        existing = db.query(UserBet).filter(
            UserBet.user_id == user_id,
            UserBet.event_hash == event_hash,
            UserBet.bet_type == 'middle'
        ).first()
        
        if existing:
            await callback.answer("✅ Déjà enregistré", show_alert=True)
            return
        
        # Create bet record with match info
        user_bet = UserBet(
            user_id=user_id,
            drop_event_id=drop.id if drop else None,
            event_hash=event_hash,
            bet_type='middle',
            bet_date=today,
            match_name=match_name,
            sport=sport_name,
            match_date=match_date,
            total_stake=total_stake,
            expected_profit=middle_profit,  # Jackpot profit if middle hits
            actual_profit=None,
            status='pending'
        )
        db.add(user_bet)
        
        # Update daily stats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today
        ).first()
        
        if daily_stat:
            daily_stat.total_bets += 1
            daily_stat.total_staked += total_stake
            daily_stat.total_profit += middle_profit  # Potential profit
        else:
            daily_stat = DailyStats(
                user_id=user_id,
                date=today,
                total_bets=1,
                total_staked=total_stake,
                total_profit=middle_profit,
                confirmed=False
            )
            db.add(daily_stat)
        
        # Update user's Middle stats
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.middle_bets = (user.middle_bets or 0) + 1
        
        db.commit()
        db.flush()
        bet_id = user_bet.id
        
        lang = user.language if user else 'en'
        
        # Base display values from callback_data
        min_profit = no_middle_profit
        display_middle_profit = middle_profit

        # If we have a structured DropEvent payload, recompute display profits
        # from the same classifier used for the rich Middle alert, so the
        # "Ce bet" footer matches the header (including WIN+PUSH vs true jackpot).
        if drop and drop.payload:
            try:
                drop_data = drop.payload
                side_a = drop_data.get('side_a', {})
                side_b = drop_data.get('side_b', {})
                if side_a and side_b and 'odds' in side_a and 'odds' in side_b and 'line' in side_a and 'line' in side_b:
                    from utils.middle_calculator import classify_middle_type
                    cls = classify_middle_type(side_a, side_b, total_stake)

                    profit_a_only = cls['profit_scenario_1']
                    profit_b_only = cls['profit_scenario_3']
                    profit_middle_cls = cls['profit_scenario_2']

                    # Align MIN profit with header (guaranteed arb component)
                    min_profit = min(profit_a_only, profit_b_only)

                    # Detect hybrid WIN+PUSH middle structures
                    try:
                        sa_sel = (side_a.get('selection') or '').lower()
                        sb_sel = (side_b.get('selection') or '').lower()
                        try:
                            line_a = float(side_a['line'])
                            line_b = float(side_b['line'])
                        except Exception:
                            line_a = None
                            line_b = None

                        over_line = None
                        under_line = None
                        if 'over' in sa_sel:
                            over_line = line_a
                        if 'over' in sb_sel:
                            over_line = line_b if over_line is None else over_line
                        if 'under' in sa_sel:
                            under_line = line_a
                        if 'under' in sb_sel:
                            under_line = line_b if under_line is None else under_line

                        def is_half(x: float) -> bool:
                            return abs((x - int(x)) - 0.5) < 1e-6

                        def is_integer(x: float) -> bool:
                            return abs(x - round(x)) < 1e-6

                        stake_a = cls['stake_a']; stake_b = cls['stake_b']
                        ret_a = cls['return_a']; ret_b = cls['return_b']

                        if over_line is not None and under_line is not None:
                            # Case: Over integer + Under (integer+0.5) → WIN+PUSH at integer
                            if is_integer(over_line) and is_half(under_line) and abs(under_line - over_line - 0.5) < 1e-6:
                                if 'over' in sa_sel:
                                    profit_middle_cls = stake_a + ret_b - total_stake
                                else:
                                    profit_middle_cls = stake_b + ret_a - total_stake
                            # Case: Under integer + Over (integer-0.5) → WIN+PUSH at integer
                            elif is_integer(under_line) and is_half(over_line) and abs(under_line - over_line - 0.5) < 1e-6:
                                if 'under' in sa_sel:
                                    profit_middle_cls = stake_a + ret_b - total_stake
                                else:
                                    profit_middle_cls = stake_b + ret_a - total_stake
                    except Exception:
                        # If detection fails, keep classifier's middle profit
                        pass

                    display_middle_profit = profit_middle_cls
            except Exception as e:
                logger.warning(f"Could not extract Middle profits from drop: {e}")

        if lang == 'fr':
            confirmation = (
                f"\n\n✅ <b>BET MIDDLE ENREGISTRÉ!</b>\n\n"
                f"📊 Ce bet:\n"
                f"• Misé: ${total_stake:.2f}\n"
                f"• Profit MIN garanti: ${min_profit:+.2f}\n"
                f"• Jackpot si middle: ${display_middle_profit:+.2f}\n\n"
                f"⚠️ <i>Middle: petite perte fréquente, GROS gain rare</i>"
            )
            undo_text = "❌ Erreur, je n'ai pas parié"
        else:
            confirmation = (
                f"\n\n✅ <b>MIDDLE BET RECORDED!</b>\n\n"
                f"📊 This bet:\n"
                f"• Staked: ${total_stake:.2f}\n"
                f"• MIN profit guaranteed: ${min_profit:+.2f}\n"
                f"• Jackpot if middle: ${display_middle_profit:+.2f}\n\n"
                f"⚠️ <i>Middle: small frequent loss, BIG rare gain</i>"
            )
            undo_text = "❌ Mistake, I didn't bet"
        
        # Update keyboard
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

                if cb and cb.startswith("middle_bet_"):
                    checked_text = "✅ " + text.replace("💰 ", "")
                    new_row.append(InlineKeyboardButton(text=checked_text, callback_data=cb))
                else:
                    if url:
                        new_row.append(InlineKeyboardButton(text=text, url=url))
                    elif cb:
                        new_row.append(InlineKeyboardButton(text=text, callback_data=cb))
                    else:
                        new_row.append(InlineKeyboardButton(text=text, callback_data="noop"))
            if new_row:
                new_kb.append(new_row)

        new_kb.append([InlineKeyboardButton(text=undo_text, callback_data=f"undo_bet_{bet_id}")])

        try:
            await callback.message.edit_text(
                callback.message.text + confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
        except Exception:
            await callback.message.answer(
                confirmation,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb)
            )
        
    except Exception as e:
        logger.error(f"Error recording Middle bet: {e}")
        await callback.answer("❌ Erreur lors de l'enregistrement", show_alert=True)
        db.rollback()
    finally:
        db.close()
