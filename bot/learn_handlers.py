"""
Learn System - Guide complet d'arbitrage
Toutes les sections du guide /learn
"""
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from bot.message_manager import BotMessageManager
from database import SessionLocal
from models.user import User

router = Router()


@router.message(Command("learn"))
async def learn_command(message: types.Message, state: FSMContext):
    """Command /learn - Redirect to new Pro Guide with tier-based access"""
    # Block access if user hasn't accepted terms yet
    current_state = await state.get_state()
    if current_state == "OnboardingStates:awaiting_terms_acceptance":
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
            lang = (user.language if user else "en")
        finally:
            db.close()
        
        if lang == 'fr':
            await message.answer(
                "⚠️ Tu dois d'abord accepter les termes en cliquant sur <b>✅ J'ACCEPTE</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                "⚠️ You must first accept the terms by clicking <b>✅ I ACCEPT</b>",
                parse_mode=ParseMode.HTML
            )
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    # Redirect to new Pro Guide
    if lang == 'fr':
        text = (
            "📖 <b>GUIDE COMPLET RISKO</b>\n\n"
            "Le guide a été amélioré avec:\n"
            "✅ Accès par niveaux (FREE vs PREMIUM)\n"
            "✅ Success stories réelles\n"
            "✅ Comparaisons détaillées\n"
            "✅ Guides exclusifs PREMIUM\n\n"
            "Accède au nouveau guide ci-dessous!"
        )
    else:
        text = (
            "📖 <b>COMPLETE RISKO GUIDE</b>\n\n"
            "The guide has been improved with:\n"
            "✅ Tier-based access (FREE vs PREMIUM)\n"
            "✅ Real success stories\n"
            "✅ Detailed comparisons\n"
            "✅ Exclusive PREMIUM guides\n\n"
            "Access the new guide below!"
        )
    
    kb = [
        [InlineKeyboardButton(text="📖 Open Complete Guide" if lang == 'en' else "📖 Ouvrir le Guide Complet", callback_data="learn_guide_pro")],
        [InlineKeyboardButton(text="📱 Main Menu" if lang == 'en' else "📱 Menu Principal", callback_data="main_menu")]
    ]
    
    await BotMessageManager.send_or_edit(
        event=message,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.HTML
    )
    return

    # Old system below (kept as backup, unreachable code)
    if lang == 'fr':
        title = (
            "📖 <b>GUIDE COMPLET RISK0</b>\n\n"
            "⏱️ <b>Temps de lecture: 5–10 minutes</b>\n"
            "💰 <b>Éviter des erreurs à $100-500+</b>\n\n"
            "Sélectionne une section:\n"
        )
        kb = [
            [InlineKeyboardButton(text="🚀 START HERE - Pourquoi lire ce guide?", callback_data="guide_start")],
            [InlineKeyboardButton(text="📖 Introduction - C'est quoi l'arbitrage?", callback_data="learn_intro")],
            [InlineKeyboardButton(text="🎯 Modes - SAFE vs RISKED expliqué", callback_data="learn_modes")],
            [InlineKeyboardButton(text="💰 CASHH - Budget et gestion", callback_data="learn_bankroll")],
            [InlineKeyboardButton(text="⚡ How to Place - Placer un arb", callback_data="learn_howto")],
            [InlineKeyboardButton(text="💎 Using I BET - Tracker vos profits", callback_data="learn_ibet")],
            [InlineKeyboardButton(text="⚠️ Mistakes - Erreurs qui coûtent cher", callback_data="learn_mistakes")],
            [InlineKeyboardButton(text="📱 Outils - Calculateur, Stats, Paramètres", callback_data="learn_tools")],
            [InlineKeyboardButton(text="🛡️ Avoid Bans - Rester sous le radar", callback_data="learn_avoid_bans")],
            [InlineKeyboardButton(text="🏦 Bookmakers - Setup & choix", callback_data="learn_books")],
            [InlineKeyboardButton(text="💎 Good Odds - Positive EV bets", callback_data="learn_good_odds")],
            [InlineKeyboardButton(text="🎯 Middle Bets - EV+ lottery", callback_data="learn_middle")],
            [InlineKeyboardButton(text="🎓 Pro Tips - Maximiser gains", callback_data="learn_advanced")],
            [InlineKeyboardButton(text="⚖️ Tax & Legal - Légalité et impôts", callback_data="learn_legal")],
            [InlineKeyboardButton(text="❓ FAQ - Questions fréquentes", callback_data="learn_faq")],
            [InlineKeyboardButton(text="📱 Menu Principal", callback_data="main_menu")],
        ]
    else:
        title = (
            "📖 <b>COMPLETE RISK0 GUIDE</b>\n\n"
            "⏱️ <b>Reading time: 5–10 minutes</b>\n"
            "💰 <b>Potential: Avoid $100-500+ mistakes</b>\n\n"
            "Select a section:\n"
        )
        kb = [
            [InlineKeyboardButton(text="🚀 START HERE - Why read this guide?", callback_data="guide_start")],
            [InlineKeyboardButton(text="📖 Introduction - What is arbitrage?", callback_data="learn_intro")],
            [InlineKeyboardButton(text="🎯 Modes - SAFE vs RISKED explained", callback_data="learn_modes")],
            [InlineKeyboardButton(text="💰 CASHH - Budget management", callback_data="learn_bankroll")],
            [InlineKeyboardButton(text="⚡ How to Place - Step by step", callback_data="learn_howto")],
            [InlineKeyboardButton(text="💎 Using I BET - Track your profits", callback_data="learn_ibet")],
            [InlineKeyboardButton(text="⚠️ Mistakes - Costly errors", callback_data="learn_mistakes")],
            [InlineKeyboardButton(text="📱 Tools - Calculator, Stats, Settings", callback_data="learn_tools")],
            [InlineKeyboardButton(text="🛡️ Avoid Bans - Stay under the radar", callback_data="learn_avoid_bans")],
            [InlineKeyboardButton(text="🏦 Bookmakers - Setup & choices", callback_data="learn_books")],
            [InlineKeyboardButton(text="💎 Good Odds - Positive EV bets", callback_data="learn_good_odds")],
            [InlineKeyboardButton(text="🎯 Middle Bets - EV+ lottery", callback_data="learn_middle")],
            [InlineKeyboardButton(text="🎓 Pro Tips - Maximize gains", callback_data="learn_advanced")],
            [InlineKeyboardButton(text="⚖️ Tax & Legal - Legality & taxes", callback_data="learn_legal")],
            [InlineKeyboardButton(text="❓ FAQ - Frequently Asked Questions", callback_data="learn_faq")],
            [InlineKeyboardButton(text="📱 Main Menu", callback_data="main_menu")],
        ]

    await BotMessageManager.send_or_edit(
        event=message,
        text=title,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("guide"))
