"""
Stake Rounding Settings Handlers
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User
from utils.stake_rounder import get_rounding_display

router = Router()


@router.callback_query(F.data == "stake_rounding_menu")
async def show_stake_rounding_menu(callback: types.CallbackQuery):
    """Show stake rounding options menu"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        current_level = user.stake_rounding or 0
        current_mode = getattr(user, 'rounding_mode', 'nearest') or 'nearest'
        
        # Randomizer settings
        randomizer_enabled = getattr(user, 'stake_randomizer_enabled', False)
        randomizer_amounts = getattr(user, 'stake_randomizer_amounts', '')
        randomizer_mode = getattr(user, 'stake_randomizer_mode', 'random')
        
        # Generate examples with actual rounding using current mode
        from utils.stake_rounder import round_stakes
        
        # Example 1: $353.74 + $396.26 = $750
        ex1_a, ex1_b = 353.74, 396.26
        ex1_prec_a, ex1_prec_b = round_stakes(ex1_a, ex1_b, 750, 0)
        ex1_dol_a, ex1_dol_b = round_stakes(ex1_a, ex1_b, 750, 1)
        ex1_five_a, ex1_five_b = round_stakes(ex1_a, ex1_b, 750, 5)
        ex1_ten_a, ex1_ten_b = round_stakes(ex1_a, ex1_b, 750, 10)
        
        # Example 2: $427.89 + $322.11 = $750
        ex2_a, ex2_b = 427.89, 322.11
        ex2_prec_a, ex2_prec_b = round_stakes(ex2_a, ex2_b, 750, 0)
        ex2_dol_a, ex2_dol_b = round_stakes(ex2_a, ex2_b, 750, 1)
        ex2_five_a, ex2_five_b = round_stakes(ex2_a, ex2_b, 750, 5)
        ex2_ten_a, ex2_ten_b = round_stakes(ex2_a, ex2_b, 750, 10)
        
        # Mode display
        mode_emoji = {'down': '⬇️', 'up': '⬆️', 'nearest': '↕️'}
        mode_text = {
            'down': ('En Bas' if lang == 'fr' else 'Down'),
            'up': ('En Haut' if lang == 'fr' else 'Up'),
            'nearest': ('Au Plus Proche' if lang == 'fr' else 'Nearest')
        }
        mode_display = f"{mode_emoji.get(current_mode, '↕️')} {mode_text.get(current_mode, 'Nearest')}"
        
        # Build text
        if lang == 'fr':
            text = (
                "🎲 <b>ARRONDI DES STAKES</b>\n\n"
                "Pour éviter d'être détecté, arrondis tes stakes d'arbitrage:\n\n"
                f"<b>Niveau:</b> {get_rounding_display(current_level, lang)}\n"
                f"<b>Mode:</b> {mode_display}\n\n"
                "📝 <b>Exemple 1 (Budget $750):</b>\n"
                f"• Précis: ${ex1_prec_a:.2f} + ${ex1_prec_b:.2f}\n"
                f"• Dollar: ${ex1_dol_a:.0f} + ${ex1_dol_b:.0f}\n"
                f"• 5$: ${ex1_five_a:.0f} + ${ex1_five_b:.0f}\n"
                f"• 10$: ${ex1_ten_a:.0f} + ${ex1_ten_b:.0f}\n\n"
                "📝 <b>Exemple 2 (Budget $750):</b>\n"
                f"• Précis: ${ex2_prec_a:.2f} + ${ex2_prec_b:.2f}\n"
                f"• Dollar: ${ex2_dol_a:.0f} + ${ex2_dol_b:.0f}\n"
                f"• 5$: ${ex2_five_a:.0f} + ${ex2_five_b:.0f}\n"
                f"• 10$: ${ex2_ten_a:.0f} + ${ex2_ten_b:.0f}\n\n"
                "💡 <b>Recommandé:</b> 5$ ou 10$ (moins suspect)\n\n"
                f"🎲 <b>Randomizer:</b> {'✅ ON' if randomizer_enabled else '❌ OFF'}\n"
                f"→ Montants: {randomizer_amounts if randomizer_amounts else 'Aucun'}\n"
                f"→ Mode: {randomizer_mode.upper()}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 <b>MODES D'ARRONDI</b>\n\n"
                "⬇️ <b>En Bas:</b>\n"
                "• Arrondit toujours vers le bas\n"
                "• Économise ton CASHH (dépense moins)\n"
                "• Ex: $353.74 → $350 (avec 5$)\n\n"
                "↕️ <b>Au Plus Proche:</b>\n"
                "• Arrondit au multiple le plus proche\n"
                "• Équilibré (recommandé)\n"
                "• Ex: $353.74 → $355 (avec 5$)\n\n"
                "⬆️ <b>En Haut:</b>\n"
                "• Arrondit toujours vers le haut\n"
                "• Peut dépasser ton budget (flexible)\n"
                "• Ex: $353.74 → $355 (avec 5$)\n"
                "• Total peut être > CASHH configuré"
            )
        else:
            text = (
                "🎲 <b>STAKE ROUNDING</b>\n\n"
                "To avoid detection, round your arbitrage stakes:\n\n"
                f"<b>Level:</b> {get_rounding_display(current_level, lang)}\n"
                f"<b>Mode:</b> {mode_display}\n\n"
                "📝 <b>Example 1 (Budget $750):</b>\n"
                f"• Precise: ${ex1_prec_a:.2f} + ${ex1_prec_b:.2f}\n"
                f"• Dollar: ${ex1_dol_a:.0f} + ${ex1_dol_b:.0f}\n"
                f"• 5$: ${ex1_five_a:.0f} + ${ex1_five_b:.0f}\n"
                f"• 10$: ${ex1_ten_a:.0f} + ${ex1_ten_b:.0f}\n\n"
                "📝 <b>Example 2 (Budget $750):</b>\n"
                f"• Precise: ${ex2_prec_a:.2f} + ${ex2_prec_b:.2f}\n"
                f"• Dollar: ${ex2_dol_a:.0f} + ${ex2_dol_b:.0f}\n"
                f"• 5$: ${ex2_five_a:.0f} + ${ex2_five_b:.0f}\n"
                f"• 10$: ${ex2_ten_a:.0f} + ${ex2_ten_b:.0f}\n\n"
                "💡 <b>Recommended:</b> 5$ or 10$ (less suspicious)\n\n"
                f"🎲 <b>Randomizer:</b> {'✅ ON' if randomizer_enabled else '❌ OFF'}\n"
                f"→ Amounts: {randomizer_amounts if randomizer_amounts else 'None'}\n"
                f"→ Mode: {randomizer_mode.upper()}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📌 <b>ROUNDING MODES</b>\n\n"
                "⬇️ <b>Down:</b>\n"
                "• Always rounds down\n"
                "• Saves your CASHH (spend less)\n"
                "• Ex: $353.74 → $350 (with 5$)\n\n"
                "↕️ <b>Nearest:</b>\n"
                "• Rounds to nearest multiple\n"
                "• Balanced (recommended)\n"
                "• Ex: $353.74 → $355 (with 5$)\n\n"
                "⬆️ <b>Up:</b>\n"
                "• Always rounds up\n"
                "• Can exceed budget (flexible)\n"
                "• Ex: $353.74 → $355 (with 5$)\n"
                "• Total can be > configured CASHH"
            )
        
        # Build keyboard
        keyboard = []
        
        # Rounding level buttons
        for level in [0, 1, 5, 10]:
            display = get_rounding_display(level, lang)
            check = "✅ " if level == current_level else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{check}{display}",
                callback_data=f"set_rounding_{level}"
            )])
        
        # Add separator
        if lang == 'fr':
            keyboard.append([InlineKeyboardButton(text="━━━━━ MODE D'ARRONDI ━━━━━", callback_data="ignore")])
        else:
            keyboard.append([InlineKeyboardButton(text="━━━━━ ROUNDING MODE ━━━━━", callback_data="ignore")])
        
        # Rounding mode buttons (3 in a row)
        mode_buttons = []
        for mode in ['down', 'nearest', 'up']:
            check = "✅ " if mode == current_mode else ""
            mode_label = mode_text[mode]
            mode_buttons.append(InlineKeyboardButton(
                text=f"{check}{mode_emoji[mode]} {mode_label}",
                callback_data=f"set_mode_{mode}"
            ))
        keyboard.append(mode_buttons)
        
        # Add explanation for modes
        if lang == 'fr':
            keyboard.append([InlineKeyboardButton(text="⬇️ = Économise CASHH  |  ⬆️ = Peut dépasser", callback_data="ignore")])
        else:
            keyboard.append([InlineKeyboardButton(text="⬇️ = Saves CASHH  |  ⬆️ = Can exceed", callback_data="ignore")])
        
        # Randomizer button
        randomizer_text = "🎲 Randomizer Stake" + (" ✅" if randomizer_enabled else "")
        keyboard.append([InlineKeyboardButton(
            text=randomizer_text,
            callback_data="stake_randomizer_menu"
        )])
        
        keyboard.append([InlineKeyboardButton(
            text="◀️ Back / Retour" if lang == 'en' else "◀️ Retour",
            callback_data="settings"
        )])
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("set_rounding_"))
async def set_stake_rounding(callback: types.CallbackQuery):
    """Set stake rounding level"""
    await callback.answer()
    
    # Extract level from callback data
    level = int(callback.data.split('_')[2])
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Update user's rounding preference
        user.stake_rounding = level
        db.commit()
        
        lang = user.language or 'en'
        display = get_rounding_display(level, lang)
        
        if lang == 'fr':
            await callback.answer(f"✅ Arrondi: {display}", show_alert=True)
        else:
            await callback.answer(f"✅ Rounding: {display}", show_alert=True)
        
        # Refresh menu
        await show_stake_rounding_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("set_mode_"))
