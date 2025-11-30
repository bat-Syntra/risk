"""
Middle Outcome Tracker - Questionnaire pour confirmer si le middle a hit (jackpot) ou pas.

Ce module envoie un questionnaire aux utilisateurs après le match pour demander si le middle a hit.
"""

import logging
from datetime import datetime, timedelta, date
from aiogram import Router, F, types
from aiogram.enums import ParseMode
from sqlalchemy import and_
from typing import Optional

from models.user import User
from models.bet import UserBet, DailyStats
from database import SessionLocal
from bot.feedback_vouch_handler import get_feedback_vouch_buttons
from bot.pending_confirmations import reset_user_notification

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("arb_outcome_"))
async def callback_arb_outcome(callback: types.CallbackQuery):
    """
    Handle arbitrage outcome confirmation (won or lost).
    
    Format: arb_outcome_<bet_id>_<outcome>
    where outcome = 'won' or 'lost'
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        outcome = parts[3]  # 'won' or 'lost'
        
        if outcome not in ['won', 'lost']:
            await callback.answer("❌ Outcome invalide", show_alert=True)
            return
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            if bet.bet_type != 'arbitrage':
                await callback.answer("❌ Ce n'est pas un Arbitrage bet", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            # Update bet
            if outcome == 'won':
                bet.actual_profit = bet.expected_profit  # Profit garanti
                bet.status = 'won'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n✅ <b>ARBITRAGE CONFIRMÉ!</b>\n\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"🎯 Arbitrage réussi!"
                    )
                else:
                    result_text = (
                        f"\n\n✅ <b>ARBITRAGE CONFIRMED!</b>\n\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"🎯 Arbitrage successful!"
                    )
            else:
                # Lost (shouldn't happen for arbitrage, but handle it)
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n❌ <b>PROBLÈME ARBITRAGE</b>\n\n"
                        f"💰 Perte: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"⚠️ Contacte le support si besoin"
                    )
                else:
                    result_text = (
                        f"\n\n❌ <b>ARBITRAGE PROBLEM</b>\n\n"
                        f"💰 Loss: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"⚠️ Contact support if needed"
                    )
            
            # Update daily stats
            bet_date = bet.bet_date
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == bet.user_id,
                DailyStats.date == bet_date
            ).first()
            
            if daily_stat:
                daily_stat.total_profit -= bet.expected_profit
                daily_stat.total_profit += bet.actual_profit
                daily_stat.confirmed = True
            
            db.commit()
            
            # Check if user can be unblocked
            reset_user_notification(bet.user_id)
            
            # Update message with feedback buttons
            try:
                original_text = callback.message.text or callback.message.caption or ""
                is_winning = bet.status == 'won' and bet.actual_profit and bet.actual_profit > 0
                final_keyboard = get_feedback_vouch_buttons(bet.id, is_winning, lang)
                
                await callback.message.edit_text(
                    original_text + result_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=final_keyboard
                )
            except Exception as e:
                logger.error(f"Could not edit message: {e}")
                await callback.answer(result_text.replace('<b>', '').replace('</b>', ''), show_alert=True)
        
        except Exception as e:
            logger.error(f"Error processing arb outcome: {e}")
            await callback.answer("❌ Erreur lors de la confirmation", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_arb_outcome: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("ev_outcome_"))
async def callback_ev_outcome(callback: types.CallbackQuery):
    """
    Handle Good EV outcome confirmation (won or lost).
    
    Format: ev_outcome_<bet_id>_<outcome>
    where outcome = 'won' or 'lost'
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        outcome = parts[3]  # 'won' or 'lost'
        
        if outcome not in ['won', 'lost']:
            await callback.answer("❌ Outcome invalide", show_alert=True)
            return
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            if bet.bet_type != 'good_ev':
                await callback.answer("❌ Ce n'est pas un Good EV bet", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            # Update bet
            if outcome == 'won':
                # For Good EV, we need to calculate actual profit based on odds
                # For now, use expected_profit as estimate (actual would need odds * stake)
                bet.actual_profit = bet.expected_profit * 2  # Rough estimate
                bet.status = 'won'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n🎯 <b>BET GOOD EV CONFIRMÉ!</b>\n\n"
                        f"✅ Gagné!\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n"
                    )
                else:
                    result_text = (
                        f"\n\n🎯 <b>GOOD EV BET CONFIRMED!</b>\n\n"
                        f"✅ Won!\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n"
                    )
            else:
                # Lost
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n📊 <b>BET GOOD EV CONFIRMÉ</b>\n\n"
                        f"❌ Perdu\n"
                        f"💰 Perte: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"💡 Sur le long terme, l'EV+ est profitable!"
                    )
                else:
                    result_text = (
                        f"\n\n📊 <b>GOOD EV BET CONFIRMED</b>\n\n"
                        f"❌ Lost\n"
                        f"💰 Loss: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"💡 In the long run, +EV is profitable!"
                    )
            
            # Update daily stats
            bet_date = bet.bet_date
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == bet.user_id,
                DailyStats.date == bet_date
            ).first()
            
            if daily_stat:
                daily_stat.total_profit -= bet.expected_profit
                daily_stat.total_profit += bet.actual_profit
                daily_stat.confirmed = True
            
            db.commit()
            
            # Check if user can be unblocked
            reset_user_notification(bet.user_id)
            
            # Update message with feedback buttons
            try:
                original_text = callback.message.text or callback.message.caption or ""
                is_winning = bet.status == 'won' and bet.actual_profit and bet.actual_profit > 0
                final_keyboard = get_feedback_vouch_buttons(bet.id, is_winning, lang)
                
                await callback.message.edit_text(
                    original_text + result_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=final_keyboard
                )
            except Exception as e:
                logger.error(f"Could not edit message: {e}")
                await callback.answer(result_text.replace('<b>', '').replace('</b>', ''), show_alert=True)
        
        except Exception as e:
            logger.error(f"Error processing ev outcome: {e}")
            await callback.answer("❌ Erreur lors de la confirmation", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_ev_outcome: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("middle_outcome_"))