async def guide_command(message: types.Message, state: FSMContext):
    """Alias /guide → same as /learn"""
    await learn_command(message, state)


@router.callback_query(F.data == "learn_menu")
async def learn_menu(callback: types.CallbackQuery):
    """Back to learn menu with back to main"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    # Same improved menu for callbacks
    if lang == 'fr':
        title = (
            "📖 <b>GUIDE COMPLET RISK0</b>\n\n"
            "⏱️ <b>Temps de lecture: 5–10 minutes</b>\n"
            "💰 <b>Éviter des erreurs à $100-500+</b>\n\n"
            "Sélectionne une section:\n"
        )
        kb = [
            [InlineKeyboardButton(text="🚀 START HERE - Pourquoi lire ce guide?", callback_data="guide_start")],
            [InlineKeyboardButton(text="📖 Introduction - C'est quoi l'arbitrage?", callback_data="learn_intro")],
            [InlineKeyboardButton(text="🎯 Modes - SAFE vs RISKED expliqué", callback_data="learn_modes")],
            [InlineKeyboardButton(text="💰 CASHH - Budget et gestion", callback_data="learn_bankroll")],
            [InlineKeyboardButton(text="⚡ How to Place - Placer un arb", callback_data="learn_howto")],
            [InlineKeyboardButton(text="💎 Using I BET - Tracker vos profits", callback_data="learn_ibet")],
            [InlineKeyboardButton(text="⚠️ Mistakes - Erreurs qui coûtent cher", callback_data="learn_mistakes")],
            [InlineKeyboardButton(text="📱 Outils - Calculateur, Stats, Paramètres", callback_data="learn_tools")],
            [InlineKeyboardButton(text="🛡️ Avoid Bans - Rester sous le radar", callback_data="learn_avoid_bans")],
            [InlineKeyboardButton(text="🏦 Bookmakers - Setup & choix", callback_data="learn_books")],
            [InlineKeyboardButton(text="💎 Good Odds - Positive EV bets", callback_data="learn_good_odds")],
            [InlineKeyboardButton(text="🎯 Middle Bets - EV+ lottery", callback_data="learn_middle")],
            [InlineKeyboardButton(text="🎓 Pro Tips - Maximiser gains", callback_data="learn_advanced")],
            [InlineKeyboardButton(text="⚖️ Tax & Legal - Légalité et impôts", callback_data="learn_legal")],
            [InlineKeyboardButton(text="❓ FAQ - Questions fréquentes", callback_data="learn_faq")],
            [InlineKeyboardButton(text="📱 Menu Principal", callback_data="main_menu")],
        ]
    else:
        title = (
            "📖 <b>COMPLETE RISK0 GUIDE</b>\n\n"
            "⏱️ <b>Reading time: 5–10 minutes</b>\n"
            "💰 <b>Potential: Avoid $100-500+ mistakes</b>\n\n"
            "Select a section:\n"
        )
        kb = [
            [InlineKeyboardButton(text="🚀 START HERE - Why read this guide?", callback_data="guide_start")],
            [InlineKeyboardButton(text="📖 Introduction - What is arbitrage?", callback_data="learn_intro")],
            [InlineKeyboardButton(text="🎯 Modes - SAFE vs RISKED explained", callback_data="learn_modes")],
            [InlineKeyboardButton(text="💰 CASHH - Budget management", callback_data="learn_bankroll")],
            [InlineKeyboardButton(text="⚡ How to Place - Step by step", callback_data="learn_howto")],
            [InlineKeyboardButton(text="💎 Using I BET - Track your profits", callback_data="learn_ibet")],
            [InlineKeyboardButton(text="⚠️ Mistakes - Costly errors", callback_data="learn_mistakes")],
            [InlineKeyboardButton(text="📱 Tools - Calculator, Stats, Settings", callback_data="learn_tools")],
            [InlineKeyboardButton(text="🛡️ Avoid Bans - Stay under the radar", callback_data="learn_avoid_bans")],
            [InlineKeyboardButton(text="🏦 Bookmakers - Setup & choices", callback_data="learn_books")],
            [InlineKeyboardButton(text="💎 Good Odds - Positive EV bets", callback_data="learn_good_odds")],
            [InlineKeyboardButton(text="🎯 Middle Bets - EV+ lottery", callback_data="learn_middle")],
            [InlineKeyboardButton(text="🎓 Pro Tips - Maximize gains", callback_data="learn_advanced")],
            [InlineKeyboardButton(text="⚖️ Tax & Legal - Legality & taxes", callback_data="learn_legal")],
            [InlineKeyboardButton(text="❓ FAQ - Frequently Asked Questions", callback_data="learn_faq")],
            [InlineKeyboardButton(text="📱 Main Menu", callback_data="main_menu")],
        ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    await callback.answer()
    try:
        await callback.message.edit_text(
            title,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception:
        # Fallback: send new message via manager
        await BotMessageManager.send_or_edit(
            event=callback,
            text=title,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


# Import toutes les sections
from bot.learn_sections import *
