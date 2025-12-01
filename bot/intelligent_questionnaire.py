"""
Système de questionnaire intelligent pour confirmer les résultats des bets (arbitrage, middle, positive EV).

Le système est intelligent:
1. Si on connaît la date/heure du match → envoie le questionnaire 30 minutes après la fin estimée du match
2. Si pas de date → demande à minuit si le match est passé
3. Si "pas encore" → demande la date du match (ou "je sais pas" pour redemander chaque jour)
"""

import logging
import asyncio
from datetime import datetime, date, timedelta, timezone
from aiogram import Router, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import and_, or_
from typing import Optional

from models.user import User
from models.bet import UserBet, DailyStats
from database import SessionLocal

logger = logging.getLogger(__name__)
router = Router()


# FSM States for date input
class BetConfirmationStates(StatesGroup):
    waiting_for_date = State()


# Sport duration mapping (average duration in minutes)
SPORT_DURATIONS = {
    'basketball': 150,  # NBA: 48 min + halftime + timeouts ≈ 2.5h
    'ncaab': 150,
    'nba': 150,
    'football': 210,  # NFL: 60 min + halftime + timeouts ≈ 3.5h
    'nfl': 210,
    'ncaaf': 210,
    'soccer': 120,  # 90 min + halftime ≈ 2h
    'hockey': 150,  # NHL: 60 min + intermissions ≈ 2.5h
    'nhl': 150,
    'baseball': 180,  # MLB: ≈ 3h
    'mlb': 180,
    'tennis': 150,  # ≈ 2.5h average
    'mma': 60,  # UFC: ≈ 1h
    'boxing': 60,  # ≈ 1h
}


def estimate_match_end(commence_time_iso: str, sport: str) -> Optional[datetime]:
    """
    Estime l'heure de fin du match basée sur l'heure de début et le sport.
    
    Args:
        commence_time_iso: ISO timestamp du début du match
        sport: Nom du sport (ex: "NBA", "NFL", "Soccer")
    
    Returns:
        datetime de la fin estimée du match, ou None si impossible
    """
    try:
        # Parse commence time
        dt_start = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
        
        # Get sport duration
        sport_lower = sport.lower() if sport else 'unknown'
        duration = None
        for key, dur in SPORT_DURATIONS.items():
            if key in sport_lower:
                duration = dur
                break
        
        if not duration:
            # Default: 2.5 hours
            duration = 150
            logger.warning(f"Unknown sport '{sport}', using default duration of 150 minutes")
        
        # Calculate estimated end time
        dt_end = dt_start + timedelta(minutes=duration)
        
        return dt_end
    except Exception as e:
        logger.error(f"Could not estimate match end: {e}")
        return None