async def callback_middle_outcome(callback: types.CallbackQuery):
    """
    Handle middle outcome confirmation (jackpot, arb, or lost).
    
    Format: middle_outcome_<bet_id>_<outcome>
    where outcome = 'jackpot' (both won), 'arb' (one won, min profit), or 'lost' (error)
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        outcome = parts[3]  # 'jackpot', 'arb', or 'lost'
        
        if outcome not in ['jackpot', 'arb', 'lost']:
            await callback.answer("❌ Outcome invalide", show_alert=True)
            return
        
        db = SessionLocal()
        try:
            # Get the bet
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            if bet.bet_type != 'middle':
                await callback.answer("❌ Ce n'est pas un Middle bet", show_alert=True)
                return
            
            # Get user for language
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            # Calculate min_profit (arbitrage profit) from drop data
            min_profit = 0.0
            if bet.drop_event and bet.drop_event.payload:
                try:
                    import json
                    drop_data = bet.drop_event.payload
                    side_a = drop_data.get('side_a', {})
                    side_b = drop_data.get('side_b', {})
                    
                    # Validate that side_a and side_b have required fields
                    if side_a and side_b and 'odds' in side_a and 'odds' in side_b and 'line' in side_a and 'line' in side_b:
                        from utils.middle_calculator import classify_middle_type
                        cls = classify_middle_type(side_a, side_b, bet.total_stake)
                        min_profit = min(cls['profit_scenario_1'], cls['profit_scenario_3'])
                    else:
                        logger.warning(f"Missing required fields in side_a or side_b for bet {bet.id}")
                except Exception as e:
                    logger.warning(f"Could not calculate min_profit: {e}")
            
            # Update bet based on outcome
            if outcome == 'jackpot':
                # 🎰 JACKPOT! Les DEUX paris ont gagné
                # actual_profit = expected_profit (which is the jackpot profit)
                bet.actual_profit = bet.expected_profit
                bet.status = 'won'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n🎰🎰🎰 <b>JACKPOT MIDDLE!</b> 🎰🎰🎰\n\n"
                        f"✅ Les DEUX paris ont gagné!\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"🔥 Félicitations! 🔥"
                    )
                else:
                    result_text = (
                        f"\n\n🎰🎰🎰 <b>JACKPOT MIDDLE!</b> 🎰🎰🎰\n\n"
                        f"✅ BOTH bets won!\n"
                        f"💰 Profit: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"🔥 Congratulations! 🔥"
                    )
            
            elif outcome == 'arb':
                # ✅ ARBITRAGE! Un seul a gagné - profit minimum garanti
                bet.actual_profit = min_profit
                bet.status = 'won'
                
                if lang == 'fr':
                    result_text = (
                        f"\n\n✅ <b>BET MIDDLE CONFIRMÉ</b>\n\n"
                        f"✅ 1 seul a gagné (arbitrage)\n"
                        f"💰 Profit minimum: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"💡 Tu es quand même gagnant! 💚"
                    )
                else:
                    result_text = (
                        f"\n\n✅ <b>MIDDLE BET CONFIRMED</b>\n\n"
                        f"✅ Only 1 won (arbitrage)\n"
                        f"💰 Minimum profit: <b>${bet.actual_profit:+.2f}</b>\n\n"
                        f"💡 You still won! 💚"
                    )
            
            else:  # outcome == 'lost'
                # PERDU! Erreur humaine (mauvaise ligne, etc.)
                bet.actual_profit = -bet.total_stake
                bet.status = 'lost'
                    
                if lang == 'fr':
                    result_text = (
                        f"\n\n❌ <b>MIDDLE PERDU</b>\n\n"
                        f"❌ Erreur humaine (mauvaise ligne, etc.)\n"
                        f"💰 Perte: <b>${bet.actual_profit:.2f}</b>\n\n"
                        f"⚠️ Vérifie toujours que les lignes sont identiques!"
                    )
                else:
                    result_text = (
                        f"\n\n❌ <b>MIDDLE LOST</b>\n\n"
                        f"❌ Human error (wrong line, etc.)\n"
                        f"💰 Loss: <b>${bet.actual_profit:.2f}</b>\n\n"
                        f"⚠️ Always verify the lines are identical!"
                    )
            
            # Update daily stats
            bet_date = bet.bet_date
            daily_stat = db.query(DailyStats).filter(
                DailyStats.user_id == bet.user_id,
                DailyStats.date == bet_date
            ).first()
            
            if daily_stat:
                # Adjust total_profit: remove expected_profit, add actual_profit
                daily_stat.total_profit -= bet.expected_profit
                daily_stat.total_profit += bet.actual_profit
                daily_stat.confirmed = True
            
            db.commit()
            
            # Check if user can be unblocked
            reset_user_notification(bet.user_id)
            
            # Check if there are more pending middle bets FIRST
            today = date.today()
            remaining_middles = db.query(UserBet).filter(
                and_(
                    UserBet.user_id == bet.user_id,
                    UserBet.status == 'pending',
                    UserBet.bet_type == 'middle',
                    UserBet.id != bet.id  # Exclude current bet
                )
            ).all()
            
            # Update message: either with next questionnaire OR with final confirmation
            try:
                if remaining_middles:
                    # There are more pending middles! Edit with next questionnaire
                    next_bet = remaining_middles[0]
                    total_remaining = len(remaining_middles)
                    match_name = next_bet.match_name or "Match"
                    
                    counter_line = ""
                    if total_remaining > 1:
                        if lang == 'fr':
                            counter_line = f"<b>({total_remaining} questionnaires restants)</b>\n\n"
                        else:
                            counter_line = f"<b>({total_remaining} questionnaires remaining)</b>\n\n"
                    
                    if lang == 'fr':
                        next_text = (
                            f"✅ <b>Confirmé!</b>\n\n"
                            f"{counter_line}"
                            f"Prochain Middle bet à confirmer:\n\n"
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ {match_name}\n"
                            f"💵 Misé: ${next_bet.total_stake:.2f}\n\n"
                            f"📊 Résultat du Middle:"
                        )
                        jackpot_btn = types.InlineKeyboardButton(
                            text="🎰 JACKPOT! (les 2 ont gagné)",
                            callback_data=f"middle_outcome_{next_bet.id}_jackpot"
                        )
                        arb_btn = types.InlineKeyboardButton(
                            text="✅ ARBITRAGE (1 seul a gagné - profit min)",
                            callback_data=f"middle_outcome_{next_bet.id}_arb"
                        )
                        lost_btn = types.InlineKeyboardButton(
                            text="❌ PERDU (erreur humaine)",
                            callback_data=f"middle_outcome_{next_bet.id}_lost"
                        )
                    else:
                        next_text = (
                            f"✅ <b>Confirmed!</b>\n\n"
                            f"{counter_line}"
                            f"Next Middle bet to confirm:\n\n"
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ {match_name}\n"
                            f"💵 Staked: ${next_bet.total_stake:.2f}\n\n"
                            f"📊 Middle result:"
                        )
                        jackpot_btn = types.InlineKeyboardButton(
                            text="🎰 JACKPOT! (both won)",
                            callback_data=f"middle_outcome_{next_bet.id}_jackpot"
                        )
                        arb_btn = types.InlineKeyboardButton(
                            text="✅ ARBITRAGE (only 1 won - min profit)",
                            callback_data=f"middle_outcome_{next_bet.id}_arb"
                        )
                        lost_btn = types.InlineKeyboardButton(
                            text="❌ LOST (human error)",
                            callback_data=f"middle_outcome_{next_bet.id}_lost"
                        )
                    
                    next_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                        [jackpot_btn],
                        [arb_btn],
                        [lost_btn]
                    ])
                    
                    # Edit with next questionnaire
                    await callback.message.edit_text(
                        next_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=next_keyboard
                    )
                    logger.info(f"Edited message with next middle questionnaire for bet {next_bet.id}")
                else:
                    # No more pending middles - edit with final confirmation
                    original_text = callback.message.text or callback.message.caption or ""
                    # Remove old questionnaire if present
                    if "🎲 Le middle a-t-il HIT?" in original_text or "🎲 Did the middle HIT?" in original_text:
                        parts = original_text.split("🎲")
                        original_text = parts[0].rstrip('\n')
                    
                    # Add Clear, Feedback, and Vouch buttons
                    is_winning = bet.status == 'won' and bet.actual_profit and bet.actual_profit > 0
                    final_keyboard = get_feedback_vouch_buttons(bet.id, is_winning, lang)
                    
                    await callback.message.edit_text(
                        original_text + result_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=final_keyboard
                    )
                    logger.info(f"Edited message with final confirmation for bet {bet.id}")
            except Exception as e:
                logger.error(f"Could not edit message: {e}")
                await callback.answer(result_text.replace('<b>', '').replace('</b>', ''), show_alert=True)
        
        except Exception as e:
            logger.error(f"Error processing middle outcome: {e}")
            await callback.answer("❌ Erreur lors de la confirmation", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_middle_outcome: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("bet_notplayed_"))
async def callback_bet_not_played(callback: types.CallbackQuery):
    """
    Handle "Match not played yet" button - postpone confirmation request
    
    Format: bet_notplayed_<bet_id>
    """
    await callback.answer()
    
    try:
        bet_id = int(callback.data.split("_")[2])
        user_id = callback.from_user.id
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            if bet.user_id != user_id:
                await callback.answer("❌ Accès non autorisé", show_alert=True)
                return
            
            # Get user language
            user = db.query(User).filter(User.telegram_id == user_id).first()
            lang = user.language if user else 'en'
            
            # Set match_date to tomorrow so it gets asked again tomorrow
            from datetime import date, timedelta
            tomorrow = date.today() + timedelta(days=1)
            bet.match_date = tomorrow
            bet.status = 'pending'  # Ensure status is still pending
            
            db.commit()
            
            # Update the message
            if lang == 'fr':
                new_text = (
                    f"⏳ <b>REPORTÉ</b>\n\n"
                    f"Je te redemanderai demain pour ce bet.\n"
                    f"Bonne chance! 🍀"
                )
            else:
                new_text = (
                    f"⏳ <b>POSTPONED</b>\n\n"
                    f"I'll ask you again tomorrow for this bet.\n"
                    f"Good luck! 🍀"
                )
            
            try:
                await callback.message.edit_text(
                    new_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                await callback.message.answer(new_text, parse_mode=ParseMode.HTML)
            
            logger.info(f"Bet {bet_id} postponed - will ask again on {tomorrow}")
            
        except Exception as e:
            logger.error(f"Error in callback_bet_not_played: {e}")
            db.rollback()
            await callback.answer("❌ Erreur", show_alert=True)
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error parsing bet_notplayed callback: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


async def middle_questionnaire_loop(bot_instance):
    """
    Background loop that sends middle questionnaires every 6 hours.
    
    This runs continuously in the background.
    """
    import asyncio
    
    while True:
        try:
            await send_middle_questionnaires(bot_instance)
            logger.info("Middle questionnaires sent successfully")
        except Exception as e:
            logger.error(f"Error in middle_questionnaire_loop: {e}")
        
        # Wait 6 hours before next check
        await asyncio.sleep(6 * 3600)


async def send_middle_questionnaires(bot_instance):
    """
    Send questionnaires to users for their pending Middle bets after the match.
    
    This should be called by a scheduler (e.g., daily at midnight or every few hours).
    """
    db = SessionLocal()
    try:
        # Find all pending Middle bets where match_date is today or earlier
        today = date.today()
        pending_middles = db.query(UserBet).filter(
            and_(
                UserBet.bet_type == 'middle',
                UserBet.status == 'pending',
                UserBet.match_date <= today
            )
        ).all()
        
        logger.info(f"Found {len(pending_middles)} pending Middle bets to confirm")
        
        for bet in pending_middles:
            try:
                # Get user for language
                user = db.query(User).filter(User.telegram_id == bet.user_id).first()
                if not user:
                    continue
                
                lang = user.language or 'en'
                
                # Build questionnaire
                match_name = bet.match_name or "Match"
                
                if lang == 'fr':
                    text = (
                        f"🎲 <b>MIDDLE BET - CONFIRMATION NÉCESSAIRE</b>\n\n"
                        f"⚽ {match_name}\n"
                        f"💵 Misé: ${bet.total_stake:.2f}\n\n"
                        f"🎲 Le middle a-t-il <b>HIT</b>?\n"
                        f"(Les DEUX paris ont-ils gagné?)"
                    )
                    hit_btn = types.InlineKeyboardButton(
                        text="🎰 OUI - JACKPOT! (les deux ont gagné)",
                        callback_data=f"middle_outcome_{bet.id}_hit"
                    )
                    no_hit_btn = types.InlineKeyboardButton(
                        text="❌ NON - 1 seul a gagné",
                        callback_data=f"middle_outcome_{bet.id}_no_hit"
                    )
                else:
                    text = (
                        f"🎲 <b>MIDDLE BET - CONFIRMATION NEEDED</b>\n\n"
                        f"⚽ {match_name}\n"
                        f"💵 Staked: ${bet.total_stake:.2f}\n\n"
                        f"🎲 Did the middle <b>HIT</b>?\n"
                        f"(Did BOTH bets win?)"
                    )
                    hit_btn = types.InlineKeyboardButton(
                        text="🎰 YES - JACKPOT! (both won)",
                        callback_data=f"middle_outcome_{bet.id}_hit"
                    )
                    no_hit_btn = types.InlineKeyboardButton(
                        text="❌ NO - only 1 won",
                        callback_data=f"middle_outcome_{bet.id}_no_hit"
                    )
                
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [hit_btn],
                    [no_hit_btn]
                ])
                
                await bot_instance.send_message(
                    bet.user_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                
                logger.info(f"Sent middle questionnaire to user {bet.user_id} for bet {bet.id}")
                
            except Exception as e:
                logger.error(f"Error sending middle questionnaire for bet {bet.id}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in send_middle_questionnaires: {e}")
    finally:
        db.close()