async def set_rounding_mode(callback: types.CallbackQuery):
    """Set stake rounding mode (down/nearest/up)"""
    await callback.answer()
    
    # Extract mode from callback data
    mode = callback.data.split('_')[2]  # down, nearest, or up
    
    if mode not in ['down', 'nearest', 'up']:
        await callback.answer("❌ Invalid mode", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Update user's rounding mode
        user.rounding_mode = mode
        db.commit()
        
        lang = user.language or 'en'
        mode_names = {
            'down': ('En Bas (économise CASHH)' if lang == 'fr' else 'Down (saves CASHH)'),
            'nearest': ('Au Plus Proche (équilibré)' if lang == 'fr' else 'Nearest (balanced)'),
            'up': ('En Haut (peut dépasser)' if lang == 'fr' else 'Up (can exceed)')
        }
        display = mode_names.get(mode, mode)
        
        if lang == 'fr':
            await callback.answer(f"✅ Mode: {display}", show_alert=True)
        else:
            await callback.answer(f"✅ Mode: {display}", show_alert=True)
        
        # Refresh menu
        await show_stake_rounding_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    """Ignore callback for separator buttons"""
    await callback.answer()


@router.callback_query(F.data == "stake_randomizer_menu")
async def show_randomizer_menu(callback: types.CallbackQuery):
    """Show stake randomizer configuration menu"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        lang = user.language or 'en'
        
        # Get current randomizer settings
        randomizer_enabled = getattr(user, 'stake_randomizer_enabled', False)
        randomizer_amounts = getattr(user, 'stake_randomizer_amounts', '')
        randomizer_mode = getattr(user, 'stake_randomizer_mode', 'random')
        
        # Parse selected amounts
        selected_amounts = randomizer_amounts.split(',') if randomizer_amounts else []
        
        # Build text
        if lang == 'fr':
            text = (
                "🎲 <b>RANDOMIZER STAKE</b>\n\n"
                "Pour avoir l'air plus humain, randomise tes stakes à chaque call!\n\n"
                f"<b>Status:</b> {'✅ ACTIVÉ' if randomizer_enabled else '❌ DÉSACTIVÉ'}\n"
                f"<b>Montants sélectionnés:</b> {randomizer_amounts if randomizer_amounts else 'Aucun'}\n"
                f"<b>Mode:</b> {randomizer_mode.upper()}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💡 <b>COMMENT ÇA MARCHE?</b>\n\n"
                "À chaque call, le bot va ajouter/retirer un montant aléatoire à tes stakes:\n\n"
                "<b>Exemple avec [5$, 10$] + Mode RANDOM:</b>\n"
                "• Call 1: +$5 → $355 devient $360\n"
                "• Call 2: -$10 → $430 devient $420\n"
                "• Call 3: +$10 → $350 devient $360\n"
                "• Call 4: -$5 → $355 devient $350\n\n"
                "Les casinos ne verront jamais le même pattern! 🎯\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📌 <b>MODES DE RANDOMISATION</b>\n\n"
                "⬆️ <b>PLUS HAUT:</b>\n"
                "• Toujours ajouter (+$1, +$5, +$10)\n"
                "• Stakes légèrement plus élevés\n\n"
                "⬇️ <b>PLUS BAS:</b>\n"
                "• Toujours retirer (-$1, -$5, -$10)\n"
                "• Économise ton CASHH\n\n"
                "🎲 <b>ALÉATOIRE:</b> (Recommandé)\n"
                "• Parfois +, parfois -\n"
                "• Pattern complètement imprévisible\n"
                "• Maximum de camouflage!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            text = (
                "🎲 <b>STAKE RANDOMIZER</b>\n\n"
                "To look more human, randomize your stakes on each call!\n\n"
                f"<b>Status:</b> {'✅ ENABLED' if randomizer_enabled else '❌ DISABLED'}\n"
                f"<b>Selected amounts:</b> {randomizer_amounts if randomizer_amounts else 'None'}\n"
                f"<b>Mode:</b> {randomizer_mode.upper()}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💡 <b>HOW IT WORKS?</b>\n\n"
                "On each call, the bot will add/subtract a random amount to your stakes:\n\n"
                "<b>Example with [5$, 10$] + RANDOM mode:</b>\n"
                "• Call 1: +$5 → $355 becomes $360\n"
                "• Call 2: -$10 → $430 becomes $420\n"
                "• Call 3: +$10 → $350 becomes $360\n"
                "• Call 4: -$5 → $355 becomes $350\n\n"
                "Casinos will never see the same pattern! 🎯\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📌 <b>RANDOMIZATION MODES</b>\n\n"
                "⬆️ <b>HIGHER:</b>\n"
                "• Always add (+$1, +$5, +$10)\n"
                "• Slightly higher stakes\n\n"
                "⬇️ <b>LOWER:</b>\n"
                "• Always subtract (-$1, -$5, -$10)\n"
                "• Saves your CASHH\n\n"
                "🎲 <b>RANDOM:</b> (Recommended)\n"
                "• Sometimes +, sometimes -\n"
                "• Completely unpredictable pattern\n"
                "• Maximum camouflage!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        # Build keyboard
        keyboard = []
        
        # Toggle ON/OFF
        toggle_text = "❌ Désactiver" if randomizer_enabled else "✅ Activer"
        if lang == 'en':
            toggle_text = "❌ Disable" if randomizer_enabled else "✅ Enable"
        keyboard.append([InlineKeyboardButton(
            text=toggle_text,
            callback_data="toggle_randomizer"
        )])
        
        # Separator
        keyboard.append([InlineKeyboardButton(
            text="━━━━ MONTANTS / AMOUNTS ━━━━",
            callback_data="ignore"
        )])
        
        # Amount selection buttons (multi-select)
        amount_buttons = []
        for amount in ['1', '5', '10']:
            check = "✅ " if amount in selected_amounts else ""
            amount_buttons.append(InlineKeyboardButton(
                text=f"{check}{amount}$",
                callback_data=f"toggle_rand_amount_{amount}"
            ))
        keyboard.append(amount_buttons)
        
        # Separator
        keyboard.append([InlineKeyboardButton(
            text="━━━━━ MODE ━━━━━",
            callback_data="ignore"
        )])
        
        # Mode buttons
        mode_buttons = []
        mode_labels = {
            'up': ('⬆️ Plus Haut' if lang == 'fr' else '⬆️ Higher'),
            'down': ('⬇️ Plus Bas' if lang == 'fr' else '⬇️ Lower'),
            'random': ('🎲 Aléatoire' if lang == 'fr' else '🎲 Random')
        }
        for mode in ['up', 'down', 'random']:
            check = "✅ " if mode == randomizer_mode else ""
            mode_buttons.append(InlineKeyboardButton(
                text=f"{check}{mode_labels[mode]}",
                callback_data=f"set_rand_mode_{mode}"
            ))
        keyboard.append(mode_buttons)
        
        # Back button
        keyboard.append([InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="stake_rounding_menu"
        )])
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        
    finally:
        db.close()


@router.callback_query(F.data == "toggle_randomizer")
async def toggle_randomizer(callback: types.CallbackQuery):
    """Toggle randomizer ON/OFF"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Toggle
        current = getattr(user, 'stake_randomizer_enabled', False)
        user.stake_randomizer_enabled = not current
        db.commit()
        
        lang = user.language or 'en'
        status = "✅ ACTIVÉ" if not current else "❌ DÉSACTIVÉ"
        if lang == 'en':
            status = "✅ ENABLED" if not current else "❌ DISABLED"
        
        await callback.answer(f"Randomizer: {status}", show_alert=True)
        
        # Refresh menu
        await show_randomizer_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("toggle_rand_amount_"))
