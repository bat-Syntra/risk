"""
Percentage filters for alerts (Arbitrage, Middle, Good EV)
Allows users to set min/max % thresholds for each bet type
"""
import logging
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "percent_filters")
async def show_percent_filters_menu(callback: types.CallbackQuery):
    """Show percentage filters menu with 3 categories"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        if lang == 'fr':
            text = (
                "📊 <b>FILTRES PAR POURCENTAGE</b>\n\n"
                "Définis les % minimum et maximum pour chaque type de bet.\n"
                "Tu ne recevras que les calls dans ta plage.\n\n"
                f"⚖️ <b>Arbitrage:</b> {user.min_arb_percent}% - {user.max_arb_percent}%\n"
                f"🎯 <b>Middle:</b> {user.min_middle_percent}% - {user.max_middle_percent}%\n"
                f"💎 <b>Good +EV:</b> {user.min_good_ev_percent}% - {user.max_good_ev_percent}%\n\n"
                "Clique sur une catégorie pour ajuster:"
            )
        else:
            text = (
                "📊 <b>PERCENTAGE FILTERS</b>\n\n"
                "Set min and max % for each bet type.\n"
                "You'll only receive calls within your range.\n\n"
                f"⚖️ <b>Arbitrage:</b> {user.min_arb_percent}% - {user.max_arb_percent}%\n"
                f"🎯 <b>Middle:</b> {user.min_middle_percent}% - {user.max_middle_percent}%\n"
                f"💎 <b>Good +EV:</b> {user.min_good_ev_percent}% - {user.max_good_ev_percent}%\n\n"
                "Click a category to adjust:"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="⚖️ Arbitrage" if lang == 'en' else "⚖️ Arbitrage",
                callback_data="filter_arb"
            )],
            [InlineKeyboardButton(
                text="🎯 Middle Bet" if lang == 'en' else "🎯 Middle Bet",
                callback_data="filter_middle"
            )],
            [InlineKeyboardButton(
                text="💎 Good +EV" if lang == 'en' else "💎 Good +EV",
                callback_data="filter_goodev"
            )],
            [InlineKeyboardButton(
                text="◀️ Back to Settings" if lang == 'en' else "◀️ Retour Settings",
                callback_data="show_settings"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("filter_"))
async def show_filter_category(callback: types.CallbackQuery):
    """Show min/max options for a specific category"""
    await callback.answer()
    
    category = callback.data.split("_")[1]  # arb, middle, goodev
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get current values
        if category == "arb":
            min_val = user.min_arb_percent
            max_val = user.max_arb_percent
            title = "⚖️ ARBITRAGE"
        elif category == "middle":
            min_val = user.min_middle_percent
            max_val = user.max_middle_percent
            title = "🎯 MIDDLE BET"
        else:  # goodev
            min_val = user.min_good_ev_percent
            max_val = user.max_good_ev_percent
            title = "💎 GOOD +EV"
        
        if lang == 'fr':
            text = (
                f"📊 <b>FILTRE {title}</b>\n\n"
                f"Plage actuelle: <b>{min_val}% - {max_val}%</b>\n\n"
                "Ajuste le minimum et/ou le maximum:"
            )
        else:
            text = (
                f"📊 <b>{title} FILTER</b>\n\n"
                f"Current range: <b>{min_val}% - {max_val}%</b>\n\n"
                "Adjust minimum and/or maximum:"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text=f"📉 Min: {min_val}%" if lang == 'en' else f"📉 Min: {min_val}%",
                callback_data=f"setmin_{category}"
            )],
            [InlineKeyboardButton(
                text=f"📈 Max: {max_val}%" if lang == 'en' else f"📈 Max: {max_val}%",
                callback_data=f"setmax_{category}"
            )],
            [InlineKeyboardButton(
                text="◀️ Back" if lang == 'en' else "◀️ Retour",
                callback_data="percent_filters"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("setmin_") | F.data.startswith("setmax_"))
async def show_percent_options(callback: types.CallbackQuery):
    """Show quick percent options"""
    await callback.answer()
    
    parts = callback.data.split("_")
    min_or_max = parts[0]  # setmin or setmax
    category = parts[1]  # arb, middle, goodev
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Category title
        if category == "arb":
            title = "⚖️ Arbitrage"
        elif category == "middle":
            title = "🎯 Middle"
        else:
            title = "💎 Good +EV"
        
        is_min = (min_or_max == "setmin")
        
        if lang == 'fr':
            text = (
                f"📊 <b>{title} - {'MIN' if is_min else 'MAX'}</b>\n\n"
                f"Choisis un pourcentage:"
            )
        else:
            text = (
                f"📊 <b>{title} - {'MIN' if is_min else 'MAX'}</b>\n\n"
                f"Choose a percentage:"
            )
        
        # Quick options
        if is_min:
            # Min options: 0.5, 1, 2, 3, 4, 5, 10
            options = [0.5, 1, 2, 3, 4, 5, 10]
        else:
            # Max options: 5, 10, 20, 50, 100
            options = [5, 10, 20, 50, 100]
        
        keyboard = []
        # 2 buttons per row
        for i in range(0, len(options), 2):
            row = []
            for j in range(2):
                if i + j < len(options):
                    val = options[i + j]
                    row.append(InlineKeyboardButton(
                        text=f"{val}%",
                        callback_data=f"apply_{min_or_max}_{category}_{val}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(
            text="◀️ Back" if lang == 'en' else "◀️ Retour",
            callback_data=f"filter_{category}"
        )])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("apply_"))
async def apply_percent_filter(callback: types.CallbackQuery):
    """Apply the selected percentage filter"""
    await callback.answer()
    
    # Format: apply_setmin_arb_2 or apply_setmax_middle_10
    parts = callback.data.split("_")
    min_or_max = parts[1]  # setmin or setmax
    category = parts[2]  # arb, middle, goodev
    value = float(parts[3])
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        is_min = (min_or_max == "setmin")
        
        # Update the appropriate field
        if category == "arb":
            if is_min:
                user.min_arb_percent = value
            else:
                user.max_arb_percent = value
        elif category == "middle":
            if is_min:
                user.min_middle_percent = value
            else:
                user.max_middle_percent = value
        else:  # goodev
            if is_min:
                user.min_good_ev_percent = value
            else:
                user.max_good_ev_percent = value
        
        db.commit()
        
        if lang == 'fr':
            await callback.answer(f"✅ {'Min' if is_min else 'Max'} mis à {value}%", show_alert=True)
        else:
            await callback.answer(f"✅ {'Min' if is_min else 'Max'} set to {value}%", show_alert=True)
        
        # Return to category filter menu
        await show_filter_category(callback)
        
    except Exception as e:
        logger.error(f"Error applying filter: {e}")
        await callback.answer("❌ Error", show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data == "show_settings")
async def callback_show_settings(callback: types.CallbackQuery):
    """Redirect back to the unified settings screen"""
    await callback.answer()
    # Import here to avoid circular dependency
    from bot.handlers import callback_settings

    # Reuse the main settings callback so there is only ONE settings UI
    await callback_settings(callback)
