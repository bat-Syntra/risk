"""
Sport Filter Menu - Settings handler for filtering alerts by sport
"""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from database import SessionLocal
from models.user import User
import json

router = Router()


@router.callback_query(F.data == "sport_filter_menu")
async def show_sport_filter_menu(callback: types.CallbackQuery):
    """Show sport filter selection menu"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get currently selected sports
        try:
            selected_sports = json.loads(user.selected_sports) if user.selected_sports else []
        except:
            selected_sports = []
        
        # If empty list, means ALL sports selected
        all_selected = len(selected_sports) == 0
        
        if lang == 'fr':
            text = (
                "🏅 <b>FILTRER PAR SPORT</b>\n\n"
                "Sélectionne les sports pour lesquels tu veux recevoir des alertes.\n\n"
                "Par défaut, tous les sports sont activés.\n"
                "Clique sur un sport pour l'activer/désactiver.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        else:
            text = (
                "🏅 <b>FILTER BY SPORT</b>\n\n"
                "Select which sports you want to receive alerts for.\n\n"
                "By default, all sports are enabled.\n"
                "Click on a sport to enable/disable it.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        
        # Define sports with their emojis
        sports = [
            ('basketball', '🏀', 'Basketball (NBA, NCAA)', 'Basketball (NBA, NCAA)'),
            ('soccer', '⚽', 'Soccer', 'Soccer'),
            ('tennis', '🎾', 'Tennis (ATP, WTA)', 'Tennis (ATP, WTA)'),
            ('hockey', '🏒', 'Hockey (NHL)', 'Hockey (NHL)'),
            ('football', '🏈', 'Football (NFL)', 'Football (NFL)'),
            ('baseball', '⚾', 'Baseball (MLB)', 'Baseball (MLB)'),
            ('mma', '🥊', 'MMA (UFC)', 'MMA (UFC)')
        ]
        
        # Build keyboard
        keyboard = []
        
        # "All sports" button
        all_checked = "✅" if all_selected else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{all_checked} Tous les sports" if lang == 'fr' else f"{all_checked} All sports",
                callback_data="sport_toggle_all"
            )
        ])
        
        # Individual sport buttons (2 per row)
        for i in range(0, len(sports), 2):
            row = []
            for j in range(2):
                if i + j < len(sports):
                    sport_key, emoji, name_fr, name_en = sports[i + j]
                    checked = "✅" if (all_selected or sport_key in selected_sports) else "⬜"
                    sport_name = name_fr if lang == 'fr' else name_en
                    
                    row.append(InlineKeyboardButton(
                        text=f"{checked} {emoji} {sport_name}",
                        callback_data=f"sport_toggle_{sport_key}"
                    ))
            keyboard.append(row)
        
        # Back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour aux Réglages" if lang == 'fr' else "◀️ Back to Settings",
                callback_data="settings"
            )
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "sport_toggle_all")
async def toggle_all_sports(callback: types.CallbackQuery):
    """Toggle all sports on/off"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get current selection
        try:
            selected_sports = json.loads(user.selected_sports) if user.selected_sports else []
        except:
            selected_sports = []
        
        # If currently all selected (empty list), deselect all
        # If not all selected, select all (empty list = all)
        if len(selected_sports) == 0:
            # Currently all selected → deselect all (select none)
            # We'll select just one sport to have something
            user.selected_sports = json.dumps(['basketball'])
            await callback.answer("⚠️ Au moins 1 sport requis" if lang == 'fr' else "⚠️ At least 1 sport required", show_alert=True)
        else:
            # Not all selected → select all
            user.selected_sports = None  # null = all sports
            await callback.answer("✅ Tous les sports sélectionnés" if lang == 'fr' else "✅ All sports selected")
        
        db.commit()
        
        # Refresh menu
        await show_sport_filter_menu(callback)
    finally:
        db.close()


@router.callback_query(F.data.startswith("sport_toggle_"))
async def toggle_sport(callback: types.CallbackQuery):
    """Toggle individual sport"""
    sport_key = callback.data.replace("sport_toggle_", "")
    
    # Ignore "all" here (handled separately)
    if sport_key == "all":
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get current selection
        try:
            selected_sports = json.loads(user.selected_sports) if user.selected_sports else []
        except:
            selected_sports = []
        
        # If currently all selected (empty list), initialize with all sports except the one being toggled off
        all_sports = ['basketball', 'soccer', 'tennis', 'hockey', 'football', 'baseball', 'mma']
        
        if len(selected_sports) == 0:
            # All were selected, user is deselecting one
            selected_sports = [s for s in all_sports if s != sport_key]
        else:
            # Toggle the sport
            if sport_key in selected_sports:
                # Deselect
                selected_sports.remove(sport_key)
                # If list becomes empty after removal, prevent it (need at least 1)
                if len(selected_sports) == 0:
                    selected_sports = [sport_key]
                    await callback.answer("⚠️ Au moins 1 sport requis" if lang == 'fr' else "⚠️ At least 1 sport required", show_alert=True)
                    db.close()
                    return
            else:
                # Select
                selected_sports.append(sport_key)
                # If all sports are now selected, set to null (all)
                if len(selected_sports) == len(all_sports):
                    selected_sports = []
        
        # Save
        if len(selected_sports) == 0:
            user.selected_sports = None  # All sports
        else:
            user.selected_sports = json.dumps(selected_sports)
        
        db.commit()
        
        # Sport names for feedback
        sport_names = {
            'basketball': ('Basketball', 'Basketball'),
            'soccer': ('Soccer', 'Soccer'),
            'tennis': ('Tennis', 'Tennis'),
            'hockey': ('Hockey', 'Hockey'),
            'football': ('Football', 'Football'),
            'baseball': ('Baseball', 'Baseball'),
            'mma': ('MMA', 'MMA')
        }
        
        sport_name_fr, sport_name_en = sport_names.get(sport_key, ('Sport', 'Sport'))
        sport_name = sport_name_fr if lang == 'fr' else sport_name_en
        
        is_selected = sport_key in (selected_sports if selected_sports else all_sports)
        status = "✅" if is_selected else "❌"
        
        await callback.answer(f"{status} {sport_name}")
        
        # Refresh menu
        await show_sport_filter_menu(callback)
    finally:
        db.close()
