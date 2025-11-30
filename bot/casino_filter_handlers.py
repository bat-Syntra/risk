"""
Casino Filter Settings Handlers
Allow users to filter alerts by specific casinos
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
import json

from database import SessionLocal
from models.user import User

router = Router()

# Complete list of all casinos with their emojis
ALL_CASINOS = [
    ("888sport", "🎰"),
    ("bet105", "🎲"),
    ("BET99", "💯"),
    ("Betsson", "🔶"),
    ("BetVictor", "👑"),
    ("Betway", "⚡"),
    ("bwin", "🎯"),
    ("Casumo", "💜"),
    ("Coolbet", "❄️"),
    ("iBet", "📱"),
    ("Jackpot.bet", "💎"),
    ("LeoVegas", "🦁"),
    ("Mise-o-jeu", "🎪"),
    ("Pinnacle", "⛰️"),
    ("Proline", "📊"),
    ("Sports Interaction", "🏟️"),
    ("Stake", "✨"),
    ("TonyBet", "🎰"),
]


@router.callback_query(F.data == "casino_filter_menu")
async def show_casino_filter_menu(callback: types.CallbackQuery):
    """Show casino filter menu with all casinos"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get user's selected casinos
        try:
            selected_casinos = json.loads(user.selected_casinos) if user.selected_casinos else []
        except:
            selected_casinos = []
        
        # If empty, all are selected by default
        if not selected_casinos:
            selected_casinos = [casino[0] for casino in ALL_CASINOS]
        
        # Build text
        if lang == 'fr':
            text = (
                "🎰 <b>FILTRER PAR CASINO</b>\n\n"
                "Sélectionne les casinos où tu peux miser.\n"
                "Tu recevras <b>uniquement</b> les alertes de ces casinos.\n\n"
                f"<b>Sélectionnés:</b> {len(selected_casinos)}/{len(ALL_CASINOS)}\n\n"
                "Clique pour activer/désactiver:"
            )
        else:
            text = (
                "🎰 <b>FILTER BY CASINO</b>\n\n"
                "Select casinos where you can bet.\n"
                "You'll receive <b>only</b> alerts from these casinos.\n\n"
                f"<b>Selected:</b> {len(selected_casinos)}/{len(ALL_CASINOS)}\n\n"
                "Click to toggle on/off:"
            )
        
        # Build keyboard - 2 casinos per row
        keyboard = []
        for i in range(0, len(ALL_CASINOS), 2):
            row = []
            for j in range(2):
                if i + j < len(ALL_CASINOS):
                    casino_name, emoji = ALL_CASINOS[i + j]
                    is_selected = casino_name in selected_casinos
                    check = "✅ " if is_selected else "❌ "
                    row.append(InlineKeyboardButton(
                        text=f"{check}{emoji} {casino_name}",
                        callback_data=f"toggle_casino_{i+j}"
                    ))
            keyboard.append(row)
        
        # Add action buttons
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Select All / Tout sélectionner" if lang == 'en' else "✅ Tout sélectionner",
                callback_data="casino_select_all"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Deselect All / Tout désélectionner" if lang == 'en' else "❌ Tout désélectionner",
                callback_data="casino_deselect_all"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Back / Retour" if lang == 'en' else "◀️ Retour",
                callback_data="settings"
            )
        ])
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("toggle_casino_"))
async def toggle_casino(callback: types.CallbackQuery):
    """Toggle a specific casino on/off"""
    await callback.answer()
    
    # Extract casino index
    casino_idx = int(callback.data.split('_')[2])
    casino_name = ALL_CASINOS[casino_idx][0]
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Get current selection
        try:
            selected_casinos = json.loads(user.selected_casinos) if user.selected_casinos else []
        except:
            selected_casinos = []
        
        # If empty, start with all selected
        if not selected_casinos:
            selected_casinos = [casino[0] for casino in ALL_CASINOS]
        
        # Toggle
        if casino_name in selected_casinos:
            selected_casinos.remove(casino_name)
        else:
            selected_casinos.append(casino_name)
        
        # Save
        user.selected_casinos = json.dumps(selected_casinos)
        db.commit()
        
        lang = user.language or 'en'
        emoji = ALL_CASINOS[casino_idx][1]
        status = "✅" if casino_name in selected_casinos else "❌"
        await callback.answer(f"{status} {emoji} {casino_name}")
        
        # Refresh menu
        await show_casino_filter_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data == "casino_select_all")
async def select_all_casinos(callback: types.CallbackQuery):
    """Select all casinos"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Select all
        all_casino_names = [casino[0] for casino in ALL_CASINOS]
        user.selected_casinos = json.dumps(all_casino_names)
        db.commit()
        
        lang = user.language or 'en'
        await callback.answer("✅ All casinos selected" if lang == 'en' else "✅ Tous les casinos sélectionnés", show_alert=True)
        
        # Refresh menu
        await show_casino_filter_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data == "casino_deselect_all")
async def deselect_all_casinos(callback: types.CallbackQuery):
    """Deselect all casinos"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Deselect all (empty list)
        user.selected_casinos = json.dumps([])
        db.commit()
        
        lang = user.language or 'en'
        await callback.answer("❌ All casinos deselected" if lang == 'en' else "❌ Tous les casinos désélectionnés", show_alert=True)
        
        # Refresh menu
        await show_casino_filter_menu(callback)
        
    finally:
        db.close()
