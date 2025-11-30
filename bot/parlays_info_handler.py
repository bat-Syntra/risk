"""
Handler for Parlays Info page - explains what parlays are
"""
from aiogram import Router, types, F
from aiogram.enums import ParseMode
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "parlays_info")
async def handle_parlays_info(callback: types.CallbackQuery):
    """
    Show info page about parlays with buttons to access functionality
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    logger.info(f"🎲 Parlays Info requested by user {user_id}")
    
    # Determine language (default FR)
    # You can add language detection here if needed
    lang = 'fr'
    
    if lang == 'fr':
        message_text = (
            "🎲 <b>PARLAYS - SYSTÈME INTELLIGENT</b>\n\n"
            "⚠️ <b>ACTUELLEMENT EN BETA</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>📚 QU'EST-CE QU'UN PARLAY?</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Un <b>parlay</b> combine plusieurs paris en un seul.\n"
            "TOUS les paris doivent gagner pour que tu gagnes!\n\n"
            "💡 <b>Exemple:</b>\n"
            "• Leg 1: Montreal Canadiens gagnent @ -150\n"
            "• Leg 2: Lakers gagnent @ +120\n"
            "→ Cote combinée: +180 environ\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>🤖 NOTRE SYSTÈME</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Le bot génère automatiquement des parlays +EV:\n\n"
            "✅ <b>Sélection intelligente</b>\n"
            "   Combine les meilleures opportunités détectées\n\n"
            "✅ <b>Edge calculé</b>\n"
            "   Chaque parlay a un edge théorique estimé\n\n"
            "✅ <b>Vérification automatique</b>\n"
            "   Vérifie les cotes en temps réel (marchés supportés)\n\n"
            "✅ <b>Profils de risque</b>\n"
            "   Sûr, Équilibré, Agressif selon tes préférences\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>⚠️ IMPORTANT - BETA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ce système est en <b>version BETA</b>:\n\n"
            "• Les algorithmes sont en amélioration continue\n"
            "• Certaines fonctionnalités peuvent changer\n"
            "• Toujours vérifier manuellement avant de placer\n"
            "• Les edges sont théoriques, pas garantis\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>🎯 COMMENT UTILISER</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Configure tes préférences</b>\n"
            "   → Clique sur \"⚙️ Settings Parlays\"\n"
            "   Choisis:\n"
            "   • Casinos favoris\n"
            "   • Profils de risque\n"
            "   • Limites quotidiennes\n\n"
            "<b>2. Consulte les parlays</b>\n"
            "   → Clique sur \"🎲 Voir Parlays\"\n"
            "   Tu verras tous les parlays générés\n"
            "   avec détails complets et edge estimé\n\n"
            "<b>3. Vérifie et place</b>\n"
            "   Utilise le bouton \"🔍 Vérifier Cotes\"\n"
            "   pour voir si les cotes ont changé\n\n"
            "Bonne chance! 🍀"
        )
    else:  # English
        message_text = (
            "🎲 <b>PARLAYS - SMART SYSTEM</b>\n\n"
            "⚠️ <b>CURRENTLY IN BETA</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>📚 WHAT IS A PARLAY?</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "A <b>parlay</b> combines multiple bets into one.\n"
            "ALL bets must win for you to win!\n\n"
            "💡 <b>Example:</b>\n"
            "• Leg 1: Montreal Canadiens win @ -150\n"
            "• Leg 2: Lakers win @ +120\n"
            "→ Combined odds: ~+180\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>🤖 OUR SYSTEM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "The bot automatically generates +EV parlays:\n\n"
            "✅ <b>Smart selection</b>\n"
            "   Combines best detected opportunities\n\n"
            "✅ <b>Calculated edge</b>\n"
            "   Each parlay has estimated theoretical edge\n\n"
            "✅ <b>Auto verification</b>\n"
            "   Verifies live odds (supported markets)\n\n"
            "✅ <b>Risk profiles</b>\n"
            "   Safe, Balanced, Aggressive per your prefs\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>⚠️ IMPORTANT - BETA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "This system is in <b>BETA version</b>:\n\n"
            "• Algorithms under continuous improvement\n"
            "• Some features may change\n"
            "• Always manually verify before placing\n"
            "• Edges are theoretical, not guaranteed\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>🎯 HOW TO USE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Configure preferences</b>\n"
            "   → Click \"⚙️ Parlay Settings\"\n"
            "   Choose:\n"
            "   • Favorite casinos\n"
            "   • Risk profiles\n"
            "   • Daily limits\n\n"
            "<b>2. View parlays</b>\n"
            "   → Click \"🎲 View Parlays\"\n"
            "   See all generated parlays\n"
            "   with full details and estimated edge\n\n"
            "<b>3. Verify and place</b>\n"
            "   Use \"🔍 Verify Odds\" button\n"
            "   to check if odds have changed\n\n"
            "Good luck! 🍀"
        )
    
    # Build keyboard with Parlays and Settings buttons
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=("🎲 Voir Parlays" if lang == 'fr' else "🎲 View Parlays"),
                callback_data="back_to_parlays"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=("⚙️ Settings Parlays" if lang == 'fr' else "⚙️ Parlay Settings"),
                callback_data="parlay_main_settings"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=("« Retour Menu" if lang == 'fr' else "« Back to Menu"),
                callback_data="menu"
            )
        ]
    ])
    
    try:
        await callback.message.edit_text(
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error editing parlays info message: {e}")
        # Fallback: send new message
        await callback.message.answer(
            message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )


@router.callback_query(F.data == "parlay_main_settings")
async def handle_parlay_main_settings(callback: types.CallbackQuery):
    """Redirect to parlay settings"""
    await callback.answer()
    
    # Import the parlay settings handler
    from bot.parlay_preferences_handler import cmd_parlay_settings
    
    # Get the settings content
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🏢 Sélectionner Casinos", callback_data="settings_casinos")],
        [types.InlineKeyboardButton(text="📊 Profil de Risque", callback_data="settings_risk")],
        [types.InlineKeyboardButton(text="🏀 Filtrer Sports", callback_data="settings_sports")],
        [types.InlineKeyboardButton(text="🔔 Notifications", callback_data="settings_notifications")],
        [types.InlineKeyboardButton(text="💰 Définir Bankroll", callback_data="settings_bankroll")],
        [types.InlineKeyboardButton(text="📈 Paramètres Avancés", callback_data="settings_advanced")],
        [types.InlineKeyboardButton(text="« Retour", callback_data="parlays_info")]
    ])
    
    await callback.message.edit_text(
        "⚙️ <b>PARAMÈTRES PARLAYS</b>\n\n"
        "Personnalisez votre expérience:\n\n"
        "• Choisissez vos casinos préférés\n"
        "• Définissez votre tolérance au risque\n"
        "• Filtrez par sports\n"
        "• Contrôlez les notifications\n"
        "• Suivez votre bankroll\n\n"
        "Que souhaitez-vous configurer?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "menu")
async def handle_menu_callback(callback: types.CallbackQuery):
    """Redirect to main menu"""
    # Just trigger the main_menu callback
    from aiogram.types import CallbackQuery
    
    # Create a new callback with main_menu data
    new_callback = callback.model_copy(update={'data': 'main_menu'})
    
    # Import and call the main menu handler
    from bot.handlers import callback_main_menu
    await callback_main_menu(callback)