async def send_bet_questionnaire(bot_instance, bet: UserBet, lang: str = 'fr'):
    """
    Envoie un questionnaire INTELLIGENT pour confirmer le résultat d'un bet.
    ÉTAPE 1: Demande si le match a commencé
    ÉTAPE 2: Si oui → questions de résultat, si non → questions de date
    
    Args:
        bot_instance: Instance du bot Telegram
        bet: UserBet record
        lang: Langue de l'utilisateur ('fr' ou 'en')
    """
    try:
        bet_type = bet.bet_type
        match_name = bet.match_name or "Match"
        sport_name = bet.sport or ""
        
        # Format dates
        from datetime import datetime
        bet_date_str = bet.bet_date.strftime("%Y-%m-%d") if bet.bet_date else "N/A"
        match_date_str = bet.match_date.strftime("%Y-%m-%d") if bet.match_date else "N/A"
        
        # STEP 1: Ask if match has started
        if lang == 'fr':
            text = (
                f"🎯 <b>CONFIRMATION NÉCESSAIRE</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{'🏆 ' + sport_name if sport_name else ''}\n"
                f"📅 Bet placé: {bet_date_str}\n"
                f"💵 Misé: ${bet.total_stake:.2f}\n\n"
                f"❓ <b>Le match a-t-il commencé?</b>"
            )
            yes_btn = types.InlineKeyboardButton(
                text="✅ OUI - Le match a eu lieu",
                callback_data=f"match_started_{bet.id}_yes"
            )
            no_btn = types.InlineKeyboardButton(
                text="⏳ NON - Pas encore joué",
                callback_data=f"match_started_{bet.id}_no"
            )
        else:
            text = (
                f"🎯 <b>CONFIRMATION NEEDED</b>\n\n"
                f"⚽ <b>{match_name}</b>\n"
                f"{'🏆 ' + sport_name if sport_name else ''}\n"
                f"📅 Bet placed: {bet_date_str}\n"
                f"💵 Staked: ${bet.total_stake:.2f}\n\n"
                f"❓ <b>Has the match started?</b>"
            )
            yes_btn = types.InlineKeyboardButton(
                text="✅ YES - Match played",
                callback_data=f"match_started_{bet.id}_yes"
            )
            no_btn = types.InlineKeyboardButton(
                text="⏳ NO - Not played yet",
                callback_data=f"match_started_{bet.id}_no"
            )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [yes_btn],
            [no_btn]
        ])
        
        await bot_instance.send_message(
            chat_id=bet.user_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Sent STEP 1 questionnaire for bet {bet.id} to user {bet.user_id}")
        return
        
        # OLD CODE BELOW - Will be triggered by callbacks
        bet_date_str = bet.bet_date.strftime("%Y-%m-%d") if bet.bet_date else "N/A"
        match_date_str = bet.match_date.strftime("%Y-%m-%d") if bet.match_date else "N/A"
        
        # Get odds and other info from drop_event if available
        odds_info = ""
        if bet.drop_event and bet.drop_event.payload:
            try:
                import json
                drop_data = bet.drop_event.payload
                outcomes = drop_data.get('outcomes', [])
                if len(outcomes) >= 2:
                    o1, o2 = outcomes[0], outcomes[1]
                    odds1 = o1.get('odds', 0)
                    odds2 = o2.get('odds', 0)
                    odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                    odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                    casino1 = o1.get('casino', 'N/A')
                    casino2 = o2.get('casino', 'N/A')
                    outcome1 = o1.get('outcome', 'N/A')
                    outcome2 = o2.get('outcome', 'N/A')
                    
                    if lang == 'fr':
                        odds_info = (
                            f"\n📊 <b>Détails des paris:</b>\n"
                            f"• [{casino1}] {outcome1}: {odds1_str}\n"
                            f"• [{casino2}] {outcome2}: {odds2_str}\n"
                        )
                    else:
                        odds_info = (
                            f"\n📊 <b>Bet details:</b>\n"
                            f"• [{casino1}] {outcome1}: {odds1_str}\n"
                            f"• [{casino2}] {outcome2}: {odds2_str}\n"
                        )
            except Exception as e:
                logger.warning(f"Could not extract odds info: {e}")
        
        # Build sport/league line
        sport_line = f"🏆 {sport_name}\n" if sport_name else ""
        
        # Build questionnaire based on bet type
        if bet_type == 'middle':
            jackpot_profit = bet.expected_profit if bet.expected_profit else 0
            
            # Calculate min_profit (arbitrage profit)
            min_profit = 0.0
            if bet.drop_event and bet.drop_event.payload:
                try:
                    drop_data = bet.drop_event.payload
                    side_a = drop_data.get('side_a', {})
                    side_b = drop_data.get('side_b', {})
                    if side_a and side_b and 'odds' in side_a and 'odds' in side_b and 'line' in side_a and 'line' in side_b:
                        from utils.middle_calculator import classify_middle_type
                        cls = classify_middle_type(side_a, side_b, bet.total_stake)
                        min_profit = min(cls['profit_scenario_1'], cls['profit_scenario_3'])
                except Exception as e:
                    logger.warning(f"Could not calculate min_profit: {e}")
            
            if lang == 'fr':
                text = (
                    f"🎲 <b>MIDDLE BET - CONFIRMATION NÉCESSAIRE</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placé: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                    f"💰 Profit si 1 bet hit: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                    f"🎰 Profit si jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                    f"📊 Résultat du Middle:"
                )
                jackpot_btn = types.InlineKeyboardButton(
                    text="🎰 JACKPOT! (les 2 ont gagné)",
                    callback_data=f"middle_outcome_{bet.id}_jackpot"
                )
                arb_btn = types.InlineKeyboardButton(
                    text="✅ ARBITRAGE (1 seul a gagné - profit min)",
                    callback_data=f"middle_outcome_{bet.id}_arb"
                )
                lost_btn = types.InlineKeyboardButton(
                    text="❌ PERDU (erreur humaine)",
                    callback_data=f"middle_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match pas encore joué",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            else:
                text = (
                    f"🎲 <b>MIDDLE BET - CONFIRMATION NEEDED</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placed: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                    f"💰 Profit if 1 bet hits: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                    f"🎰 Profit if jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                    f"📊 Middle result:"
                )
                jackpot_btn = types.InlineKeyboardButton(
                    text="🎰 JACKPOT! (both won)",
                    callback_data=f"middle_outcome_{bet.id}_jackpot"
                )
                arb_btn = types.InlineKeyboardButton(
                    text="✅ ARBITRAGE (only 1 won - min profit)",
                    callback_data=f"middle_outcome_{bet.id}_arb"
                )
                lost_btn = types.InlineKeyboardButton(
                    text="❌ LOST (human error)",
                    callback_data=f"middle_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match not played yet",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [jackpot_btn],
                [arb_btn],
                [lost_btn],
                [not_played_btn]
            ])
        
        elif bet_type == 'arbitrage':
            guaranteed_profit = bet.expected_profit if bet.expected_profit else 0
            roi_percent = (guaranteed_profit / bet.total_stake * 100) if bet.total_stake > 0 else 0
            
            if lang == 'fr':
                text = (
                    f"✅ <b>ARBITRAGE - CONFIRMATION NÉCESSAIRE</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placé: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                    f"💰 Profit garanti: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                    f"As-tu bien reçu ton profit?"
                )
                yes_btn = types.InlineKeyboardButton(
                    text="✅ OUI - J'ai reçu mon profit",
                    callback_data=f"arb_outcome_{bet.id}_won"
                )
                no_btn = types.InlineKeyboardButton(
                    text="❌ NON - Problème",
                    callback_data=f"arb_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match pas encore joué",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            else:
                text = (
                    f"✅ <b>ARBITRAGE - CONFIRMATION NEEDED</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placed: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                    f"💰 Guaranteed profit: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                    f"Did you receive your profit?"
                )
                yes_btn = types.InlineKeyboardButton(
                    text="✅ YES - I got my profit",
                    callback_data=f"arb_outcome_{bet.id}_won"
                )
                no_btn = types.InlineKeyboardButton(
                    text="❌ NO - Problem",
                    callback_data=f"arb_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match not played yet",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [yes_btn],
                [no_btn],
                [not_played_btn]
            ])
        
        elif bet_type == 'good_ev':
            expected_ev = bet.expected_profit if bet.expected_profit else 0
            
            if lang == 'fr':
                text = (
                    f"📈 <b>GOOD EV - CONFIRMATION NÉCESSAIRE</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placé: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                    f"📊 EV prévu: <b>${expected_ev:+.2f}</b>\n\n"
                    f"As-tu gagné ou perdu ce bet?"
                )
                won_btn = types.InlineKeyboardButton(
                    text="✅ GAGNÉ",
                    callback_data=f"ev_outcome_{bet.id}_won"
                )
                lost_btn = types.InlineKeyboardButton(
                    text="❌ PERDU",
                    callback_data=f"ev_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match pas encore joué",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            else:
                text = (
                    f"📈 <b>GOOD EV - CONFIRMATION NEEDED</b>\n\n"
                    f"⚽ <b>{match_name}</b>\n"
                    f"{sport_line}"
                    f"🕐 Match: {match_date_str}\n"
                    f"📅 Bet placed: {bet_date_str}\n"
                    f"{odds_info}\n"
                    f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                    f"📊 Expected EV: <b>${expected_ev:+.2f}</b>\n\n"
                    f"Did you win or lose this bet?"
                )
                won_btn = types.InlineKeyboardButton(
                    text="✅ WON",
                    callback_data=f"ev_outcome_{bet.id}_won"
                )
                lost_btn = types.InlineKeyboardButton(
                    text="❌ LOST",
                    callback_data=f"ev_outcome_{bet.id}_lost"
                )
                not_played_btn = types.InlineKeyboardButton(
                    text="⏳ Match not played yet",
                    callback_data=f"bet_notplayed_{bet.id}"
                )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [won_btn],
                [lost_btn],
                [not_played_btn]
            ])
        
        else:
            logger.error(f"Unknown bet type: {bet_type}")
            return
        
        await bot_instance.send_message(
            bet.user_id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info(f"Sent {bet_type} questionnaire to user {bet.user_id} for bet {bet.id}")
        
    except Exception as e:
        logger.error(f"Error sending bet questionnaire for bet {bet.id}: {e}")


async def intelligent_questionnaire_loop(bot_instance):
    """
    Background loop DÉSACTIVÉ - Les questionnaires sont maintenant envoyés manuellement
    via le système de pending_confirmations qui bloque l'accès au menu.
    
    Ce loop ne fait plus rien automatiquement.
    """
    bot = bot_instance
    
    while True:
        try:
            # Loop désactivé - on ne fait rien
            logger.info("📵 Intelligent questionnaire loop is disabled (manual confirmation system active)")
            
        except Exception as e:
            logger.error(f"Error in intelligent_questionnaire_loop: {e}")
        
        # Wait 1 hour before next check (juste pour garder le loop actif)
        await asyncio.sleep(60 * 60)


async def check_finished_matches(bot_instance, now: datetime):
    """
    Vérifie les bets avec date de match connue et envoie les questionnaires pour ceux terminés.
    """
    db = SessionLocal()
    try:
        # Find all pending bets with match_date
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.status == 'pending',
                UserBet.match_date.isnot(None)
            )
        ).all()
        
        logger.info(f"Found {len(pending_bets)} pending bets with known match dates")
        
        for bet in pending_bets:
            try:
                # Get commence_time from drop event if available
                commence_time_iso = None
                sport = bet.sport or 'unknown'
                
                if bet.drop_event and bet.drop_event.payload:
                    import json
                    drop_data = bet.drop_event.payload
                    commence_time_iso = drop_data.get('commence_time')
                
                # Estimate match end
                if commence_time_iso:
                    match_end = estimate_match_end(commence_time_iso, sport)
                else:
                    # If no commence_time, assume match starts at noon on match_date
                    match_start = datetime.combine(bet.match_date, datetime.min.time().replace(hour=12))
                    match_start = match_start.replace(tzinfo=timezone.utc)
                    match_end = estimate_match_end(match_start.isoformat(), sport)
                
                if not match_end:
                    continue
                
                # Check if match is finished (30 minutes buffer after estimated end)
                buffer_minutes = 30
                match_end_with_buffer = match_end + timedelta(minutes=buffer_minutes)
                
                if now >= match_end_with_buffer:
                    # Match is finished! Send questionnaire
                    user = db.query(User).filter(User.telegram_id == bet.user_id).first()
                    lang = user.language if user else 'en'
                    
                    await send_bet_questionnaire(bot_instance, bet, lang)
                    
                    logger.info(f"Sent questionnaire for bet {bet.id} (match ended at {match_end})")
                    
            except Exception as e:
                logger.error(f"Error processing bet {bet.id} for finished match check: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in check_finished_matches: {e}")
    finally:
        db.close()


