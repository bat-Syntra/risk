"""
Step 2 handlers for intelligent questionnaire system
"""
import logging
from datetime import date, timedelta
from aiogram import Router, F, types
from aiogram.enums import ParseMode
from sqlalchemy import and_

from models.user import User
from models.bet import UserBet
from database import SessionLocal

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("match_started_"))
async def handle_match_started(callback: types.CallbackQuery):
    """
    Handle response to "Has the match started?"
    Format: match_started_{bet_id}_yes/no
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        answer = parts[3]  # 'yes' or 'no'
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            if answer == 'yes':
                # Match has started → Send result questions
                await send_result_questions(callback, bet, lang, db)
            else:
                # Match not started → Ask if they know the date
                await ask_match_date(callback, bet, lang)
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in handle_match_started: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


async def send_result_questions(callback: types.CallbackQuery, bet: UserBet, lang: str, db):
    """
    Send the actual result questions (Step 2A)
    """
    bet_type = bet.bet_type
    match_name = bet.match_name or "Match"
    
    # Get odds info
    odds_info = ""
    if bet.drop_event and bet.drop_event.payload:
        try:
            drop_data = bet.drop_event.payload
            outcomes = drop_data.get('outcomes', [])
            if len(outcomes) >= 2:
                o1, o2 = outcomes[0], outcomes[1]
                odds1 = o1.get('odds', 0)
                odds2 = o2.get('odds', 0)
                
                # Convert odds to string safely
                if isinstance(odds1, str):
                    odds1_str = odds1
                else:
                    odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                
                if isinstance(odds2, str):
                    odds2_str = odds2
                else:
                    odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                
                casino1 = o1.get('casino', 'N/A')
                casino2 = o2.get('casino', 'N/A')
                outcome1 = o1.get('outcome', 'N/A')
                outcome2 = o2.get('outcome', 'N/A')
                
                if lang == 'fr':
                    odds_info = (
                        f"\n📊 <b>Détails:</b>\n"
                        f"• [{casino1}] {outcome1}: {odds1_str}\n"
                        f"• [{casino2}] {outcome2}: {odds2_str}\n"
                    )
                else:
                    odds_info = (
                        f"\n📊 <b>Details:</b>\n"
                        f"• [{casino1}] {outcome1}: {odds1_str}\n"
                        f"• [{casino2}] {outcome2}: {odds2_str}\n"
                    )
        except Exception as e:
            logger.warning(f"Could not extract odds info: {e}")
    
    if bet_type == 'middle':
        # Middle bet questions
        jackpot_profit = bet.expected_profit if bet.expected_profit else 0
        
        # Calculate profits for each scenario
        casino1_profit = 0.0
        casino2_profit = 0.0
        casino1_name = "Casino A"
        casino2_name = "Casino B"
        
        if bet.drop_event and bet.drop_event.payload:
            try:
                drop_data = bet.drop_event.payload
                side_a = drop_data.get('side_a', {})
                side_b = drop_data.get('side_b', {})
                
                if side_a and side_b:
                    from utils.middle_calculator import classify_middle_type
                    cls = classify_middle_type(side_a, side_b, bet.total_stake)
                    
                    # Get casino names
                    casino1_name = side_a.get('casino', 'Casino A')
                    casino2_name = side_b.get('casino', 'Casino B')
                    
                    # Profits when only one casino wins
                    casino1_profit = cls['profit_scenario_1']  # Side A wins, Side B loses
                    casino2_profit = cls['profit_scenario_3']  # Side B wins, Side A loses
            except Exception as e:
                logger.warning(f"Could not calculate middle profits: {e}")
        
        if lang == 'fr':
            text = (
                f"🎲 <b>MIDDLE - RÉSULTAT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Misé total: ${bet.total_stake:.2f}\n"
                f"💰 Si arbitrage: ${min(casino1_profit, casino2_profit):+.2f}\n"
                f"🎰 Si JACKPOT: ${jackpot_profit:+.2f}\n\n"
                f"❓ <b>Quel est le résultat?</b>"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"🎰 JACKPOT! (les 2) - ${jackpot_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_jackpot")],
                [types.InlineKeyboardButton(text=f"✅ {casino1_name} seul - ${casino1_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_casino1")],
                [types.InlineKeyboardButton(text=f"✅ {casino2_name} seul - ${casino2_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_casino2")],
                [types.InlineKeyboardButton(text="❌ Aucun n'a gagné (perdu)", callback_data=f"middle_outcome_{bet.id}_lost")]
            ])
        else:
            text = (
                f"🎲 <b>MIDDLE - RESULT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Total staked: ${bet.total_stake:.2f}\n"
                f"💰 If arbitrage: ${min(casino1_profit, casino2_profit):+.2f}\n"
                f"🎰 If JACKPOT: ${jackpot_profit:+.2f}\n\n"
                f"❓ <b>What's the result?</b>"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"🎰 JACKPOT! (both) - ${jackpot_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_jackpot")],
                [types.InlineKeyboardButton(text=f"✅ {casino1_name} only - ${casino1_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_casino1")],
                [types.InlineKeyboardButton(text=f"✅ {casino2_name} only - ${casino2_profit:+.2f}", callback_data=f"middle_outcome_{bet.id}_casino2")],
                [types.InlineKeyboardButton(text="❌ None won (lost)", callback_data=f"middle_outcome_{bet.id}_lost")]
            ])
    
    elif bet_type == 'arbitrage':
        guaranteed_profit = bet.expected_profit if bet.expected_profit else 0
        roi_percent = (guaranteed_profit / bet.total_stake * 100) if bet.total_stake > 0 else 0
        
        # Extract casino profits from drop_event
        casino1_profit = 0
        casino2_profit = 0
        casino1_name = "Casino A"
        casino2_name = "Casino B"
        
        if bet.drop_event and bet.drop_event.payload:
            try:
                drop_data = bet.drop_event.payload
                outcomes = drop_data.get('outcomes', [])
                if len(outcomes) >= 2:
                    o1, o2 = outcomes[0], outcomes[1]
                    casino1_name = o1.get('casino', 'Casino A')
                    casino2_name = o2.get('casino', 'Casino B')
                    
                    # Calculate profit for each casino win
                    stake1 = o1.get('stake', bet.total_stake / 2)
                    stake2 = o2.get('stake', bet.total_stake / 2)
                    payout1 = o1.get('payout', 0)
                    payout2 = o2.get('payout', 0)
                    
                    casino1_profit = payout1 - bet.total_stake
                    casino2_profit = payout2 - bet.total_stake
            except Exception as e:
                logger.warning(f"Could not calculate casino profits: {e}")
        
        if lang == 'fr':
            text = (
                f"✅ <b>ARBITRAGE - RÉSULTAT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Misé total: ${bet.total_stake:.2f}\n"
                f"💰 Profit garanti: ${guaranteed_profit:+.2f} ({roi_percent:.2f}%)\n\n"
                f"❓ <b>Quel casino a gagné?</b>"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"🎰 {casino1_name} (${casino1_profit:+.2f})", callback_data=f"arb_outcome_{bet.id}_casino1")],
                [types.InlineKeyboardButton(text=f"🎰 {casino2_name} (${casino2_profit:+.2f})", callback_data=f"arb_outcome_{bet.id}_casino2")],
                [types.InlineKeyboardButton(text="❌ Problème/Perdu", callback_data=f"arb_outcome_{bet.id}_lost")]
            ])
        else:
            text = (
                f"✅ <b>ARBITRAGE - RESULT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Total staked: ${bet.total_stake:.2f}\n"
                f"💰 Guaranteed profit: ${guaranteed_profit:+.2f} ({roi_percent:.2f}%)\n\n"
                f"❓ <b>Which casino won?</b>"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"🎰 {casino1_name} (${casino1_profit:+.2f})", callback_data=f"arb_outcome_{bet.id}_casino1")],
                [types.InlineKeyboardButton(text=f"🎰 {casino2_name} (${casino2_profit:+.2f})", callback_data=f"arb_outcome_{bet.id}_casino2")],
                [types.InlineKeyboardButton(text="❌ Problem/Lost", callback_data=f"arb_outcome_{bet.id}_lost")]
            ])
    
    else:  # good_ev
        expected_profit = bet.expected_profit if bet.expected_profit else 0
        
        # Calculate potential payout from odds
        potential_payout = 0
        if bet.drop_event and bet.drop_event.payload:
            try:
                drop_data = bet.drop_event.payload
                outcomes = drop_data.get('outcomes', [])
                if len(outcomes) >= 1:
                    potential_payout = outcomes[0].get('payout', 0)
            except Exception as e:
                logger.warning(f"Could not calculate potential payout: {e}")
        
        if lang == 'fr':
            text = (
                f"📈 <b>GOOD EV - RÉSULTAT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Misé: ${bet.total_stake:.2f}\n"
                f"💰 Si win: ${potential_payout:.2f} (profit: ${potential_payout - bet.total_stake:+.2f})\n"
                f"📊 EV prévu: ${expected_profit:+.2f}\n\n"
                f"As-tu gagné ou perdu?"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ GAGNÉ", callback_data=f"ev_outcome_{bet.id}_won")],
                [types.InlineKeyboardButton(text="❌ PERDU", callback_data=f"ev_outcome_{bet.id}_lost")],
                [types.InlineKeyboardButton(text="⚖️ PUSH", callback_data=f"ev_outcome_{bet.id}_push")]
            ])
        else:
            text = (
                f"📈 <b>GOOD EV - RESULT</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{odds_info}\n"
                f"💵 Staked: ${bet.total_stake:.2f}\n"
                f"💰 If win: ${potential_payout:.2f} (profit: ${potential_payout - bet.total_stake:+.2f})\n"
                f"📊 Expected EV: ${expected_profit:+.2f}\n\n"
                f"Did you win or lose?"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ WON", callback_data=f"ev_outcome_{bet.id}_won")],
                [types.InlineKeyboardButton(text="❌ LOST", callback_data=f"ev_outcome_{bet.id}_lost")],
                [types.InlineKeyboardButton(text="⚖️ PUSH", callback_data=f"ev_outcome_{bet.id}_push")]
            ])
    
    await callback.message.edit_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def ask_match_date(callback: types.CallbackQuery, bet: UserBet, lang: str):
    """
    Ask if user knows the match date (Step 2B)
    """
    match_name = bet.match_name or "Match"
    sport_name = bet.sport or ""
    
    # Get bet details
    bet_date_str = bet.bet_date.strftime("%Y-%m-%d") if bet.bet_date else "N/A"
    sport_line = f"🏆 {sport_name}\n" if sport_name else ""
    
    if lang == 'fr':
        text = (
            f"📅 <b>DATE DU MATCH</b>\n\n"
            f"⚽ <b>{match_name}</b>\n"
            f"{sport_line}"
            f"📅 Bet placé: {bet_date_str}\n"
            f"💵 Misé: ${bet.total_stake:.2f}\n\n"
            f"❓ <b>Connais-tu la date du match?</b>"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📅 Demain", callback_data=f"set_matchdate_{bet.id}_tomorrow")],
            [types.InlineKeyboardButton(text="📅 Après-demain", callback_data=f"set_matchdate_{bet.id}_day2")],
            [types.InlineKeyboardButton(text="📅 Dans 3 jours", callback_data=f"set_matchdate_{bet.id}_day3")],
            [types.InlineKeyboardButton(text="🤷 Je ne sais pas", callback_data=f"set_matchdate_{bet.id}_unknown")]
        ])
    else:
        text = (
            f"📅 <b>MATCH DATE</b>\n\n"
            f"⚽ <b>{match_name}</b>\n"
            f"{sport_line}"
            f"📅 Bet placed: {bet_date_str}\n"
            f"💵 Staked: ${bet.total_stake:.2f}\n\n"
            f"❓ <b>Do you know the match date?</b>"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📅 Tomorrow", callback_data=f"set_matchdate_{bet.id}_tomorrow")],
            [types.InlineKeyboardButton(text="📅 Day after tomorrow", callback_data=f"set_matchdate_{bet.id}_day2")],
            [types.InlineKeyboardButton(text="📅 In 3 days", callback_data=f"set_matchdate_{bet.id}_day3")],
            [types.InlineKeyboardButton(text="🤷 I don't know", callback_data=f"set_matchdate_{bet.id}_unknown")]
        ])
    
    await callback.message.edit_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("set_matchdate_"))
async def handle_set_match_date(callback: types.CallbackQuery):
    """
    Handle match date selection
    Format: set_matchdate_{bet_id}_tomorrow/day2/day3/unknown
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        date_option = parts[3]
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            if date_option == 'unknown':
                # User doesn't know - ask again tomorrow
                if lang == 'fr':
                    await callback.message.edit_text(
                        callback.message.text + "\n\n🤷 <b>Pas de problème!</b>\n"
                        "Je te redemanderai demain.",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None
                    )
                else:
                    await callback.message.edit_text(
                        callback.message.text + "\n\n🤷 <b>No problem!</b>\n"
                        "I'll ask you again tomorrow.",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None
                    )
            else:
                # Calculate the date
                today = date.today()
                if date_option == 'tomorrow':
                    match_date = today + timedelta(days=1)
                elif date_option == 'day2':
                    match_date = today + timedelta(days=2)
                elif date_option == 'day3':
                    match_date = today + timedelta(days=3)
                else:
                    await callback.answer("❌ Option invalide", show_alert=True)
                    return
                
                # Save the date
                bet.match_date = match_date
                db.commit()
                
                if lang == 'fr':
                    await callback.message.edit_text(
                        callback.message.text + f"\n\n✅ <b>Date enregistrée: {match_date.strftime('%d/%m/%Y')}</b>\n"
                        "Je te redemanderai le lendemain du match!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None
                    )
                else:
                    await callback.message.edit_text(
                        callback.message.text + f"\n\n✅ <b>Date saved: {match_date.strftime('%m/%d/%Y')}</b>\n"
                        "I'll ask you the day after the match!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None
                    )
            
        except Exception as e:
            logger.error(f"Error setting match date: {e}")
            await callback.answer("❌ Erreur", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in handle_set_match_date: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