async def toggle_randomizer_amount(callback: types.CallbackQuery):
    """Toggle a randomizer amount (1, 5, or 10)"""
    await callback.answer()
    
    # Extract amount
    amount = callback.data.split('_')[-1]  # '1', '5', or '10'
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Get current amounts
        current_amounts = getattr(user, 'stake_randomizer_amounts', '')
        amounts_list = current_amounts.split(',') if current_amounts else []
        
        # Toggle this amount
        if amount in amounts_list:
            amounts_list.remove(amount)
        else:
            amounts_list.append(amount)
        
        # Update user
        user.stake_randomizer_amounts = ','.join(sorted(amounts_list)) if amounts_list else ''
        db.commit()
        
        lang = user.language or 'en'
        if amount in amounts_list:
            msg = f"✅ Ajouté: {amount}$" if lang == 'fr' else f"✅ Added: {amount}$"
        else:
            msg = f"❌ Retiré: {amount}$" if lang == 'fr' else f"❌ Removed: {amount}$"
        
        await callback.answer(msg)
        
        # Refresh menu
        await show_randomizer_menu(callback)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("set_rand_mode_"))
async def set_randomizer_mode(callback: types.CallbackQuery):
    """Set randomizer mode (up, down, random)"""
    await callback.answer()
    
    # Extract mode
    mode = callback.data.split('_')[-1]  # 'up', 'down', or 'random'
    
    if mode not in ['up', 'down', 'random']:
        await callback.answer("❌ Invalid mode", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User not found", show_alert=True)
            return
        
        # Update mode
        user.stake_randomizer_mode = mode
        db.commit()
        
        lang = user.language or 'en'
        mode_names = {
            'up': ('Plus Haut' if lang == 'fr' else 'Higher'),
            'down': ('Plus Bas' if lang == 'fr' else 'Lower'),
            'random': ('Aléatoire' if lang == 'fr' else 'Random')
        }
        
        await callback.answer(f"✅ Mode: {mode_names[mode]}", show_alert=True)
        
        # Refresh menu
        await show_randomizer_menu(callback)
        
    finally:
        db.close()
