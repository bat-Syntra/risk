"""
Complete Risko Guide - 2-Tier System (FREE vs ALPHA)
Professional guide with conversion funnel and upsells
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from database import SessionLocal
from models.user import User, TierLevel

# Import pro tips sections
from bot.guide_pro_tips_complete import show_pro_tips_section1, show_pro_tips_section2_part1
from bot.guide_pro_tips_part2 import show_pro_tips_section2_part2a, show_pro_tips_section2_part2b, show_pro_tips_section3

# Import book health guide
from bot.guide_book_health import (
    show_book_health_intro,
    show_book_health_why,
    show_book_health_activation,
    show_book_health_score,
    show_book_health_tracking,
    show_book_health_tracking2,
    show_book_health_dashboard,
    show_book_health_faq
)

import logging
logger = logging.getLogger(__name__)

router = Router()

# Guide section access levels
GUIDE_SECTIONS = {
    # ✅ FREE FULL ACCESS
    'start_here': {'name': '🚀 START HERE - Why read this guide?', 'access': 'free', 'type': 'full'},
    'introduction': {'name': '📖 Introduction - What is RISKO?', 'access': 'free', 'type': 'full'},
    'modes': {'name': '🎯 Modes - SAFE vs RISKED explained', 'access': 'free', 'type': 'full'},
    'tax_legal': {'name': '⚖️ Tax & Legal - Legality & taxes', 'access': 'free', 'type': 'full'},
    'faq': {'name': '❓ FAQ - Frequently Asked Questions', 'access': 'free', 'type': 'full'},
    
    # ⚠️ PARTIAL ACCESS (Teasers)
    'cashh': {'name': '💰 CASHH - Budget management', 'access': 'teaser', 'type': 'partial', 'unlock_pct': 20},
    'how_to_place': {'name': '⚡ How to Place - Step by step', 'access': 'teaser', 'type': 'partial', 'unlock_pct': 40},
    'i_bet': {'name': '💎 Using I BET - Track profits', 'access': 'teaser', 'type': 'partial', 'unlock_pct': 30},
    'mistakes': {'name': '⚠️ Mistakes - Costly errors', 'access': 'teaser', 'type': 'partial', 'unlock_pct': 30},
    'avoid_bans': {'name': '🛡️ Avoid Bans - Stay under radar', 'access': 'teaser', 'type': 'partial', 'unlock_pct': 50},
    
    # 🔒 ALPHA EXCLUSIVE
    'tools': {'name': '🧮 Tools - Calculator, Stats, Settings 🔒', 'access': 'premium', 'type': 'locked'},
    'bookmakers': {'name': '🏢 Bookmakers - Setup & choices 🔒', 'access': 'premium', 'type': 'locked'},
    'good_odds': {'name': '💎 Good Odds - Positive EV bets 🔒', 'access': 'premium', 'type': 'locked'},
    'middle_bets': {'name': '🎯 Middle Bets - EV+ lottery 🔒', 'access': 'premium', 'type': 'locked'},
    'pro_tips': {'name': '🌟 Pro Tips - Maximize gains 🔒', 'access': 'premium', 'type': 'locked'},
    'settings': {'name': '⚙️ Settings Guide - Full control 🔒', 'access': 'premium', 'type': 'locked'},
    'last_call': {'name': '🔔 Last Call - Never miss profits 🔒', 'access': 'premium', 'type': 'locked'},
    
    # 🎲 PARLAY FEATURE (Beta - Accessible à tous)
    'parlays': {'name': '🎲 Parlays - Optimized combos 🆕', 'access': 'free', 'type': 'full'},
    
    # 🏥 BOOK HEALTH MONITOR (Beta - Accessible à tous)
    'book_health': {'name': '🏥 Book Health - Limit protection 🆕', 'access': 'free', 'type': 'full'},
    
    # 💰 SALES SECTIONS
    'success_stories': {'name': '🏆 Success Stories - Real results', 'access': 'free', 'type': 'sales'},
    'free_vs_premium': {'name': '⚖️ BETA vs ALPHA - Comparison', 'access': 'free', 'type': 'sales'},
    'upgrade': {'name': '💎 Upgrade to ALPHA', 'access': 'free', 'type': 'sales'},
}


@router.callback_query(F.data == "learn_guide_pro")
async def show_guide_menu(callback: types.CallbackQuery):
    """Show complete guide menu with tier-based access"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        is_premium = user and user.tier != TierLevel.FREE
        
        # Build header - Different for ALPHA vs FREE
        if is_premium:
            # ALPHA users - Simple header
            if lang == 'fr':
                text = (
                    f"📖 <b>GUIDE COMPLET RISKO</b>\n\n"
                    f"🔓 <b>ALPHA GUIDE - Tout Débloqué</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            else:
                text = (
                    f"📖 <b>COMPLETE RISKO GUIDE</b>\n\n"
                    f"🔓 <b>ALPHA GUIDE - Everything Unlocked</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
        else:
            # FREE users - Show upgrade potential
            if lang == 'fr':
                text = (
                    f"📖 <b>GUIDE COMPLET RISKO</b>\n\n"
                    f"⏱️ Temps de lecture: 5-10 minutes\n"
                    f"💰 Potentiel: Éviter $100-500+ d'erreurs\n\n"
                    f"💎 <b>Débloque tous les guides → Deviens membre ALPHA</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            else:
                text = (
                    f"📖 <b>COMPLETE RISKO GUIDE</b>\n\n"
                    f"⏱️ Reading time: 5-10 minutes\n"
                    f"💰 Potential: Avoid $100-500+ mistakes\n\n"
                    f"💎 <b>Unlock Complete Guides → Become ALPHA member</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
        
        # FREE FULL ACCESS sections (only show header for FREE users)
        if not is_premium:
            text += "✅ <b>FREE ACCESS</b>\n\n" if lang == 'en' else "✅ <b>ACCÈS GRATUIT</b>\n\n"
        
        keyboard = []
        
        # Add FREE full access buttons
        for section_id, section in GUIDE_SECTIONS.items():
            if section['access'] == 'free' and section['type'] == 'full':
                keyboard.append([InlineKeyboardButton(
                    text=section['name'],
                    callback_data=f"guide_view_{section_id}"
                )])
        
        # PARTIAL ACCESS sections (only show header for FREE users)
        if not is_premium:
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            if lang == 'fr':
                text += "⚠️ <b>ACCÈS PARTIEL (Upgrade pour tout)</b>\n\n"
            else:
                text += "⚠️ <b>PARTIAL ACCESS (Upgrade for full)</b>\n\n"
        
        for section_id, section in GUIDE_SECTIONS.items():
            if section['access'] == 'teaser':
                if is_premium:
                    # ALPHA users: show unlocked icon without percentage
                    btn_text = f"{section['name']} 🔓"
                else:
                    # FREE users: show percentage unlock
                    pct = section.get('unlock_pct', 0)
                    btn_text = f"{section['name']} 🔓 {pct}%"
                keyboard.append([InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"guide_view_{section_id}"
                )])
        
        # ALPHA EXCLUSIVE sections (only show header for FREE users)
        if not is_premium:
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            if lang == 'fr':
                text += "🔒 <b>EXCLUSIF ALPHA</b>\n\n"
            else:
                text += "🔒 <b>ALPHA EXCLUSIVE</b>\n\n"
        
        for section_id, section in GUIDE_SECTIONS.items():
            if section['access'] == 'premium':
                # Replace locked icon with unlocked for ALPHA users
                if is_premium:
                    # ALPHA users: replace 🔒 with 🔓
                    btn_text = section['name'].replace('🔒', '🔓')
                else:
                    # FREE users: keep 🔒
                    btn_text = section['name']
                
                # Good Odds & Middle: même si FREE, on ouvre une page explicative (teaser)
                if not is_premium and section_id in ('good_odds', 'middle_bets'):
                    cb = f"guide_view_{section_id}"
                else:
                    cb = f"guide_view_{section_id}" if is_premium else f"guide_locked_{section_id}"
                keyboard.append([InlineKeyboardButton(
                    text=btn_text,
                    callback_data=cb
                )])
        
        # Add sales sections ONLY for FREE users
        if not is_premium:
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for section_id, section in GUIDE_SECTIONS.items():
                if section['type'] == 'sales':
                    keyboard.append([InlineKeyboardButton(
                        text=section['name'],
                        callback_data=f"guide_view_{section_id}"
                    )])
        
        # Main menu button
        keyboard.append([InlineKeyboardButton(
            text="📱 Main Menu" if lang == 'en' else "📱 Menu Principal",
            callback_data="main_menu"
        )])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_guide_menu: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("guide_locked_"))
async def show_premium_lock(callback: types.CallbackQuery):
    """Show premium lock message when user tries to access locked content"""
    await callback.answer()
    
    section_id = callback.data.split('_')[2]
    section = GUIDE_SECTIONS.get(section_id, {})
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        if lang == 'fr':
            text = (
                f"🔒 <b>CONTENU PREMIUM VERROUILLÉ</b>\n\n"
                f"📖 Section: {section.get('name', 'Unknown')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💎 <b>CE QUI VOUS MANQUE</b>\n\n"
                f"Cette section contient:\n"
                f"• Guides détaillés étape par étape\n"
                f"• Exemples concrets avec chiffres\n"
                f"• Stratégies avancées\n"
                f"• Astuces exclusives\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 <b>COMPARAISON RAPIDE</b>\n\n"
                f"<b>GRATUIT:</b>\n"
                f"• 5 calls arbitrage/jour\n"
                f"• Maximum 2.5% de profit\n"
                f"• Pas de Middle ou Good Odds\n"
                f"• Guides basiques\n\n"
                f"<b>ALPHA:</b>\n"
                f"• Calls illimités\n"
                f"• Aucune limite de profit\n"
                f"• Accès complet Middle & Good Odds\n"
                f"• Tous les guides\n"
                f"• Calculateur avancé\n"
                f"• Statistiques complètes\n"
                f"• Settings avancés\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>RETOUR SUR INVESTISSEMENT</b>\n\n"
                f"Premium: $200/mois\n"
                f"Profit moyen: $3,000-5,000/mois\n"
                f"ROI: 15-25x 🚀\n\n"
                f"Rentabilise ton abonnement en 1-2 jours!"
            )
        else:
            text = (
                f"🔒 <b>ALPHA CONTENT LOCKED</b>\n\n"
                f"📖 Section: {section.get('name', 'Unknown')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💎 <b>WHAT YOU'RE MISSING</b>\n\n"
                f"This section contains:\n"
                f"• Detailed step-by-step guides\n"
                f"• Real examples with numbers\n"
                f"• Advanced strategies\n"
                f"• Exclusive tips\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 <b>QUICK COMPARISON</b>\n\n"
                f"<b>FREE:</b>\n"
                f"• 5 arbitrage calls/day\n"
                f"• Max 2.5% profit\n"
                f"• No Middle or Good Odds\n"
                f"• Basic guides\n\n"
                f"<b>ALPHA:</b>\n"
                f"• Unlimited calls\n"
                f"• No profit limit\n"
                f"• Full Middle & Good Odds access\n"
                f"• All guides unlocked\n"
                f"• Advanced calculator\n"
                f"• Complete statistics\n"
                f"• Advanced settings\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ROI ANALYSIS</b>\n\n"
                f"ALPHA: $200/month\n"
                f"Average profit: $3,000-5,000/month\n"
                f"ROI: 15-25x 🚀\n\n"
                f"Break even in 1-2 days!"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="🚀 Upgrade to ALPHA" if lang == 'en' else "🚀 Upgrade vers ALPHA",
                callback_data="upgrade_premium"
            )],
            [InlineKeyboardButton(
                text="◀️ Back to Guide" if lang == 'en' else "◀️ Retour au Guide",
                callback_data="learn_guide_pro"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_premium_lock: {e}")
    finally:
        db.close()


@router.callback_query(F.data == "upgrade_premium")
async def handle_upgrade_premium(callback: types.CallbackQuery):
    """Handle upgrade to premium button click - redirect to show_tiers"""
    # Import and call the show_tiers handler from handlers.py
    from bot.handlers import callback_show_tiers
    await callback_show_tiers(callback)


@router.callback_query(F.data.startswith("guide_view_"))
async def view_guide_section(callback: types.CallbackQuery):
    """View a guide section (access control applied)"""
    await callback.answer()
    
    # Extract section_id by removing "guide_view_" prefix
    section_id = callback.data.replace("guide_view_", "")
    
    # Import section content handler
    from bot.guide_content import get_section_content
    
    await get_section_content(callback, section_id)


@router.callback_query(F.data == "contact_support")
async def contact_support(callback: types.CallbackQuery):
    """Simple contact support message from guide CTA."""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        if lang == 'fr':
            text = (
                "🆘 <b>SUPPORT</b>\n\n"
                "📖 Nouveau? Lis le guide: /guide (10-15 min)\n\n"
                "👤 Contact: @ZEROR1SK\n"
                "🕒 Réponse: Rapide (même jour)\n\n"
                "Inclus: ton problème et screenshots si possible"
            )
        else:
            text = (
                "🆘 <b>SUPPORT</b>\n\n"
                "📖 New? Read the guide: /guide (10-15 min)\n\n"
                "👤 Contact: @ZEROR1SK\n"
                "🕒 Response: Fast (Same day)\n\n"
                "Include: your issue and screenshots if possible"
            )
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    finally:
        db.close()


# Pro Tips Navigation Handlers
@router.callback_query(F.data == "guide_pro_tips_1")
async def handle_pro_tips_1(callback: types.CallbackQuery):
    """Navigate to Pro Tips Section 1"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_pro_tips_section1(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_pro_tips_2")
async def handle_pro_tips_2(callback: types.CallbackQuery):
    """Navigate to Pro Tips Section 2 Part 1"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_pro_tips_section2_part1(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_pro_tips_2b")
async def handle_pro_tips_2b(callback: types.CallbackQuery):
    """Navigate to Pro Tips Section 2 Part 2a"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_pro_tips_section2_part2a(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_pro_tips_2c")
async def handle_pro_tips_2c(callback: types.CallbackQuery):
    """Navigate to Pro Tips Section 2 Part 2b"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_pro_tips_section2_part2b(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_pro_tips_3")
async def handle_pro_tips_3(callback: types.CallbackQuery):
    """Navigate to Pro Tips Section 3"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_pro_tips_section3(callback, lang)
    finally:
        db.close()


# Book Health Guide Navigation Handlers
@router.callback_query(F.data == "guide_book_health_intro")
async def handle_book_health_intro(callback: types.CallbackQuery):
    """Navigate to Book Health Introduction"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_intro(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_why")