async def check_bets_without_date(bot_instance):
    """
    À minuit, vérifie les bets sans date de match connue et demande si le match est passé.
    """
    db = SessionLocal()
    try:
        # Find all pending bets without match_date
        # Exclude bets created today (avoid spamming on restart)
        today = date.today()
        pending_bets = db.query(UserBet).filter(
            and_(
                UserBet.status == 'pending',
                UserBet.match_date.is_(None),
                UserBet.bet_date < today  # Only ask for bets from previous days
            )
        ).all()
        
        logger.info(f"Found {len(pending_bets)} pending bets without known match dates (excluding today's bets)")
        
        for bet in pending_bets:
            try:
                # Get user language
                user = db.query(User).filter(User.telegram_id == bet.user_id).first()
                if not user:
                    continue
                
                lang = user.language or 'en'
                match_name = bet.match_name or "Match"
                sport_name = bet.sport or ""
                bet_type = bet.bet_type
                
                # Format dates
                from datetime import datetime
                bet_date_str = bet.bet_date.strftime("%Y-%m-%d") if bet.bet_date else "N/A"
                match_date_str = bet.match_date.strftime("%Y-%m-%d") if bet.match_date else "N/A"
                
                # Get odds info from drop_event
                odds_info = ""
                min_profit = 0.0
                if bet.drop_event and bet.drop_event.payload:
                    try:
                        import json
                        drop_data = bet.drop_event.payload
                        
                        # For MIDDLE, calculate min_profit
                        if bet_type == 'middle':
                            side_a = drop_data.get('side_a', {})
                            side_b = drop_data.get('side_b', {})
                            if side_a and side_b and 'odds' in side_a and 'odds' in side_b and 'line' in side_a and 'line' in side_b:
                                from utils.middle_calculator import classify_middle_type
                                cls = classify_middle_type(side_a, side_b, bet.total_stake)
                                min_profit = min(cls['profit_scenario_1'], cls['profit_scenario_3'])
                        
                        # Get outcomes for odds display
                        outcomes = drop_data.get('outcomes', [])
                        if len(outcomes) >= 2:
                            o1, o2 = outcomes[0], outcomes[1]
                            odds1 = o1.get('odds', 0)
                            odds2 = o2.get('odds', 0)
                            odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                            odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                            casino1 = o1.get('casino', 'N/A')
                            casino2 = o2.get('casino', 'N/A')
                            outcome1 = o1.get('outcome', 'N/A')
                            outcome2 = o2.get('outcome', 'N/A')
                            
                            if lang == 'fr':
                                odds_info = (
                                    f"\n📊 <b>Détails des paris:</b>\n"
                                    f"• [{casino1}] {outcome1}: {odds1_str}\n"
                                    f"• [{casino2}] {outcome2}: {odds2_str}\n"
                                )
                            else:
                                odds_info = (
                                    f"\n📊 <b>Bet details:</b>\n"
                                    f"• [{casino1}] {outcome1}: {odds1_str}\n"
                                    f"• [{casino2}] {outcome2}: {odds2_str}\n"
                                )
                    except Exception as e:
                        logger.warning(f"Could not parse drop_event payload: {e}")
                
                sport_line = f"🏆 {sport_name}\n" if sport_name else ""
                
                # Build message based on bet type
                if bet_type == 'middle':
                    jackpot_profit = bet.expected_profit if bet.expected_profit else 0
                    if lang == 'fr':
                        text = (
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit si 1 bet hit: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                            f"🎰 Profit si jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                            f"Le match a-t-il déjà eu lieu?"
                        )
                    else:
                        text = (
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit if 1 bet hits: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                            f"🎰 Profit if jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                            f"Has the match already happened?"
                        )
                
                elif bet_type == 'arbitrage':
                    guaranteed_profit = bet.expected_profit if bet.expected_profit else 0
                    roi_percent = (guaranteed_profit / bet.total_stake * 100) if bet.total_stake > 0 else 0
                    if lang == 'fr':
                        text = (
                            f"✅ <b>ARBITRAGE - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit garanti: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                            f"Le match a-t-il déjà eu lieu?"
                        )
                    else:
                        text = (
                            f"✅ <b>ARBITRAGE - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Guaranteed profit: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                            f"Has the match already happened?"
                        )
                
                elif bet_type == 'good_ev':
                    expected_ev = bet.expected_profit if bet.expected_profit else 0
                    if lang == 'fr':
                        text = (
                            f"📈 <b>GOOD EV - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"📊 EV prévu: <b>${expected_ev:+.2f}</b>\n\n"
                            f"Le match a-t-il déjà eu lieu?"
                        )
                    else:
                        text = (
                            f"📈 <b>GOOD EV - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"📊 Expected EV: <b>${expected_ev:+.2f}</b>\n\n"
                            f"Has the match already happened?"
                        )
                else:
                    # Unknown type - fallback to simple message
                    if lang == 'fr':
                        text = (
                            f"📅 <b>CONFIRMATION DE MATCH</b>\n\n"
                            f"⚽ {match_name}\n"
                            f"💵 Misé: ${bet.total_stake:.2f}\n\n"
                            f"Le match a-t-il déjà eu lieu?"
                        )
                    else:
                        text = (
                            f"📅 <b>MATCH CONFIRMATION</b>\n\n"
                            f"⚽ {match_name}\n"
                            f"💵 Staked: ${bet.total_stake:.2f}\n\n"
                            f"Has the match already happened?"
                        )
                
                if lang == 'fr':
                    yes_btn = types.InlineKeyboardButton(
                        text="✅ OUI - Match terminé",
                        callback_data=f"match_passed_{bet.id}_yes"
                    )
                    no_btn = types.InlineKeyboardButton(
                        text="❌ NON - Pas encore",
                        callback_data=f"match_passed_{bet.id}_no"
                    )
                    idk_btn = types.InlineKeyboardButton(
                        text="🤷 JE SAIS PAS",
                        callback_data=f"match_passed_{bet.id}_idk"
                    )
                else:
                    yes_btn = types.InlineKeyboardButton(
                        text="✅ YES - Match finished",
                        callback_data=f"match_passed_{bet.id}_yes"
                    )
                    no_btn = types.InlineKeyboardButton(
                        text="❌ NO - Not yet",
                        callback_data=f"match_passed_{bet.id}_no"
                    )
                    idk_btn = types.InlineKeyboardButton(
                        text="🤷 I DON'T KNOW",
                        callback_data=f"match_passed_{bet.id}_idk"
                    )
                
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [yes_btn],
                    [no_btn],
                    [idk_btn]
                ])
                
                await bot_instance.send_message(
                    bet.user_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                
                logger.info(f"Sent match status question for bet {bet.id}")
                
            except Exception as e:
                logger.error(f"Error sending match status question for bet {bet.id}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in check_bets_without_date: {e}")
    finally:
        db.close()


@router.callback_query(F.data.startswith("match_passed_"))
async def callback_match_passed(callback: types.CallbackQuery):
    """
    Handle match status confirmation (yes/no/idk).
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        status = parts[3]  # 'yes', 'no', 'idk'
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            if status == 'yes':
                # Match is finished → edit message to show result questionnaire
                # Build detailed questionnaire directly in the same message
                match_name = bet.match_name or "Match"
                sport_name = bet.sport or ""
                bet_type = bet.bet_type
                
                # Format dates
                from datetime import datetime
                bet_date_str = bet.bet_date.strftime("%Y-%m-%d") if bet.bet_date else "N/A"
                match_date_str = bet.match_date.strftime("%Y-%m-%d") if bet.match_date else "N/A"
                
                # Get odds info
                odds_info = ""
                if bet.drop_event and bet.drop_event.payload:
                    try:
                        import json
                        drop_data = bet.drop_event.payload
                        outcomes = drop_data.get('outcomes', [])
                        if len(outcomes) >= 2:
                            o1, o2 = outcomes[0], outcomes[1]
                            odds1 = o1.get('odds', 0)
                            odds2 = o2.get('odds', 0)
                            odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
                            odds2_str = f"+{odds2}" if odds2 > 0 else str(odds2)
                            casino1 = o1.get('casino', 'N/A')
                            casino2 = o2.get('casino', 'N/A')
                            outcome1 = o1.get('outcome', 'N/A')
                            outcome2 = o2.get('outcome', 'N/A')
                            
                            if lang == 'fr':
                                odds_info = (
                                    f"\n📊 <b>Détails des paris:</b>\n"
                                    f"• [{casino1}] {outcome1}: {odds1_str}\n"
                                    f"• [{casino2}] {outcome2}: {odds2_str}\n"
                                )
                            else:
                                odds_info = (
                                    f"\n📊 <b>Bet details:</b>\n"
                                    f"• [{casino1}] {outcome1}: {odds1_str}\n"
                                    f"• [{casino2}] {outcome2}: {odds2_str}\n"
                                )
                    except Exception:
                        pass
                
                sport_line = f"🏆 {sport_name}\n" if sport_name else ""
                
                # Build questionnaire based on bet type
                if bet_type == 'middle':
                    jackpot_profit = bet.expected_profit if bet.expected_profit else 0
                    
                    # Calculate min_profit (arbitrage profit)
                    min_profit = 0.0
                    if bet.drop_event and bet.drop_event.payload:
                        try:
                            drop_data = bet.drop_event.payload
                            side_a = drop_data.get('side_a', {})
                            side_b = drop_data.get('side_b', {})
                            if side_a and side_b and 'odds' in side_a and 'odds' in side_b and 'line' in side_a and 'line' in side_b:
                                from utils.middle_calculator import classify_middle_type
                                cls = classify_middle_type(side_a, side_b, bet.total_stake)
                                min_profit = min(cls['profit_scenario_1'], cls['profit_scenario_3'])
                        except Exception as e:
                            logger.warning(f"Could not calculate min_profit: {e}")
                    
                    if lang == 'fr':
                        new_text = (
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit si 1 bet hit: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                            f"🎰 Profit si jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                            f"📊 Résultat du Middle:"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="🎰 JACKPOT! (les 2 ont gagné)",
                            callback_data=f"middle_outcome_{bet.id}_jackpot"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="✅ ARBITRAGE (1 seul a gagné - profit min)",
                            callback_data=f"middle_outcome_{bet.id}_arb"
                        )
                        btn3 = types.InlineKeyboardButton(
                            text="❌ PERDU (erreur humaine)",
                            callback_data=f"middle_outcome_{bet.id}_lost"
                        )
                    else:
                        new_text = (
                            f"🎲 <b>MIDDLE BET - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit if 1 bet hits: <b>${min_profit:+.2f}</b> (arbitrage)\n"
                            f"🎰 Profit if jackpot: <b>${jackpot_profit:+.2f}</b>\n\n"
                            f"📊 Middle result:"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="🎰 JACKPOT! (both won)",
                            callback_data=f"middle_outcome_{bet.id}_jackpot"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="✅ ARBITRAGE (only 1 won - min profit)",
                            callback_data=f"middle_outcome_{bet.id}_arb"
                        )
                        btn3 = types.InlineKeyboardButton(
                            text="❌ LOST (human error)",
                            callback_data=f"middle_outcome_{bet.id}_lost"
                        )
                    
                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2], [btn3]])
                
                elif bet_type == 'arbitrage':
                    guaranteed_profit = bet.expected_profit if bet.expected_profit else 0
                    roi_percent = (guaranteed_profit / bet.total_stake * 100) if bet.total_stake > 0 else 0
                    if lang == 'fr':
                        new_text = (
                            f"✅ <b>ARBITRAGE - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Profit garanti: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                            f"As-tu bien reçu ton profit?"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="✅ OUI - J'ai reçu mon profit",
                            callback_data=f"arb_outcome_{bet.id}_won"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="❌ NON - Problème",
                            callback_data=f"arb_outcome_{bet.id}_lost"
                        )
                    else:
                        new_text = (
                            f"✅ <b>ARBITRAGE - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"💰 Guaranteed profit: <b>${guaranteed_profit:+.2f}</b> (ROI: {roi_percent:.2f}%)\n\n"
                            f"Did you receive your profit?"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="✅ YES - I got my profit",
                            callback_data=f"arb_outcome_{bet.id}_won"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="❌ NO - Problem",
                            callback_data=f"arb_outcome_{bet.id}_lost"
                        )
                    
                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2]])
                
                elif bet_type == 'good_ev':
                    expected_ev = bet.expected_profit if bet.expected_profit else 0
                    if lang == 'fr':
                        new_text = (
                            f"📈 <b>GOOD EV - CONFIRMATION NÉCESSAIRE</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placé: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Misé: <b>${bet.total_stake:.2f}</b>\n"
                            f"📊 EV prévu: <b>${expected_ev:+.2f}</b>\n\n"
                            f"As-tu gagné ou perdu ce bet?"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="✅ GAGNÉ",
                            callback_data=f"ev_outcome_{bet.id}_won"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="❌ PERDU",
                            callback_data=f"ev_outcome_{bet.id}_lost"
                        )
                    else:
                        new_text = (
                            f"📈 <b>GOOD EV - CONFIRMATION NEEDED</b>\n\n"
                            f"⚽ <b>{match_name}</b>\n"
                            f"{sport_line}"
                            f"🕐 Match: {match_date_str}\n"
                            f"📅 Bet placed: {bet_date_str}\n"
                            f"{odds_info}\n"
                            f"💵 Staked: <b>${bet.total_stake:.2f}</b>\n"
                            f"📊 Expected EV: <b>${expected_ev:+.2f}</b>\n\n"
                            f"Did you win or lose this bet?"
                        )
                        btn1 = types.InlineKeyboardButton(
                            text="✅ WON",
                            callback_data=f"ev_outcome_{bet.id}_won"
                        )
                        btn2 = types.InlineKeyboardButton(
                            text="❌ LOST",
                            callback_data=f"ev_outcome_{bet.id}_lost"
                        )
                    
                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2]])
                else:
                    # Unknown type - just confirm
                    if lang == 'fr':
                        new_text = callback.message.text + "\n\n✅ <b>Match confirmé comme terminé</b>"
                    else:
                        new_text = callback.message.text + "\n\n✅ <b>Match confirmed as finished</b>"
                    keyboard = None
                
                # Edit the existing message with the detailed questionnaire
                await callback.message.edit_text(
                    new_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            
            elif status == 'no':
                # Match not finished yet → ask when the match will be
                from datetime import timedelta
                tomorrow = date.today() + timedelta(days=1)
                day_after = date.today() + timedelta(days=2)
                in_3_days = date.today() + timedelta(days=3)
                in_4_days = date.today() + timedelta(days=4)
                in_5_days = date.today() + timedelta(days=5)
                
                if lang == 'fr':
                    new_text = callback.message.text + "\n\n📅 <b>Quand est le match?</b>"
                    btn1 = types.InlineKeyboardButton(
                        text=f"📆 Demain ({tomorrow.strftime('%d/%m')})",
                        callback_data=f"set_date_{bet.id}_{tomorrow.isoformat()}"
                    )
                    btn2 = types.InlineKeyboardButton(
                        text=f"📆 Après-demain ({day_after.strftime('%d/%m')})",
                        callback_data=f"set_date_{bet.id}_{day_after.isoformat()}"
                    )
                    btn3 = types.InlineKeyboardButton(
                        text=f"📆 Dans 3 jours ({in_3_days.strftime('%d/%m')})",
                        callback_data=f"set_date_{bet.id}_{in_3_days.isoformat()}"
                    )
                    btn4 = types.InlineKeyboardButton(
                        text=f"📆 Dans 4 jours ({in_4_days.strftime('%d/%m')})",
                        callback_data=f"set_date_{bet.id}_{in_4_days.isoformat()}"
                    )
                    btn5 = types.InlineKeyboardButton(
                        text=f"📆 Dans 5 jours ({in_5_days.strftime('%d/%m')})",
                        callback_data=f"set_date_{bet.id}_{in_5_days.isoformat()}"
                    )
                    btn_idk = types.InlineKeyboardButton(
                        text="🤷 JE SAIS PAS",
                        callback_data=f"set_date_{bet.id}_unknown"
                    )
                else:
                    new_text = callback.message.text + "\n\n📅 <b>When is the match?</b>"
                    btn1 = types.InlineKeyboardButton(
                        text=f"📆 Tomorrow ({tomorrow.strftime('%m/%d')})",
                        callback_data=f"set_date_{bet.id}_{tomorrow.isoformat()}"
                    )
                    btn2 = types.InlineKeyboardButton(
                        text=f"📆 Day after ({day_after.strftime('%m/%d')})",
                        callback_data=f"set_date_{bet.id}_{day_after.isoformat()}"
                    )
                    btn3 = types.InlineKeyboardButton(
                        text=f"📆 In 3 days ({in_3_days.strftime('%m/%d')})",
                        callback_data=f"set_date_{bet.id}_{in_3_days.isoformat()}"
                    )
                    btn4 = types.InlineKeyboardButton(
                        text=f"📆 In 4 days ({in_4_days.strftime('%m/%d')})",
                        callback_data=f"set_date_{bet.id}_{in_4_days.isoformat()}"
                    )
                    btn5 = types.InlineKeyboardButton(
                        text=f"📆 In 5 days ({in_5_days.strftime('%m/%d')})",
                        callback_data=f"set_date_{bet.id}_{in_5_days.isoformat()}"
                    )
                    btn_idk = types.InlineKeyboardButton(
                        text="🤷 I DON'T KNOW",
                        callback_data=f"set_date_{bet.id}_unknown"
                    )
                
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [btn1],
                    [btn2],
                    [btn3],
                    [btn4],
                    [btn5],
                    [btn_idk]
                ])
                
                await callback.message.edit_text(
                    new_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            
            elif status == 'idk':
                # User doesn't know → will be asked again tomorrow
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
            
        except Exception as e:
            logger.error(f"Error processing match status: {e}")
            await callback.answer("❌ Erreur", show_alert=True)
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in callback_match_passed: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("set_date_"))
async def callback_set_date(callback: types.CallbackQuery):
    """
    Handle match date selection.
    Format: set_date_<bet_id>_<date_iso_or_unknown>
    """
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.answer("❌ Format invalide", show_alert=True)
            return
        
        bet_id = int(parts[2])
        date_str = parts[3]  # ISO date or 'unknown'
        
        db = SessionLocal()
        try:
            bet = db.query(UserBet).filter(UserBet.id == bet_id).first()
            
            if not bet:
                await callback.answer("❌ Bet non trouvé", show_alert=True)
                return
            
            user = db.query(User).filter(User.telegram_id == bet.user_id).first()
            lang = user.language if user else 'en'
            
            if date_str == 'unknown':
                # User doesn't know - will ask again tomorrow
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
                # Parse and set the date
                from datetime import datetime
                match_date = datetime.fromisoformat(date_str).date()
                bet.match_date = match_date
                db.commit()
                
                if lang == 'fr':
                    await callback.message.edit_text(
                        callback.message.text + f"\n\n✅ <b>Date enregistrée: {match_date.strftime('%d/%m/%Y')}</b>\n"
                        "Je te redemanderai après le match!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None
                    )
                else:
                    await callback.message.edit_text(
                        callback.message.text + f"\n\n✅ <b>Date saved: {match_date.strftime('%m/%d/%Y')}</b>\n"
                        "I'll ask you after the match!",
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
        logger.error(f"Error in callback_set_date: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
