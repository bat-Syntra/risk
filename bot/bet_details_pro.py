"""
Bet Details Professional Display
Affichage COMPLET des détails d'un bet avec toutes les infos
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User
from models.bet import UserBet
from models.drop_event import DropEvent
from core.casinos import get_casino_logo, get_casino_referral_link

import logging
logger = logging.getLogger(__name__)

router = Router()


def format_bet_details_pro(bet: UserBet, db, lang: str = 'en') -> tuple:
    """
    Génère l'affichage COMPLET d'un bet
    Returns: (message, keyboard)
    """
    
    # Type & Status
    type_emoji = {
        'arbitrage': '⚖️',
        'middle': '🎯',
        'good_ev': '💎'
    }.get(bet.bet_type, '💰')
    
    type_name = {
        'arbitrage': 'ARBITRAGE',
        'good_ev': 'GOOD +EV',
        'middle': 'MIDDLE BET'
    }.get(bet.bet_type, 'BET')
    
    # Determine outcome
    if bet.bet_type == 'arbitrage':
        outcome_text = "✅ WIN" if lang == 'en' else "✅ GAGNÉ"
        outcome_emoji = "✅"
    elif bet.actual_profit is not None:
        if bet.actual_profit > 0:
            outcome_text = "✅ WIN" if lang == 'en' else "✅ GAGNÉ"
            outcome_emoji = "✅"
        elif bet.actual_profit < 0:
            outcome_text = "❌ LOSS" if lang == 'en' else "❌ PERDU"
            outcome_emoji = "❌"
        else:
            outcome_text = "🤝 PUSH" if lang == 'en' else "🤝 NUL"
            outcome_emoji = "🤝"
    else:
        outcome_text = "⏳ PENDING" if lang == 'en' else "⏳ EN COURS"
        outcome_emoji = "⏳"
    
    # Get match info
    match_info = "N/A"
    sport = "N/A"
    league = "N/A"
    
    if bet.drop_event_id:
        drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
        if drop:
            match_info = drop.match or "N/A"
            league = drop.league or "N/A"  # League contains sport for manual bets
            sport = league  # Use league as sport
    
    # Calculate values
    profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
    roi = (profit_val / bet.total_stake * 100) if bet.total_stake > 0 else 0
    total_return = bet.total_stake + profit_val
    
    bet_date_str = bet.bet_date.strftime('%Y-%m-%d')
    bet_time_str = bet.bet_date.strftime('%I:%M %p')
    
    # Build message - Style d'alerte complet
    if lang == 'fr':
        message = f"""
{type_emoji} <b>BET #{bet.id} - {type_name}</b>

{outcome_emoji} <b>{outcome_text}</b>

🏟️ <b>{match_info}</b>
🏀 {sport} - {league}
📅 {bet_date_str} à {bet_time_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>RÉSUMÉ FINANCIER</b>

💵 Misé total: <b>${bet.total_stake:,.2f}</b>
✅ Profit: <b>${profit_val:+,.2f}</b>
📊 ROI: <b>{roi:.2f}%</b>
💸 Retour total: <b>${total_return:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        message = f"""
{type_emoji} <b>BET #{bet.id} - {type_name}</b>

{outcome_emoji} <b>{outcome_text}</b>

🏟️ <b>{match_info}</b>
🏀 {sport} - {league}
📅 {bet_date_str} at {bet_time_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>FINANCIAL SUMMARY</b>

💵 Total staked: <b>${bet.total_stake:,.2f}</b>
✅ Profit: <b>${profit_val:+,.2f}</b>
📊 ROI: <b>{roi:.2f}%</b>
💸 Total return: <b>${total_return:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Keyboard with all options
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Éditer" if lang == 'fr' else "✏️ Edit",
                callback_data=f"edit_bet_{bet.id}"
            ),
            InlineKeyboardButton(
                text="🏆 Outcome" if lang == 'en' else "🏆 Résultat",
                callback_data=f"set_outcome_{bet.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Note" if lang == 'fr' else "📝 Note",
                callback_data=f"add_note_{bet.id}"
            ),
            InlineKeyboardButton(
                text="🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete",
                callback_data=f"delete_bet_{bet.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="my_bets"
            )
        ]
    ]
    
    return message, InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data.startswith("view_bet_"))
async def show_bet_details(callback: types.CallbackQuery):
    """Show detailed bet information"""
    await callback.answer()
    
    bet_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get bet
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        # Format message
        message, keyboard = format_bet_details_pro(bet, db, lang)
        
        await callback.message.edit_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error showing bet details: {e}")
        await callback.answer("❌ Error loading bet", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("set_outcome_"))
async def set_bet_outcome(callback: types.CallbackQuery):
    """Menu to set bet outcome"""
    await callback.answer()
    
    bet_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        # For arbitrages, they're always wins
        if bet.bet_type == 'arbitrage':
            text = "⚖️ Arbitrages are automatic wins!\n\n" if lang == 'en' else "⚖️ Les arbitrages sont des gains automatiques!\n\n"
            text += f"Profit: ${bet.expected_profit:+.2f}"
            
            keyboard = [[InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"view_bet_{bet_id}"
            )]]
        else:
            text = f"🏆 SET OUTCOME - BET #{bet_id}\n\n" if lang == 'en' else f"🏆 DÉFINIR RÉSULTAT - BET #{bet_id}\n\n"
            text += "Choose the outcome:" if lang == 'en' else "Choisis le résultat:"
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="✅ WIN / GAGNÉ",
                        callback_data=f"outcome_win_{bet_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ LOSS / PERDU",
                        callback_data=f"outcome_loss_{bet_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🤝 PUSH / NUL",
                        callback_data=f"outcome_push_{bet_id}"
                    ),
                    InlineKeyboardButton(
                        text="⏳ PENDING / EN COURS",
                        callback_data=f"outcome_pending_{bet_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                        callback_data=f"view_bet_{bet_id}"
                    )
                ]
            ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("outcome_"))
async def save_outcome(callback: types.CallbackQuery):
    """Save bet outcome"""
    await callback.answer()
    
    parts = callback.data.split('_')
    outcome = parts[1]  # win, loss, push, pending
    bet_id = int(parts[2])
    
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        bet = db.query(UserBet).filter(
            UserBet.id == bet_id,
            UserBet.user_id == user_id
        ).first()
        
        if not bet:
            await callback.answer("❌ Bet not found", show_alert=True)
            return
        
        # Set actual_profit based on outcome
        if outcome == 'win':
            bet.actual_profit = abs(bet.expected_profit)
        elif outcome == 'loss':
            bet.actual_profit = -bet.total_stake
        elif outcome == 'push':
            bet.actual_profit = 0
        else:  # pending
            bet.actual_profit = None
        
        db.commit()
        
        await callback.answer("✅ Outcome saved!", show_alert=True)
        
        # Refresh bet details
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        message, keyboard = format_bet_details_pro(bet, db, lang)
        
        await callback.message.edit_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error saving outcome: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()