async def handle_book_health_why(callback: types.CallbackQuery):
    """Navigate to Book Health Why"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_why(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_activation")
async def handle_book_health_activation(callback: types.CallbackQuery):
    """Navigate to Book Health Activation"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_activation(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_score")
async def handle_book_health_score(callback: types.CallbackQuery):
    """Navigate to Book Health Score"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_score(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_tracking")
async def handle_book_health_tracking(callback: types.CallbackQuery):
    """Navigate to Book Health Tracking"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_tracking(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_tracking2")
async def handle_book_health_tracking2(callback: types.CallbackQuery):
    """Navigate to Book Health Tracking Part 2"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_tracking2(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_dashboard")
async def handle_book_health_dashboard(callback: types.CallbackQuery):
    """Navigate to Book Health Dashboard"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        await show_book_health_dashboard(callback, lang)
    finally:
        db.close()


@router.callback_query(F.data == "guide_book_health_faq")
async def handle_book_health_faq(callback: types.CallbackQuery):
    """Navigate to Book Health FAQ"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        is_premium = user and user.tier != TierLevel.FREE
        await show_book_health_faq(callback, lang, is_premium)
    finally:
        db.close()


@router.callback_query(F.data == "book_health_start_check")
async def handle_book_health_start_check(callback: types.CallbackQuery, state: FSMContext):
    """Check tier before activating Book Health"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else 'en'
        is_premium = user and user.tier != TierLevel.FREE
        
        if not is_premium:
            # FREE user → Show lock message
            if lang == 'fr':
                text = (
                    "🔒 <b>BOOK HEALTH MONITOR - ALPHA EXCLUSIF</b>\n\n"
                    "Le système Book Health Monitor est réservé aux membres ALPHA.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💎 <b>AVEC ALPHA, TU OBTIENS:</b>\n\n"
                    "✅ Book Health Monitor complet\n"
                    "✅ Prédiction des limites de casino\n"
                    "✅ Dashboard avec score de risque\n"
                    "✅ Alertes automatiques\n"
                    "✅ Recommendations personnalisées\n"
                    "✅ Tracking ML de ton comportement\n\n"
                    "Plus TOUS les autres avantages ALPHA:\n"
                    "• Good Odds (+EV bets)\n"
                    "• Middle Bets (lottery)\n"
                    "• Parlays optimisés\n"
                    "• Guides complets\n"
                    "• Support prioritaire\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💰 <b>INVESTISSEMENT:</b>\n"
                    "$200 CAD/mois\n\n"
                    "🚀 <b>ROI:</b> 10-15x garanti!"
                )
            else:
                text = (
                    "🔒 <b>BOOK HEALTH MONITOR - ALPHA EXCLUSIVE</b>\n\n"
                    "The Book Health Monitor system is reserved for ALPHA members.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💎 <b>WITH ALPHA, YOU GET:</b>\n\n"
                    "✅ Complete Book Health Monitor\n"
                    "✅ Casino limit prediction\n"
                    "✅ Dashboard with risk score\n"
                    "✅ Automatic alerts\n"
                    "✅ Personalized recommendations\n"
                    "✅ ML tracking of your behavior\n\n"
                    "Plus ALL other ALPHA benefits:\n"
                    "• Good Odds (+EV bets)\n"
                    "• Middle Bets (lottery)\n"
                    "• Optimized Parlays\n"
                    "• Complete guides\n"
                    "• Priority support\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💰 <b>INVESTMENT:</b>\n"
                    "$200 CAD/month\n\n"
                    "🚀 <b>ROI:</b> 10-15x guaranteed!"
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💎 Devenir Membre ALPHA" if lang == 'fr' else "💎 Become ALPHA Member",
                    callback_data="guide_view_upgrade"
                )],
                [InlineKeyboardButton(
                    text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                    callback_data="guide_book_health_faq"
                )]
            ])
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            # ALPHA user → Start activation
            from bot.book_health_onboarding import start_onboarding
            await start_onboarding(callback, state)
    finally:
        db.close()
