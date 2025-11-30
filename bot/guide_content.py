"""
Guide Content - All sections with tier-based access
Complete content for FREE, TEASER, and PREMIUM sections
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User, TierLevel

# Import sales content
from bot.guide_content_sales import show_success_stories, show_free_vs_premium, show_upgrade

# Import new introduction
from bot.guide_introduction_new import show_introduction_new

# Import Parlays guide (Beta feature)
from bot.guide_parlays import show_parlays_guide

# Import Book Health guide (Beta feature)
from bot.guide_book_health import show_book_health_intro

# Import ALPHA EXCLUSIVE sections
try:
    from bot.guide_alpha_exclusive import show_tools_content, show_settings_content, show_last_call_content
except ImportError:
    show_tools_content = None
    show_settings_content = None
    show_last_call_content = None

# Import PRO TIPS sections
try:
    from bot.guide_pro_tips_complete import show_pro_tips_section1
except ImportError:
    show_pro_tips_section1 = None

import logging
logger = logging.getLogger(__name__)


async def show_premium_lock_message(callback: types.CallbackQuery, lang: str, section: str):
    """Show premium lock message for FREE users trying to access premium content"""
    if lang == 'fr':
        text = (
            f"🔒 <b>CONTENU PREMIUM VERROUILLÉ</b>\n\n"
            f"Cette section est exclusive aux membres Premium.\n\n"
            f"💎 <b>Upgrade pour débloquer:</b>\n"
            f"• Guide complet étape par étape\n"
            f"• Exemples réels avec chiffres\n"
            f"• Stratégies avancées\n"
            f"• Support prioritaire\n\n"
            f"Prix: $200 CAD/mois\n"
            f"ROI: 10-15x garanti! 🚀"
        )
    else:
        text = (
            f"🔒 <b>PREMIUM CONTENT LOCKED</b>\n\n"
            f"This section is exclusive to Premium members.\n\n"
            f"💎 <b>Upgrade to unlock:</b>\n"
            f"• Complete step-by-step guide\n"
            f"• Real examples with numbers\n"
            f"• Advanced strategies\n"
            f"• Priority support\n\n"
            f"Price: $200 CAD/month\n"
            f"ROI: 10-15x guaranteed! 🚀"
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
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


async def get_section_content(callback: types.CallbackQuery, section_id: str):
    """Get and display section content based on user tier"""
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        is_premium = user and user.tier != TierLevel.FREE
        
        # Route to appropriate section handler
        if section_id == 'start_here':
            await show_start_here(callback, lang)
        elif section_id == 'introduction':
            await show_introduction_new(callback, lang)
        elif section_id == 'modes':
            await show_modes(callback, lang, is_premium)
        elif section_id == 'tax_legal':
            await show_tax_legal(callback, lang)
        elif section_id == 'faq':
            await show_faq(callback, lang, is_premium)
        elif section_id == 'cashh':
            await show_cashh(callback, lang, is_premium)
        elif section_id == 'how_to_place':
            await show_how_to_place(callback, lang, is_premium)
        elif section_id == 'i_bet':
            await show_i_bet(callback, lang, is_premium)
        elif section_id == 'mistakes':
            await show_mistakes(callback, lang, is_premium)
        elif section_id == 'avoid_bans':
            await show_avoid_bans(callback, lang, is_premium)
        elif section_id == 'tools':
            if not is_premium:
                await show_premium_lock_message(callback, lang, 'tools')
            else:
                # Use new detailed ALPHA EXCLUSIVE content
                if show_tools_content:
                    await show_tools_content(callback, lang)
                else:
                    await show_tools(callback, lang)
        elif section_id == 'bookmakers':
            if not is_premium:
                await show_premium_lock_message(callback, lang, 'bookmakers')  
            else:
                await show_bookmakers(callback, lang)
        elif section_id == 'good_odds':
            # FREE users voient l'explication, PREMIUM l'utilise en plus
            await show_good_odds(callback, lang, is_premium)
        elif section_id == 'middle_bets':
            # FREE users voient l'explication, PREMIUM l'utilise en plus
            await show_middle_bets(callback, lang, is_premium)
        elif section_id == 'pro_tips':
            if not is_premium:
                await show_premium_lock_message(callback, lang, 'pro_tips')
            else:
                # Use new MASSIVE pro tips section 1 (3-part guide)
                if show_pro_tips_section1:
                    await show_pro_tips_section1(callback, lang)
                else:
                    await show_pro_tips(callback, lang)
        elif section_id == 'settings':
            if not is_premium:
                await show_premium_lock_message(callback, lang, 'settings')
            else:
                # Use new detailed ALPHA EXCLUSIVE content
                if show_settings_content:
                    await show_settings_content(callback, lang)
                else:
                    await show_settings(callback, lang)
        elif section_id == 'last_call':
            if not is_premium:
                await show_premium_lock_message(callback, lang, 'last_call')
            else:
                # Use new detailed ALPHA EXCLUSIVE content
                if show_last_call_content:
                    await show_last_call_content(callback, lang)
                else:
                    await show_last_call(callback, lang)
        elif section_id == 'parlays':
            # Parlays guide accessible à tous (BETA et ALPHA)
            await show_parlays_guide(callback, lang)
        elif section_id == 'book_health':
            # Book Health guide accessible à tous (BETA et ALPHA)
            await show_book_health_intro(callback, lang)
        elif section_id == 'success_stories':
            # ALPHA users should not see marketing content
            if is_premium:
                await callback.answer("✅ You're already ALPHA! Skip to CASHH guide.", show_alert=True)
                await show_cashh(callback, lang, is_premium)
            else:
                await show_success_stories(callback, lang)
        elif section_id == 'free_vs_premium':
            # ALPHA users should not see FREE vs ALPHA comparison
            if is_premium:
                await callback.answer("✅ You're already ALPHA!", show_alert=True)
                return
            else:
                await show_free_vs_premium(callback, lang)
        elif section_id == 'upgrade':
            # ALPHA users don't need upgrade page
            if is_premium:
                await callback.answer("✅ You're already ALPHA!", show_alert=True)
                return
            else:
                await show_upgrade(callback, lang)
        else:
            await callback.answer("Section not available", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in get_section_content: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


# ============================================================================
# FREE FULL ACCESS SECTIONS
# ============================================================================

async def show_start_here(callback: types.CallbackQuery, lang: str):
    """🚀 START HERE - Why read this guide? (FREE)"""
    
    if lang == 'fr':
        text = (
            "🚀 <b>COMMENCER ICI - Pourquoi lire ce guide?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>CE GUIDE PEUT VOUS SAUVER $500+ D'ERREURS</b>\n\n"
            "Arbitrage semble simple:\n"
            "1. Trouve 2 cotes opposées\n"
            "2. Parie sur les deux\n"
            "3. Profit garanti\n\n"
            "Mais la réalité est plus complexe...\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>ERREURS COURANTES (coûteuses!)</b>\n\n"
            "❌ Mauvaise gestion du CASHH\n"
            "→ Fonds bloqués, opportunités manquées\n\n"
            "❌ Mauvaise façon de placer les paris\n"
            "→ Erreurs de calcul, pertes évitables\n\n"
            "❌ Ne pas tracker avec I BET\n"
            "→ Impossible de savoir si profitable\n\n"
            "❌ Se faire limiter trop vite\n"
            "→ Game over après 2 semaines\n\n"
            "❌ Utiliser le mauvais mode (SAFE vs RISKED)\n"
            "→ Soit trop conservateur, soit trop risqué\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>CE QUE CE GUIDE VA FAIRE</b>\n\n"
            "1. <b>Éviter les erreurs coûteuses</b>\n"
            "   → Apprends des erreurs des autres\n\n"
            "2. <b>Maximiser tes profits</b>\n"
            "   → Stratégies qui fonctionnent vraiment\n\n"
            "3. <b>Jouer le long jeu</b>\n"
            "   → $1k/mois × 2 ans > $5k × 2 mois\n\n"
            "4. <b>Rester sous le radar</b>\n"
            "   → Éviter les limitations rapides\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>TEMPS REQUIS</b>\n\n"
            "• Lecture complète: 30-45 minutes\n"
            "• Retour sur investissement: INFINI\n\n"
            "💡 Prends 45 minutes maintenant,\n"
            "économise des centaines d'heures de frustration!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>COMMENCE PAR QUOI?</b>\n\n"
            "Si tu es:\n\n"
            "🆕 <b>Débutant total</b>\n"
            "→ Lis dans l'ordre (Introduction → Modes → etc.)\n\n"
            "📚 <b>Tu connais l'arbitrage</b>\n"
            "→ Saute à CASHH, How to Place, Avoid Bans\n\n"
            "💎 <b>Premium et sérieux</b>\n"
            "→ Focus sur Tools, Pro Tips, Settings\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🚀 <b>START HERE - Why read this guide?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>THIS GUIDE CAN SAVE YOU $500+ IN MISTAKES</b>\n\n"
            "Arbitrage seems simple:\n"
            "1. Find 2 opposite odds\n"
            "2. Bet on both\n"
            "3. Guaranteed profit\n\n"
            "But reality is more complex...\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>COMMON MISTAKES (costly!)</b>\n\n"
            "❌ Poor CASHH management\n"
            "→ Funds locked, missed opportunities\n\n"
            "❌ Wrong way to place bets\n"
            "→ Calculation errors, avoidable losses\n\n"
            "❌ Not tracking with I BET\n"
            "→ Impossible to know if profitable\n\n"
            "❌ Getting limited too fast\n"
            "→ Game over after 2 weeks\n\n"
            "❌ Using wrong mode (SAFE vs RISKED)\n"
            "→ Either too conservative or too risky\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>WHAT THIS GUIDE WILL DO</b>\n\n"
            "1. <b>Avoid costly mistakes</b>\n"
            "   → Learn from others' errors\n\n"
            "2. <b>Maximize your profits</b>\n"
            "   → Strategies that actually work\n\n"
            "3. <b>Play the long game</b>\n"
            "   → $1k/month × 2 years > $5k × 2 months\n\n"
            "4. <b>Stay under the radar</b>\n"
            "   → Avoid quick limitations\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>TIME REQUIRED</b>\n\n"
            "• Full read: 30-45 minutes\n"
            "• ROI: INFINITE\n\n"
            "💡 Spend 45 minutes now,\n"
            "save hundreds of hours of frustration!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHERE TO START?</b>\n\n"
            "If you're:\n\n"
            "🆕 <b>Total beginner</b>\n"
            "→ Read in order (Introduction → Modes → etc.)\n\n"
            "📚 <b>You know arbitrage</b>\n"
            "→ Jump to CASHH, How to Place, Avoid Bans\n\n"
            "💎 <b>Premium and serious</b>\n"
            "→ Focus on Tools, Pro Tips, Settings\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="📖 Next: Introduction" if lang == 'en' else "📖 Suivant: Introduction",
            callback_data="guide_view_introduction"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_introduction(callback: types.CallbackQuery, lang: str):
    """📖 Introduction - What is arbitrage? (FREE)"""
    
    if lang == 'fr':
        text = (
            "📖 <b>INTRODUCTION - Qu'est-ce que l'arbitrage?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>DÉFINITION SIMPLE</b>\n\n"
            "L'arbitrage sportif = parier sur TOUS les résultats possibles\n"
            "d'un événement pour un profit garanti.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>EXEMPLE CONCRET</b>\n\n"
            "Match: Real Madrid vs Barcelona\n\n"
            "<b>Bookmaker A (Betsson):</b>\n"
            "Real Madrid: 2.10 cote\n\n"
            "<b>Bookmaker B (bet365):</b>\n"
            "Barcelona: 2.15 cote\n\n"
            "💰 <b>TON CASHH: $500</b>\n\n"
            "Stakes calculés:\n"
            "• Betsson (Real): $254.80\n"
            "• bet365 (Barca): $245.20\n"
            "• Total investi: $500\n\n"
            "<b>Résultat si Real gagne:</b>\n"
            "→ Betsson paie: $254.80 × 2.10 = $535.08\n"
            "→ Profit: $535.08 - $500 = <b>$35.08</b>\n\n"
            "<b>Résultat si Barca gagne:</b>\n"
            "→ bet365 paie: $245.20 × 2.15 = $527.18\n"
            "→ Profit: $527.18 - $500 = <b>$27.18</b>\n\n"
            "💎 Dans les deux cas: <b>PROFIT GARANTI!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>POURQUOI ÇA EXISTE?</b>\n\n"
            "Les bookmakers:\n"
            "• Ont des opinions différentes\n"
            "• Ajustent les cotes à différents rythmes\n"
            "• Ciblent différents marchés\n"
            "• Font des erreurs\n\n"
            "Résultat: Des opportunités d'arbitrage constantes!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>PROFITS RÉALISTES</b>\n\n"
            "ROI moyen par arbitrage: <b>2-8%</b>\n\n"
            "Avec $1,000 CASHH:\n"
            "• 1 arb/jour @ 4%: $40/jour → $1,200/mois\n"
            "• 3 arbs/jour @ 4%: $120/jour → $3,600/mois\n\n"
            "Avec $5,000 CASHH:\n"
            "• 3 arbs/jour @ 4%: $600/jour → $18,000/mois\n\n"
            "💎 Premium users: 10-20 arbs/jour possibles!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>AVANTAGES</b>\n\n"
            "• Profit mathématiquement garanti\n"
            "• Pas besoin de connaître le sport\n"
            "• Fonctionne 24/7\n"
            "• Scalable (plus de CASHH = plus de profit)\n\n"
            "⚠️ <b>INCONVÉNIENTS</b>\n\n"
            "• Bookmakers limitent les gagnants\n"
            "• Requiert un capital de départ\n"
            "• Demande du temps et de la discipline\n"
            "• Les cotes bougent vite\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚨 <b>AVERTISSEMENT - UTILISATEURS GRATUITS</b>\n\n"
            "Tier GRATUIT:\n"
            "• <b>5 calls arbitrage par jour maximum</b>\n"
            "• <b>Profit maximum 2.5% par call</b>\n"
            "• <b>Pas d'accès Middle Bets</b>\n"
            "• <b>Pas d'accès Good Odds (+EV)</b>\n\n"
            "→ Suffisant pour apprendre et valider le concept\n"
            "→ Profit mensuel: $300-600\n\n"
            "💎 Premium = calls illimités + tous types de bets\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "📖 <b>INTRODUCTION - What is arbitrage?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>SIMPLE DEFINITION</b>\n\n"
            "Sports arbitrage = betting on ALL possible outcomes\n"
            "of an event for guaranteed profit.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>CONCRETE EXAMPLE</b>\n\n"
            "Match: Real Madrid vs Barcelona\n\n"
            "<b>Bookmaker A (Betsson):</b>\n"
            "Real Madrid: 2.10 odds\n\n"
            "<b>Bookmaker B (bet365):</b>\n"
            "Barcelona: 2.15 odds\n\n"
            "💰 <b>YOUR CASHH: $500</b>\n\n"
            "Calculated stakes:\n"
            "• Betsson (Real): $254.80\n"
            "• bet365 (Barca): $245.20\n"
            "• Total invested: $500\n\n"
            "<b>If Real wins:</b>\n"
            "→ Betsson pays: $254.80 × 2.10 = $535.08\n"
            "→ Profit: $535.08 - $500 = <b>$35.08</b>\n\n"
            "<b>If Barca wins:</b>\n"
            "→ bet365 pays: $245.20 × 2.15 = $527.18\n"
            "→ Profit: $527.18 - $500 = <b>$27.18</b>\n\n"
            "💎 Either way: <b>GUARANTEED PROFIT!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>WHY DOES IT EXIST?</b>\n\n"
            "Bookmakers:\n"
            "• Have different opinions\n"
            "• Adjust odds at different speeds\n"
            "• Target different markets\n"
            "• Make mistakes\n\n"
            "Result: Constant arbitrage opportunities!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>REALISTIC PROFITS</b>\n\n"
            "Average ROI per arb: <b>2-8%</b>\n\n"
            "With $1,000 CASHH:\n"
            "• 1 arb/day @ 4%: $40/day → $1,200/month\n"
            "• 3 arbs/day @ 4%: $120/day → $3,600/month\n\n"
            "With $5,000 CASHH:\n"
            "• 3 arbs/day @ 4%: $600/day → $18,000/month\n\n"
            "💎 Premium users: 10-20 arbs/day possible!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>ADVANTAGES</b>\n\n"
            "• Mathematically guaranteed profit\n"
            "• No need to know the sport\n"
            "• Works 24/7\n"
            "• Scalable (more CASHH = more profit)\n\n"
            "⚠️ <b>DISADVANTAGES</b>\n\n"
            "• Bookmakers limit winners\n"
            "• Requires starting capital\n"
            "• Demands time and discipline\n"
            "• Odds move fast\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚨 <b>WARNING - FREE USERS</b>\n\n"
            "FREE Tier:\n"
            "• <b>5 arbitrage calls per day maximum</b>\n"
            "• <b>Max 2.5% profit per call</b>\n"
            "• <b>No Middle Bets access</b>\n"
            "• <b>No Good Odds (+EV) access</b>\n\n"
            "→ Enough to learn and validate concept\n"
            "→ Monthly profit: $300-600\n\n"
            "💎 Premium = unlimited calls + all bet types\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="🎯 Next: Modes (SAFE vs RISKED)" if lang == 'en' else "🎯 Suivant: Modes (SAFE vs RISKED)",
            callback_data="guide_view_modes"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


# Stub functions for missing sections (to prevent errors)

async def show_modes(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """🎯 Modes - SAFE vs RISKED (FREE overview, works for all tiers)"""
    if lang == 'fr':
        text = (
            "🎯 <b>MODES - SAFE vs RISKED</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>MODE SAFE (Arbitrage pur)</b>\n\n"
            "• Tu paries sur <b>TOUS</b> les côtés\n"
            "• Profit garanti si bien exécuté\n"
            "• 0% risque mathématique\n"
            "• C'est le mode utilisé pour les calls FREE\n\n"
            "🔥 <b>MODE RISKED (Alpha)</b>\n\n"
            "• Tu bet via <b>2 casinos différents</b>\n"
            "• Au lieu d'un arbitrage, tu fais un bet\n"
            "• Tu risques un peu plus MAIS profit beaucoup plus\n"
            "• Utilise différences de cotes en live\n"
            "• Profits 2-3x plus élevés que SAFE\n\n"
            "Exemple RISKED:\n"
            "• Casino A: Lakers +5.5 @ -110 (live)\n"
            "• Casino B: Lakers +4.5 @ +105 (pre-game)\n"
            "→ Tu bet Lakers +5.5 pour profit maximum\n"
            "→ Risque: 1 seul côté (pas arbitrage)\n"
            "→ Reward: Profit 2-3x plus haut\n\n"
        )
        if not is_premium:
            text += (
                "En FREE tu utilises uniquement le mode SAFE.\n"
                "En ALPHA tu débloques le mode RISKED + Good Odds.\n\n"
            )
    else:
        text = (
            "🎯 <b>MODES - SAFE vs RISKED</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>SAFE MODE (Pure arbitrage)</b>\n\n"
            "• You bet on <b>ALL</b> sides\n"
            "• Guaranteed profit if executed correctly\n"
            "• 0% mathematical risk\n"
            "• This is the mode used for FREE calls\n\n"
            "🔥 <b>RISKED MODE (Alpha)</b>\n\n"
            "• You bet via <b>2 different casinos</b>\n"
            "• Instead of arbitrage, you make a bet\n"
            "• You risk a bit more BUT profit much more\n"
            "• Uses live odds differences\n"
            "• Profits 2-3x higher than SAFE\n\n"
            "RISKED example:\n"
            "• Casino A: Lakers +5.5 @ -110 (live)\n"
            "• Casino B: Lakers +4.5 @ +105 (pre-game)\n"
            "→ You bet Lakers +5.5 for max profit\n"
            "→ Risk: One side only (not arbitrage)\n"
            "→ Reward: Profit 2-3x higher\n\n"
        )
        if not is_premium:
            text += (
                "On FREE you only use SAFE mode.\n"
                "On ALPHA you unlock RISKED mode + Good Odds.\n\n"
            )

    next_label = "⚖️ Next: Tax & Legal" if lang == 'en' else "⚖️ Suivant: Tax & Legal"
    keyboard = [
        [InlineKeyboardButton(text=next_label, callback_data="guide_view_tax_legal")],
        [InlineKeyboardButton(text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu", callback_data="learn_guide_pro")],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

async def show_tax_legal(callback: types.CallbackQuery, lang: str):
    """⚖️ Tax & Legal (FREE)"""
    
    if lang == 'fr':
        text = (
            "⚖️ <b>TAX & LEGAL - Impôts et Légalité</b>\n\n"
            "⚠️ <b>DISCLAIMER:</b> Ceci n'est PAS un conseil juridique ou fiscal. Consulte un professionnel.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇨🇦 <b>CANADA (Québec & autres provinces)</b>\n\n"
            "✅ <b>Légalité:</b>\n"
            "• Paris sportifs en ligne LÉGAUX au Canada\n"
            "• Arbitrage est LÉGAL (aucune loi l'interdisant)\n"
            "• Bookmakers offshore acceptent Canadiens\n\n"
            "💰 <b>Impôts:</b>\n"
            "• Gains de paris = NON IMPOSABLES au Canada!\n"
            "• Considérés comme \"windfall\" (aubaine)\n"
            "• Pas besoin de déclarer si paris récréatifs\n"
            "• Si activité professionnelle = pourrait être imposable\n\n"
            "💡 Recommandation:\n"
            "• Moins de $30k/an: Aucun souci\n"
            "• Plus de $30k/an: Consulte un comptable\n"
            "• Garde registre de tes paris (au cas où)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇺🇸 <b>USA (états varies)</b>\n\n"
            "⚠️ Dépend de l'état:\n"
            "• Certains états = paris légaux\n"
            "• Arbitrage souvent dans zone grise\n"
            "• Gains TOUJOURS imposables (IRS)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇫🇷 <b>FRANCE</b>\n\n"
            "⚠️ Réglementé:\n"
            "• Seuls bookmakers ARJEL autorisés\n"
            "• Gains NON imposables si paris récréatifs\n"
            "• Imposable si activité professionnelle\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛡️ <b>CONSEILS GÉNÉRAUX</b>\n\n"
            "1. Garde registre de tous tes paris\n"
            "2. Screenshots des tickets gagnants\n"
            "3. Si >$30k/an, consulte comptable\n"
            "4. Utilise bookmakers réputés\n"
            "5. Ne parie que ce que tu peux te permettre"
        )
    else:
        text = (
            "⚖️ <b>TAX & LEGAL - Taxes and Legality</b>\n\n"
            "⚠️ <b>DISCLAIMER:</b> This is NOT legal or tax advice. Consult a professional.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇨🇦 <b>CANADA (Quebec & other provinces)</b>\n\n"
            "✅ <b>Legality:</b>\n"
            "• Online sports betting LEGAL in Canada\n"
            "• Arbitrage is LEGAL (no law against it)\n"
            "• Offshore bookmakers accept Canadians\n\n"
            "💰 <b>Taxes:</b>\n"
            "• Betting winnings = TAX-FREE in Canada!\n"
            "• Considered as \"windfall\"\n"
            "• No need to declare if recreational\n"
            "• If professional activity = could be taxable\n\n"
            "💡 Recommendation:\n"
            "• Under $30k/year: No worries\n"
            "• Over $30k/year: Consult accountant\n"
            "• Keep record of bets (just in case)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇺🇸 <b>USA (varies by state)</b>\n\n"
            "⚠️ Depends on state:\n"
            "• Some states = betting legal\n"
            "• Arbitrage often gray area\n"
            "• Winnings ALWAYS taxable (IRS)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🇫🇷 <b>FRANCE</b>\n\n"
            "⚠️ Regulated:\n"
            "• Only ARJEL bookmakers authorized\n"
            "• Winnings TAX-FREE if recreational\n"
            "• Taxable if professional activity\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛡️ <b>GENERAL TIPS</b>\n\n"
            "1. Keep record of all bets\n"
            "2. Screenshots of winning tickets\n"
            "3. If >$30k/year, consult accountant\n"
            "4. Use reputable bookmakers\n"
            "5. Only bet what you can afford"
        )
    
    next_label = "❓ Next: FAQ" if lang == 'en' else "❓ Suivant: FAQ"
    keyboard = [
        [InlineKeyboardButton(text=next_label, callback_data="guide_view_faq")],
        [InlineKeyboardButton(text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu", callback_data="learn_guide_pro")],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

async def show_faq(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """❓ FAQ (FREE, but useful for everyone)"""
    
    if lang == 'fr':
        text = (
            "❓ <b>FAQ - Questions Fréquentes</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Est-ce légal?</b>\n"
            "✅ Arbitrage = utiliser les cotes offertes par les bookmakers.\n"
            "✅ Aucune loi au Canada qui l'interdit.\n"
            "⚠️ Toujours vérifier ta juridiction locale.\n\n"
            "<b>2. Combien je peux faire?</b>\n"
            "• FREE: 5 calls/jour, petits profits, parfait pour tester.\n"
            "• PREMIUM: appels illimités + Good Odds + Middle.\n"
            "• Objectif réaliste: $1k-3k/mois si sérieux.\n\n"
            "<b>3. Est-ce risqué?</b>\n"
            "• Arbitrage SAFE: risque très faible si bien exécuté.\n"
            "• Good Odds / Middle: variance plus élevée (long terme).\n"
            "• Toujours parier des montants que tu peux te permettre.\n\n"
            "<b>4. Différence FREE vs PREMIUM?</b>\n"
            "• FREE = Découverte, 5 calls/jour, pas de Good Odds/Middle.\n"
            "• PREMIUM = Tous les outils, tous les types de bets, stats complètes.\n\n"
            "<b>5. Dois-je laisser le bot placer les bets?</b>\n"
            "Non. Tu gardes le contrôle. Le bot montre les opportunités,\n"
            "TU décides quoi placer, quand et combien.\n\n"
            "<b>6. De quoi j'ai besoin pour commencer?</b>\n"
            "• 2-3 bookmakers actifs\n"
            "• Une bankroll claire (CASHH)\n"
            "• 20-30 minutes/jour\n\n"
        )
    else:
        text = (
            "❓ <b>FAQ - Frequently Asked Questions</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Is this legal?</b>\n"
            "✅ Arbitrage = using odds offered by bookmakers.\n"
            "✅ No law in Canada specifically banning it.\n"
            "⚠️ Always check your local laws.\n\n"
            "<b>2. How much can I make?</b>\n"
            "• FREE: 5 calls/day, small but real profits, good to test.\n"
            "• PREMIUM: unlimited calls + Good Odds + Middles.\n"
            "• Realistic goal: $1k-3k/month if serious.\n\n"
            "<b>3. Is it risky?</b>\n"
            "• SAFE arbitrage: very low risk if done correctly.\n"
            "• Good Odds / Middles: higher variance (long term game).\n"
            "• Always bet what you can afford to lose.\n\n"
            "<b>4. FREE vs PREMIUM?</b>\n"
            "• FREE = Discovery, 5 calls/day, no Good Odds/Middles.\n"
            "• PREMIUM = All tools, all bet types, full stats.\n\n"
            "<b>5. Does the bot place bets for me?</b>\n"
            "No. You stay in control. The bot shows opportunities,\n"
            "YOU decide what to place, when and how much.\n\n"
            "<b>6. What do I need to start?</b>\n"
            "• 2-3 active bookmakers\n"
            "• A clear bankroll (CASHH)\n"
            "• 20-30 minutes per day\n\n"
        )
    
    keyboard_rows = []
    # All users go to Parlays next
    next_label = "🎲 Suivant: Parlays" if lang == 'fr' else "🎲 Next: Parlays"
    keyboard_rows.append([InlineKeyboardButton(text=next_label, callback_data="guide_view_parlays")])
    keyboard_rows.append([InlineKeyboardButton(text="◀️ Retour au Menu" if lang == 'fr' else "◀️ Back to Guide Menu", callback_data="learn_guide_pro")])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_cashh(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """💰 CASHH - Bankroll management (Teaser for FREE, full for PREMIUM)"""
    
    if lang == 'fr':
        if is_premium:
            text = (
                "💰 <b>CASHH - Gestion de Bankroll (COMPLET)</b>\n\n"
                "CASHH = montant total que tu utilises pour arbitrage.\n\n"
                "<b>1. Règle de base:</b>\n"
                "• Ne mets pas 100% de ton argent dans 1 bookmaker.\n"
                "• Répartis sur 3-5 books pour avoir plus d'opportunités.\n\n"
                "<b>2. Allocation recommandée:</b>\n"
                "• 40-50% sur les books qui offrent le plus de value.\n"
                "• 20-30% sur 2-3 books secondaires.\n"
                "• 10% en réserve (cash libre).\n\n"
                "<b>3. Avec le bot Risk0:</b>\n"
                "• Mets ton CASHH dans Settings.\n"
                "• Le calculateur ajuste les stakes pour chaque call.\n"
                "• Utilise I BET pour suivre ton profit réel.\n\n"
                "<b>4. Quand augmenter ton CASHH?</b>\n"
                "• Quand tu as 20-30 bets gagnés sans tilt.\n"
                "• Quand tu es à l'aise avec le processus complet.\n\n"
                "<b>5. Erreurs à éviter:</b>\n"
                "• Tout mettre sur 1 match.\n"
                "• Doubler après une perte (tilt).\n"
                "• Retirer trop vite les gains (tu casses la croissance).\n\n"
            )
        else:
            text = (
                "💰 <b>CASHH - Gestion de Bankroll</b>\n\n"
                "🔓 <b>20% DÉBLOQUÉ POUR FREE</b>\n\n"
                "CASHH = l'argent que tu décides de consacrer à l'arbitrage.\n\n"
                "Ce que tu dois retenir:\n"
                "• Commence petit (ex: $500-1,000).\n"
                "• Répartis sur plusieurs books.\n"
                "• Ne parie jamais l'argent du loyer.\n\n"
                "La version PREMIUM te montre:\n"
                "• Le plan complet d'allocation par bookmaker.\n"
                "• Comment augmenter ton CASHH étape par étape.\n"
                "• Comment éviter les erreurs de bankroll.\n\n"
            )
    else:
        if is_premium:
            text = (
                "💰 <b>CASHH - Bankroll Management (FULL)</b>\n\n"
                "CASHH = total amount you use for arbitrage.\n\n"
                "<b>1. Core rule:</b>\n"
                "• Do NOT park 100% on a single book.\n"
                "• Spread across 3-5 books for more opportunities.\n\n"
                "<b>2. Suggested allocation:</b>\n"
                "• 40-50% on your main value books.\n"
                "• 20-30% on 2-3 secondary books.\n"
                "• 10% as free cash buffer.\n\n"
                "<b>3. With the Risk0 bot:</b>\n"
                "• Set your CASHH in Settings.\n"
                "• Calculator adjusts stakes for every call.\n"
                "• Use I BET to track real profit.\n\n"
                "<b>4. When to increase CASHH?</b>\n"
                "• After 20-30 bets without tilting.\n"
                "• When you're fully comfortable with the process.\n\n"
                "<b>5. Mistakes to avoid:</b>\n"
                "• All-in on one match.\n"
                "• Chasing losses.\n"
                "• Withdrawing too fast and killing growth.\n\n"
            )
        else:
            text = (
                "💰 <b>CASHH - Bankroll Management</b>\n\n"
                "🔓 <b>20% UNLOCKED FOR FREE</b>\n\n"
                "CASHH = money you dedicate to arbitrage.\n\n"
                "Key ideas:\n"
                "• Start small (e.g. $500-1,000).\n"
                "• Spread across multiple books.\n"
                "• Never bet rent money.\n\n"
                "The PREMIUM version shows you:\n"
                "• Full allocation plan per bookmaker.\n"
                "• How to scale your CASHH step by step.\n"
                "• How to avoid bankroll management mistakes.\n\n"
            )
    
    keyboard_rows = []
    next_label = "⚡ Next: How to Place" if lang == 'en' else "⚡ Suivant: Comment Placer"
    keyboard_rows.append([InlineKeyboardButton(
        text=next_label,
        callback_data="guide_view_how_to_place"
    )])
    if not is_premium:
        keyboard_rows.append([InlineKeyboardButton(
            text="🚀 Upgrade to ALPHA" if lang == 'en' else "🚀 Upgrade vers ALPHA",
            callback_data="upgrade_premium"
        )])
    keyboard_rows.append([InlineKeyboardButton(
        text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
        callback_data="learn_guide_pro"
    )])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_how_to_place(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """⚡ How to Place - Using bot calls correctly"""
    
    if lang == 'fr':
        if is_premium:
            text = (
                "⚡ <b>COMMENT PLACER UN CALL (COMPLET)</b>\n\n"
                "1️⃣ Ouvre le call dans Telegram\n"
                "• Lis le % d'arbitrage ou l'EV\n"
                "• Vérifie les casinos concernés\n\n"
                "2️⃣ Clique sur les liens casinos\n"
                "• Ouvre chaque bookmaker\n"
                "• Va sur le bon match / marché\n\n"
                "3️⃣ Utilise le CALCULATEUR\n"
                "• Clique 🧮 Calculator dans le call\n"
                "• Vérifie les stakes proposés\n\n"
                "4️⃣ Place les paris EXACTEMENT comme indiqué\n"
                "• Même cote ou meilleure\n"
                "• Même mise (ou très proche)\n\n"
                "5️⃣ Marque ""I BET"" après avoir parié\n"
                "• Le bot enregistre le bet\n"
                "• Tes stats seront exactes\n\n"
                "6️⃣ Toujours vérifier les cotes AVANT d'accepter\n"
                "• Si la cote a trop bougé, SKIP le call.\n\n"
            )
        else:
            text = (
                "⚡ <b>COMMENT PLACER UN CALL</b>\n\n"
                "🔓 <b>40% DÉBLOQUÉ POUR FREE</b>\n\n"
                "Aperçu rapide des étapes:\n"
                "1️⃣ Ouvrir le call dans Telegram\n"
                "2️⃣ Ouvrir les bookmakers indiqués\n"
                "3️⃣ Vérifier le match / marché\n"
                "4️⃣ Placer les paris comme indiqué\n\n"
                "En PREMIUM, tu verras:\n"
                "• Le guide complet étape par étape (avec screenshots).\n"
                "• Comment utiliser le calculateur et I BET ensemble.\n"
                "• Comment réagir si les cotes bougent.\n\n"
            )
    else:
        if is_premium:
            text = (
                "⚡ <b>HOW TO PLACE A CALL (FULL)</b>\n\n"
                "1️⃣ Open the call in Telegram\n"
                "• Read arb% or EV%\n"
                "• Check which casinos are used\n\n"
                "2️⃣ Tap casino links\n"
                "• Open each bookmaker\n"
                "• Go to the correct match/market\n\n"
                "3️⃣ Use the CALCULATOR\n"
                "• Tap 🧮 Calculator in the call\n"
                "• Check suggested stakes\n\n"
                "4️⃣ Place bets EXACTLY as shown\n"
                "• Same or better odds\n"
                "• Same stake sizes (or very close)\n\n"
                "5️⃣ Hit ""I BET"" after placing\n"
                "• Bot records the bet\n"
                "• Stats stay accurate\n\n"
                "6️⃣ Always re-check odds BEFORE confirming\n"
                "• If odds moved too much, SKIP the call.\n\n"
            )
        else:
            text = (
                "⚡ <b>HOW TO PLACE A CALL</b>\n\n"
                "🔓 <b>40% UNLOCKED FOR FREE</b>\n\n"
                "Quick overview:\n"
                "1️⃣ Open the call\n"
                "2️⃣ Open the suggested bookmakers\n"
                "3️⃣ Find the right match/market\n"
                "4️⃣ Place the bets as indicated\n\n"
                "In PREMIUM you'll see:\n"
                "• Full step-by-step with screenshots.\n"
                "• How to use calculator + I BET together.\n"
                "• How to react when odds move.\n\n"
            )
    
    keyboard_rows = [
        [InlineKeyboardButton(
            text="💎 Next: I BET" if lang == 'en' else "💎 Suivant: I BET",
            callback_data="guide_view_i_bet"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_i_bet(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """💎 Using I BET - Tracking profits"""
    
    if lang == 'fr':
        if is_premium:
            text = (
                "💎 <b>I BET - TON JOURNAL DE PARIS</b>\n\n"
                "I BET enregistre tes paris directement depuis les calls.\n\n"
                "<b>Comment l'utiliser:</b>\n"
                "1️⃣ Quand tu as placé un call, clique sur ""I BET"".\n"
                "2️⃣ Le bot enregistre mise, cotes, casinos.\n"
                "3️⃣ Quand le match est fini, mets le résultat.\n\n"
                "<b>Pourquoi c'est CRUCIAL:</b>\n"
                "• Tu vois ton vrai ROI.\n"
                "• Tu peux filtrer par type (arb, Middle, Good Odds).\n"
                "• Tu sais quels casinos performants le mieux.\n\n"
            )
        else:
            text = (
                "💎 <b>I BET - SUIVI SIMPLE</b>\n\n"
                "🔓 <b>30% DÉBLOQUÉ POUR FREE</b>\n\n"
                "Tu peux déjà utiliser I BET pour marquer tes bets,\n"
                "mais les stats avancées (graphes, filtres, ROI) sont PREMIUM.\n\n"
                "En PREMIUM tu verras:\n"
                "• Graphiques de profit.\n"
                "• Stats par type de bet.\n"
                "• ROI par bookmaker.\n\n"
            )
    else:
        if is_premium:
            text = (
                "💎 <b>I BET - YOUR BET JOURNAL</b>\n\n"
                "I BET records your bets directly from calls.\n\n"
                "<b>How to use:</b>\n"
                "1️⃣ After placing a call, tap ""I BET"".\n"
                "2️⃣ Bot stores stake, odds, casinos.\n"
                "3️⃣ When game finishes, set the result.\n\n"
                "<b>Why it's CRITICAL:</b>\n"
                "• You see your real ROI.\n"
                "• Filter by bet type (arb, Middle, Good Odds).\n"
                "• See which books are most profitable.\n\n"
            )
        else:
            text = (
                "💎 <b>I BET - SIMPLE TRACKING</b>\n\n"
                "🔓 <b>30% UNLOCKED FOR FREE</b>\n\n"
                "You can already use I BET to mark your bets,\n"
                "but advanced stats (graphs, filters, ROI) are PREMIUM.\n\n"
                "In PREMIUM you'll see:\n"
                "• Profit charts.\n"
                "• Stats by bet type.\n"
                "• ROI by bookmaker.\n\n"
            )
    
    keyboard_rows = [
        [InlineKeyboardButton(
            text="⚠️ Next: Mistakes" if lang == 'en' else "⚠️ Suivant: Mistakes",
            callback_data="guide_view_mistakes"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_mistakes(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """⚠️ Mistakes - Complete costly errors guide"""
    
    if lang == 'fr':
        if is_premium:
            text = (
                "⚠️ <b>10 ERREURS QUI TUENT TES PROFITS</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "1️⃣ <b>NE PAS VÉRIFIER LES COTES</b>\n"
                "💸 Coût: -$50 à -$500 par erreur\n"
                "✅ Solution: Toujours revérifier avant confirmer\n\n"
                "2️⃣ <b>TROP LENT À PLACER</b>\n"
                "💸 Coût: Rate 50% des opportunités\n"
                "✅ Solution: Moins de 60 secondes du call au placement\n\n"
                "3️⃣ <b>ARRONDIR LES MISES</b>\n"
                "💸 Coût: -0.5% à -2% par bet\n"
                "✅ Solution: Mises EXACTES du calculator\n\n"
                "4️⃣ <b>TOUT SUR UN BOOKMAKER</b>\n"
                "💸 Coût: Limité après 2-4 semaines\n"
                "✅ Solution: Max 20-30 arbs/book/mois\n\n"
                "5️⃣ <b>IGNORER I BET</b>\n"
                "💸 Coût: Aucune idée du vrai profit\n"
                "✅ Solution: TOUJOURS cliquer I BET\n\n"
                "6️⃣ <b>CHASSER LES PERTES</b>\n"
                "💸 Coût: -$1,000+ en tilt\n"
                "✅ Solution: Stick au plan\n\n"
                "7️⃣ <b>MAUVAIS MARCHÉ</b>\n"
                "💸 Coût: Perte totale\n"
                "✅ Solution: Triple-check le marché\n\n"
                "8️⃣ <b>IGNORER LES LIMITES</b>\n"
                "💸 Coût: Compte fermé\n"
                "✅ Solution: Max $500-1000/bet\n\n"
                "9️⃣ <b>PAS DIVERSIFIER</b>\n"
                "💸 Coût: -40% profit potentiel\n"
                "✅ Solution: Multi-sports\n\n"
                "🔟 <b>RISKED TROP TÔT</b>\n"
                "💸 Coût: Bankroll explosé\n"
                "✅ Solution: 100+ SAFE d'abord\n\n"
            )
        else:
            text = (
                "⚠️ <b>ERREURS COÛTEUSES</b>\n\n"
                "🔓 <b>30% DÉBLOQUÉ POUR FREE</b>\n\n"
                "Top 3 erreurs visibles:\n\n"
                "1️⃣ Ne pas vérifier les cotes\n"
                "2️⃣ Trop lent\n"
                "3️⃣ Mauvais bookmaker\n\n"
                "🔒 <b>7 AUTRES ERREURS CACHÉES</b>\n\n"
                "Les membres Premium évitent ces pièges\n"
                "et font +50% de profits!\n\n"
            )
    else:
        if is_premium:
            text = (
                "⚠️ <b>10 MISTAKES THAT KILL PROFITS</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "1️⃣ <b>NOT CHECKING ODDS</b>\n"
                "💸 Cost: -$50 to -$500 per mistake\n"
                "✅ Solution: Always double-check\n\n"
                "2️⃣ <b>TOO SLOW TO PLACE</b>\n"
                "💸 Cost: Miss 50% of opportunities\n"
                "✅ Solution: Under 60 seconds from call\n\n"
                "3️⃣ <b>ROUNDING STAKES</b>\n"
                "💸 Cost: -0.5% to -2% per bet\n"
                "✅ Solution: EXACT calculator stakes\n\n"
                "4️⃣ <b>ALL ON ONE BOOK</b>\n"
                "💸 Cost: Limited after 2-4 weeks\n"
                "✅ Solution: Max 20-30 arbs/book/month\n\n"
                "5️⃣ <b>IGNORING I BET</b>\n"
                "💸 Cost: No idea of real profit\n"
                "✅ Solution: ALWAYS click I BET\n\n"
                "6️⃣ <b>CHASING LOSSES</b>\n"
                "💸 Cost: -$1,000+ on tilt\n"
                "✅ Solution: Stick to plan\n\n"
                "7️⃣ <b>WRONG MARKET</b>\n"
                "💸 Cost: Total loss\n"
                "✅ Solution: Triple-check market\n\n"
                "8️⃣ <b>IGNORING LIMITS</b>\n"
                "💸 Cost: Account closed\n"
                "✅ Solution: Max $500-1000/bet\n\n"
                "9️⃣ <b>NOT DIVERSIFYING</b>\n"
                "💸 Cost: -40% potential profit\n"
                "✅ Solution: Multi-sports\n\n"
                "🔟 <b>RISKED TOO EARLY</b>\n"
                "💸 Cost: Blown bankroll\n"
                "✅ Solution: 100+ SAFE first\n\n"
            )
        else:
            text = (
                "⚠️ <b>COSTLY MISTAKES</b>\n\n"
                "🔓 <b>30% UNLOCKED FOR FREE</b>\n\n"
                "Top 3 mistakes revealed:\n\n"
                "1️⃣ Not checking odds\n"
                "2️⃣ Too slow\n"
                "3️⃣ Wrong bookmaker\n\n"
                "🔒 <b>7 OTHER HIDDEN MISTAKES</b>\n\n"
                "Premium members avoid these traps\n"
                "and make +50% more profit!\n\n"
            )
    
    keyboard_rows = [
        [InlineKeyboardButton(
            text="🛡️ Next: Avoid Bans" if lang == 'en' else "🛡️ Suivant: Éviter Bans",
            callback_data="guide_view_avoid_bans"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )]
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_avoid_bans(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """🛡️ Avoid Bans - Complete anti-detection guide"""
    
    if lang == 'fr':
        if is_premium:
            text = (
                "🛡️ <b>ÉVITER LIMITES & BANS - GUIDE COMPLET</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📱 <b>STRATÉGIE PAR BOOKMAKER</b>\n\n"
                "<b>bet365:</b> Max 20 arbs/mois, mises sous $500\n"
                "<b>Betsson:</b> Max 30 arbs/mois, plus tolérant\n"
                "<b>DraftKings:</b> Max 15 arbs/mois, très sensible!\n"
                "<b>BET99:</b> Max 25 arbs/mois, OK pour volume\n"
                "<b>FanDuel:</b> Max 20 arbs/mois, évite retraits\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🕵️ <b>TECHNIQUES ANTI-DÉTECTION</b>\n\n"
                "✅ Mises naturelles (arrondi niveau 1-2)\n"
                "✅ Varie les montants\n"
                "✅ Connecte sans parier parfois\n"
                "✅ Place quelques paris fun ($10-20)\n"
                "✅ Max 2-3 arbs/jour/book\n"
                "✅ Espace tes bets (30+ min)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "⚠️ <b>SIGNAUX D'ALARME</b>\n\n"
                "🔴 Tu es proche de la limite si:\n"
                "• Mises max diminuent\n"
                "• Délais validation augmentent\n"
                "• Messages 'vérification'\n"
                "• Bonus retirés\n\n"
                "Action: STOP 2-4 semaines sur ce book!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💰 <b>STRATÉGIE LONG TERME</b>\n\n"
                "Mois 1-2: Agressif sur 3 books\n"
                "Mois 3-4: Ralentis + 2 nouveaux\n"
                "Mois 5-6: Rotation complète\n"
                "= $2-3k/mois pendant 1 an+! 🚀\n\n"
            )
        else:
            text = (
                "🛡️ <b>ÉVITER LES BANS</b>\n\n"
                "🔓 <b>50% DÉBLOQUÉ POUR FREE</b>\n\n"
                "Conseils de base:\n"
                "• Max 20-30 arbs/book/mois\n"
                "• Varie tes mises\n"
                "• Mixe avec paris normaux\n"
                "• Évite gros retraits rapides\n\n"
                "⚠️ <b>CE QUI MANQUE:</b>\n\n"
                "❌ Stratégie par bookmaker\n"
                "❌ Signaux d'alarme\n"
                "❌ Techniques avancées\n"
                "❌ Plan de rotation\n\n"
                "Ces secrets = 3 mois vs 12+ mois!\n\n"
            )
    else:
        if is_premium:
            text = (
                "🛡️ <b>AVOID LIMITS & BANS - COMPLETE GUIDE</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📱 <b>STRATEGY PER BOOKMAKER</b>\n\n"
                "<b>bet365:</b> Max 20 arbs/month, stakes under $500\n"
                "<b>Betsson:</b> Max 30 arbs/month, more tolerant\n"
                "<b>DraftKings:</b> Max 15 arbs/month, very sensitive!\n"
                "<b>BET99:</b> Max 25 arbs/month, OK for volume\n"
                "<b>FanDuel:</b> Max 20 arbs/month, avoid withdrawals\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🕵️ <b>ANTI-DETECTION TECHNIQUES</b>\n\n"
                "✅ Natural stakes (rounding level 1-2)\n"
                "✅ Vary amounts\n"
                "✅ Login without betting sometimes\n"
                "✅ Place some fun bets ($10-20)\n"
                "✅ Max 2-3 arbs/day/book\n"
                "✅ Space your bets (30+ min)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "⚠️ <b>WARNING SIGNS</b>\n\n"
                "🔴 You're close to limit if:\n"
                "• Max stakes decrease\n"
                "• Validation delays increase\n"
                "• 'Verification' messages\n"
                "• Bonuses removed\n\n"
                "Action: STOP 2-4 weeks on that book!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💰 <b>LONG TERM STRATEGY</b>\n\n"
                "Months 1-2: Aggressive on 3 books\n"
                "Months 3-4: Slow down + 2 new\n"
                "Months 5-6: Complete rotation\n"
                "= $2-3k/month for 1 year+! 🚀\n\n"
            )
        else:
            text = (
                "🛡️ <b>AVOID BANS</b>\n\n"
                "🔓 <b>50% UNLOCKED FOR FREE</b>\n\n"
                "Basic tips:\n"
                "• Max 20-30 arbs/book/month\n"
                "• Vary your stakes\n"
                "• Mix with normal bets\n"
                "• Avoid quick big withdrawals\n\n"
                "⚠️ <b>WHAT'S MISSING:</b>\n\n"
                "❌ Strategy per bookmaker\n"
                "❌ Warning signs\n"
                "❌ Advanced techniques\n"
                "❌ Rotation plan\n\n"
                "These secrets = 3 months vs 12+ months!\n\n"
            )
    
    keyboard_rows = [
        [InlineKeyboardButton(
            text="🧮 Next: Tools" if lang == 'en' else "🧮 Suivant: Outils",
            callback_data="guide_view_tools"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )]
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_tools(callback: types.CallbackQuery, lang: str):
    """🧮 Tools - PREMIUM: calculator, stats, filters"""
    
    if lang == 'fr':
        text = (
            "🧮 <b>OUTILS PREMIUM</b>\n\n"
            "• Calculateur d'arbitrage (stakes auto).\n"
            "• I BET (journal de paris).\n"
            "• Filtres par % (arb, Middle, Good Odds).\n"
            "• Filtres par casinos.\n"
            "• Arrondi automatique des mises.\n\n"
            "Utilise ces outils ensemble pour maximiser ton ROI.\n\n"
        )
    else:
        text = (
            "🧮 <b>PREMIUM TOOLS</b>\n\n"
            "• Arbitrage calculator (auto stakes).\n"
            "• I BET (bet journal).\n"
            "• % filters (arb, Middle, Good Odds).\n"
            "• Casino filters.\n"
            "• Automatic stake rounding.\n\n"
            "Use these tools together to maximize ROI.\n\n"
        )
    keyboard_rows = [
        [InlineKeyboardButton(
            text="🏢 Next: Bookmakers" if lang == 'en' else "🏢 Suivant: Bookmakers",
            callback_data="guide_view_bookmakers"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_bookmakers(callback: types.CallbackQuery, lang: str):
    """🏢 Bookmakers - PREMIUM: how to set up"""
    
    if lang == 'fr':
        text = (
            "🏢 <b>BOOKMAKERS - SETUP</b>\n\n"
            "Objectif: avoir 3-5 comptes actifs pour profiter des arbs.\n\n"
            "Conseils:\n"
            "• Vérifie les bonus de bienvenue mais ne compte pas dessus.\n"
            "• Priorise les books avec bon volume et cashout rapide.\n"
            "• Utilise plusieurs méthodes de dépôt (Interac, carte).\n\n"
        )
    else:
        text = (
            "🏢 <b>BOOKMAKERS - SETUP</b>\n\n"
            "Goal: keep 3-5 active accounts to exploit arbs.\n\n"
            "Tips:\n"
            "• Check welcome bonuses but don't rely on them.\n"
            "• Prioritize books with good volume and fast payouts.\n"
            "• Use multiple deposit methods (Interac, card, etc.).\n\n"
        )
    keyboard_rows = [
        [InlineKeyboardButton(
            text="💎 Next: Good Odds" if lang == 'en' else "💎 Suivant: Good Odds",
            callback_data="guide_view_good_odds"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_good_odds(callback: types.CallbackQuery, lang: str, is_premium: bool = False):
    """💎 Good Odds - PREMIUM (Explain to FREE to drive upgrade)"""
    
    if lang == 'fr':
        text = (
            "💎 <b>GOOD ODDS - Positive EV (+EV)</b>\n\n"
            "👑 <b>PREMIUM EXCLUSIF</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>QU'EST-CE QUE C'EST?</b>\n\n"
            "Good Odds (ou +EV) = paris avec une <b>valeur attendue positive</b>.\n\n"
            "Contrairement à l'arbitrage (profit garanti), +EV signifie:\n"
            "• Tu paries sur UN SEUL côté\n"
            "• Les cotes sont \"surévaluées\" vs probabilité réelle\n"
            "• Long terme = profit mathématique\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>EXEMPLE CONCRET</b>\n\n"
            "Match: Lakers vs Celtics\n\n"
            "<b>Probabilité réelle calculée:</b>\n"
            "Lakers ont 40% de chance de gagner\n\n"
            "<b>Cote offerte par bookmaker:</b>\n"
            "Lakers @ +300 (implique 25% de chance)\n\n"
            "💡 <b>C'est une Good Odd!</b>\n"
            "→ Le bookmaker sous-estime Lakers\n"
            "→ Cote devrait être @ +150 (40%)\n"
            "→ Tu as +15% EV sur ce pari\n\n"
            "<b>Si tu paries $100:</b>\n"
            "✅ Lakers gagnent (40%): +$300 profit\n"
            "❌ Lakers perdent (60%): -$100 perte\n\n"
            "<b>Valeur attendue:</b>\n"
            "EV = (0.40 × $300) - (0.60 × $100) = <b>+$60</b>\n\n"
            "Sur 100 paris similaires: <b>+$6,000 profit!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>POURQUOI C'EST PUISSANT</b>\n\n"
            "✅ Profits plus élevés que l'arbitrage\n"
            "✅ Plus d'opportunités (1 bookmaker suffit)\n"
            "✅ Moins détectable par les bookies\n"
            "✅ Combine bien avec l'arbitrage\n\n"
            "⚠️ Mais variance plus élevée:\n"
            "• Pas de profit garanti par pari\n"
            "• Nécessite plus de paris pour converger\n"
            "• Bankroll plus important recommandé\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📈 <b>RÉSULTATS RÉELS</b>\n\n"
            "Membre Premium (3 mois):\n"
            "• 50 arbs SAFE: $2,000 (garanti)\n"
            "• 30 Good Odds +EV: $1,800 extra\n"
            "• Total: <b>$3,800 vs $2,000</b>\n\n"
            "💎 <b>+90% de profits en combinant les deux!</b>"
        )
        # Only show paywall to FREE users
        if not is_premium:
            text += (
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔒 <b>PREMIUM SEULEMENT</b>\n\n"
                "Good Odds nécessite:\n"
                "• Algo avancé de calcul EV\n"
                "• Data en temps réel\n"
                "• Analyse probabilités\n\n"
                "🚀 Upgrade PREMIUM pour débloquer!"
            )
    else:
        text = (
            "💎 <b>GOOD ODDS - Positive EV (+EV)</b>\n\n"
            "👑 <b>PREMIUM EXCLUSIVE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHAT IS IT?</b>\n\n"
            "Good Odds (or +EV) = bets with <b>positive expected value</b>.\n\n"
            "Unlike arbitrage (guaranteed profit), +EV means:\n"
            "• You bet on ONE side only\n"
            "• Odds are \"overvalued\" vs real probability\n"
            "• Long term = mathematical profit\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>REAL EXAMPLE</b>\n\n"
            "Match: Lakers vs Celtics\n\n"
            "<b>Calculated real probability:</b>\n"
            "Lakers have 40% chance to win\n\n"
            "<b>Odds offered by bookmaker:</b>\n"
            "Lakers @ +300 (implies 25% chance)\n\n"
            "💡 <b>This is a Good Odd!</b>\n"
            "→ Bookmaker underestimates Lakers\n"
            "→ Odds should be @ +150 (40%)\n"
            "→ You have +15% EV on this bet\n\n"
            "<b>If you bet $100:</b>\n"
            "✅ Lakers win (40%): +$300 profit\n"
            "❌ Lakers lose (60%): -$100 loss\n\n"
            "<b>Expected value:</b>\n"
            "EV = (0.40 × $300) - (0.60 × $100) = <b>+$60</b>\n\n"
            "Over 100 similar bets: <b>+$6,000 profit!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>WHY IT'S POWERFUL</b>\n\n"
            "✅ Higher profits than arbitrage\n"
            "✅ More opportunities (1 bookmaker enough)\n"
            "✅ Less detectable by bookies\n"
            "✅ Combines well with arbitrage\n\n"
            "⚠️ But higher variance:\n"
            "• No guaranteed profit per bet\n"
            "• Needs more bets to converge\n"
            "• Bigger bankroll recommended\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📈 <b>REAL RESULTS</b>\n\n"
            "Premium member (3 months):\n"
            "• 50 SAFE arbs: $2,000 (guaranteed)\n"
            "• 30 Good Odds +EV: $1,800 extra\n"
            "• Total: <b>$3,800 vs $2,000</b>\n\n"
            "💎 <b>+90% profits by combining both!</b>"
        )
        # Only show paywall to FREE users
        if not is_premium:
            text += (
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔒 <b>PREMIUM ONLY</b>\n\n"
                "Good Odds requires:\n"
                "• Advanced EV calculation algo\n"
                "• Real-time data\n"
                "• Probability analysis\n\n"
                "🚀 Upgrade PREMIUM to unlock!"
            )
    
    next_label = "🎯 Next: Middle Bets" if lang == 'en' else "🎯 Suivant: Middle Bets"
    keyboard = [
        [InlineKeyboardButton(
            text=next_label,
            callback_data="guide_view_middle_bets"
        )]
    ]
    
    # Only show upgrade button to FREE users
    if not is_premium:
        keyboard.append([InlineKeyboardButton(
            text="🚀 Upgrade to ALPHA" if lang == 'en' else "🚀 Upgrade vers ALPHA",
            callback_data="upgrade_premium"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
        callback_data="learn_guide_pro"
    )])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

async def show_middle_bets(callback: types.CallbackQuery, lang: str, is_premium: bool = False):
    """🎯 Middle Bets - PREMIUM (Explain to FREE to drive upgrade)"""
    
    if lang == 'fr':
        text = (
            "🎯 <b>MIDDLE BETS - La Loterie +EV</b>\n\n"
            "👑 <b>PREMIUM EXCLUSIF</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎰 <b>QU'EST-CE QUE C'EST?</b>\n\n"
            "Un Middle = pari sur DEUX côtés opposés d'un marché qui <b>peuvent TOUS LES DEUX gagner</b>.\n\n"
            "Contrairement à l'arbitrage (1 seul gagne):\n"
            "• Scénario 1: Les deux paris gagnent = JACKPOT!\n"
            "• Scénario 2: 1 gagne, 1 perd = petit profit/perte\n"
            "• C'est comme une loterie avec +EV\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>EXEMPLE CONCRET</b>\n\n"
            "Match NBA: Lakers vs Celtics\n"
            "Total Points Over/Under\n\n"
            "<b>Bookmaker A:</b>\n"
            "Over 215.5 @ -110\n\n"
            "<b>Bookmaker B:</b>\n"
            "Under 218.5 @ -110\n\n"
            "💡 <b>IL Y A UN MIDDLE!</b>\n"
            "Si le match finit entre 216-218 points,\n"
            "les DEUX paris gagnent!\n\n"
            "<b>Scénarios avec $100 sur chaque:</b>\n\n"
            "🎰 <b>MIDDLE (216-218 pts):</b>\n"
            "→ Over 215.5 gagne: +$91\n"
            "→ Under 218.5 gagne: +$91\n"
            "→ TOTAL: <b>+$182 profit!</b> 🔥\n\n"
            "✅ <b>Over gagne (219+ pts):</b>\n"
            "→ Over gagne: +$91\n"
            "→ Under perd: -$100\n"
            "→ Total: <b>-$9</b>\n\n"
            "❌ <b>Under gagne (≤215 pts):</b>\n"
            "→ Over perd: -$100\n"
            "→ Under gagne: +$91\n"
            "→ Total: <b>-$9</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>POURQUOI C'EST PUISSANT</b>\n\n"
            "✅ Potentiel de GROS gains (+$100-300)\n"
            "✅ Risque limité (-$10-20 si manqué)\n"
            "✅ Ratio risque/reward excellent\n"
            "✅ Moins de capital requis vs arbitrage\n\n"
            "📈 <b>ANALYSE PROBABILISTE:</b>\n\n"
            "Si middle arrive 15% du temps:\n"
            "• 15 fois: +$182 = +$2,730\n"
            "• 85 fois: -$9 = -$765\n"
            "• NET sur 100: <b>+$1,965!</b>\n\n"
            "C'est comme une loterie où tu GAGNES long terme!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>VARIANCE ET BANKROLL</b>\n\n"
            "Middle ≠ Arbitrage:\n"
            "• Pas de profit garanti chaque fois\n"
            "• Séquences de pertes possibles\n"
            "• Bankroll plus grand nécessaire\n"
            "• Patience requise (long terme)\n\n"
            "💡 Recommandation:\n"
            "• 5-10% du bankroll en Middle\n"
            "• 90-95% en arbitrage SAFE\n"
            "• = Base solide + upside explosif\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📈 <b>RÉSULTATS RÉELS</b>\n\n"
            "Membre Premium (2 mois):\n"
            "• 40 arbitrages: $1,600 (base)\n"
            "• 15 middles: $2,100 (dont 3 jackpots)\n"
            "• Total: <b>$3,700 vs $1,600</b>\n\n"
            "💎 <b>+131% de profits avec les middles!</b>"
        )
        # Only show paywall to FREE users
        if not is_premium:
            text += (
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔒 <b>PREMIUM SEULEMENT</b>\n\n"
                "Middle Bets nécessite:\n"
                "• Algo de détection de middles\n"
                "• Calcul probabilités\n"
                "• Analyse spreads/totals\n\n"
                "🚀 Upgrade PREMIUM pour débloquer!"
            )
    else:
        text = (
            "🎯 <b>MIDDLE BETS - The +EV Lottery</b>\n\n"
            "👑 <b>PREMIUM EXCLUSIVE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎰 <b>WHAT IS IT?</b>\n\n"
            "A Middle = betting on TWO opposite sides of a market that <b>can BOTH win</b>.\n\n"
            "Unlike arbitrage (only 1 wins):\n"
            "• Scenario 1: Both bets win = JACKPOT!\n"
            "• Scenario 2: 1 wins, 1 loses = small profit/loss\n"
            "• It's like a lottery with +EV\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>REAL EXAMPLE</b>\n\n"
            "NBA Match: Lakers vs Celtics\n"
            "Total Points Over/Under\n\n"
            "<b>Bookmaker A:</b>\n"
            "Over 215.5 @ -110\n\n"
            "<b>Bookmaker B:</b>\n"
            "Under 218.5 @ -110\n\n"
            "💡 <b>THERE'S A MIDDLE!</b>\n"
            "If match finishes between 216-218 points,\n"
            "BOTH bets win!\n\n"
            "<b>Scenarios with $100 on each:</b>\n\n"
            "🎰 <b>MIDDLE (216-218 pts):</b>\n"
            "→ Over 215.5 wins: +$91\n"
            "→ Under 218.5 wins: +$91\n"
            "→ TOTAL: <b>+$182 profit!</b> 🔥\n\n"
            "✅ <b>Over wins (219+ pts):</b>\n"
            "→ Over wins: +$91\n"
            "→ Under loses: -$100\n"
            "→ Total: <b>-$9</b>\n\n"
            "❌ <b>Under wins (≤215 pts):</b>\n"
            "→ Over loses: -$100\n"
            "→ Under wins: +$91\n"
            "→ Total: <b>-$9</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>WHY IT'S POWERFUL</b>\n\n"
            "✅ Potential for BIG wins (+$100-300)\n"
            "✅ Limited risk (-$10-20 if missed)\n"
            "✅ Excellent risk/reward ratio\n"
            "✅ Less capital needed vs arbitrage\n\n"
            "📈 <b>PROBABILISTIC ANALYSIS:</b>\n\n"
            "If middle hits 15% of time:\n"
            "• 15 times: +$182 = +$2,730\n"
            "• 85 times: -$9 = -$765\n"
            "• NET over 100: <b>+$1,965!</b>\n\n"
            "It's like a lottery where you WIN long term!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>VARIANCE & BANKROLL</b>\n\n"
            "Middle ≠ Arbitrage:\n"
            "• No guaranteed profit each time\n"
            "• Possible losing streaks\n"
            "• Bigger bankroll needed\n"
            "• Patience required (long term)\n\n"
            "💡 Recommendation:\n"
            "• 5-10% of bankroll in Middles\n"
            "• 90-95% in SAFE arbitrage\n"
            "• = Solid base + explosive upside\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📈 <b>REAL RESULTS</b>\n\n"
            "Premium member (2 months):\n"
            "• 40 arbitrages: $1,600 (base)\n"
            "• 15 middles: $2,100 (3 jackpots hit)\n"
            "• Total: <b>$3,700 vs $1,600</b>\n\n"
            "💎 <b>+131% profits with middles!</b>"
        )
        # Only show paywall to FREE users
        if not is_premium:
            text += (
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔒 <b>PREMIUM ONLY</b>\n\n"
                "Middle Bets requires:\n"
                "• Middle detection algo\n"
                "• Probability calculation\n"
                "• Spreads/totals analysis\n\n"
            )
    
    keyboard = [
        [InlineKeyboardButton(
            text="🌟 Next: Pro Tips" if lang == 'en' else "🌟 Suivant: Pro Tips",
            callback_data="guide_view_pro_tips"
        )]
    ]
    
    # Only show upgrade button to FREE users
    if not is_premium:
        keyboard.append([InlineKeyboardButton(
            text="🚀 Upgrade to ALPHA" if lang == 'en' else "🚀 Upgrade vers ALPHA",
            callback_data="upgrade_premium"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
        callback_data="learn_guide_pro"
    )])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


async def show_pro_tips(callback: types.CallbackQuery, lang: str):
    """🌟 Pro Tips - PREMIUM advanced advice"""
    
    if lang == 'fr':
        text = (
            "🌟 <b>PRO TIPS</b>\n\n"
            "• Commence en mode SAFE seulement, puis ajoute Good Odds/Middle.\n"
            "• Fixe-toi un objectif hebdo (ex: $300) plutôt que par jour.\n"
            "• Ne trade pas quand tu es fatigué ou tilt.\n"
            "• Revois tes stats chaque semaine dans I BET.\n\n"
        )
    else:
        text = (
            "🌟 <b>PRO TIPS</b>\n\n"
            "• Start with SAFE mode only, then layer Good Odds/Middles.\n"
            "• Set weekly goals (e.g. $300) instead of daily.\n"
            "• Don't trade when tired or tilted.\n"
            "• Review your I BET stats weekly.\n\n"
        )
    keyboard_rows = [
        [InlineKeyboardButton(
            text="⚙️ Next: Settings" if lang == 'en' else "⚙️ Suivant: Paramètres",
            callback_data="guide_view_settings"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_settings(callback: types.CallbackQuery, lang: str):
    """⚙️ Settings - PREMIUM guide"""
    
    if lang == 'fr':
        text = (
            "⚙️ <b>GUIDE DES PARAMÈTRES</b>\n\n"
            "• CASHH: montant total utilisé pour calculer les mises.\n"
            "• Risk %: agressivité sur certains modes.\n"
            "• Notifications: ON/OFF pour les calls.\n"
            "• Filtres %: plage de % pour arb / Middle / Good Odds.\n"
            "• Filtres casinos: inclure/exclure certains books.\n"
            "• Arrondi stakes: rendre les mises plus naturelles.\n\n"
        )
    else:
        text = (
            "⚙️ <b>SETTINGS GUIDE</b>\n\n"
            "• CASHH: total amount used to compute stakes.\n"
            "• Risk %: aggressiveness on some modes.\n"
            "• Notifications: ON/OFF for calls.\n"
            "• % filters: ranges for arb / Middle / Good Odds.\n"
            "• Casino filters: include/exclude some books.\n"
            "• Stake rounding: make stakes look natural.\n\n"
        )
    keyboard_rows = [
        [InlineKeyboardButton(
            text="🔔 Next: Last Call" if lang == 'en' else "🔔 Suivant: Last Call",
            callback_data="guide_view_last_call"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))

async def show_last_call(callback: types.CallbackQuery, lang: str):
    """🔔 Last Call - PREMIUM recap feature"""
    
    if lang == 'fr':
        text = (
            "🔔 <b>LAST CALL SYSTEM - JAMAIS RATER UN PROFIT</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>QU'EST-CE QUE C'EST?</b>\n\n"
            "Last Call sauvegarde tes calls récents qui sont\n"
            "ENCORE VALIDES après que tu les ai manqués!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ <b>DURÉE DE VALIDITÉ</b>\n\n"
            "• 0-5 min: 80% encore valides ✅\n"
            "• 5-10 min: 50% encore valides ⚠️\n"
            "• 10-15 min: 20% encore valides ⚠️\n"
            "• 15-30 min: 5% encore valides ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📱 <b>COMMENT L'UTILISER</b>\n\n"
            "1️⃣ Accès: [Menu] → [🕒 Last Call]\n\n"
            "2️⃣ Tu vois les calls récents avec:\n"
            "• Temps écoulé\n"
            "• Profit potentiel\n"
            "• Status (valide/expiré)\n\n"
            "3️⃣ Clique [Verify] pour vérifier les cotes actuelles\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>EXEMPLE RÉEL</b>\n\n"
            "Tu manques 3 calls le matin.\n"
            "À midi, tu check Last Call:\n"
            "• Call 1: Encore valide! +$45\n"
            "• Call 2: Cotes bougées, skip\n"
            "• Call 3: Encore bon! +$32\n\n"
            "Total récupéré: $77 qui était perdu!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>MEMBRES PREMIUM:</b>\n"
            "+$400/mois en moyenne juste avec Last Call! 🔥\n\n"
        )
    else:
        text = (
            "🔔 <b>LAST CALL SYSTEM - NEVER MISS PROFITS</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHAT IS IT?</b>\n\n"
            "Last Call saves recent calls that are\n"
            "STILL VALID after you missed them!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ <b>VALIDITY DURATION</b>\n\n"
            "• 0-5 min: 80% still valid ✅\n"
            "• 5-10 min: 50% still valid ⚠️\n"
            "• 10-15 min: 20% still valid ⚠️\n"
            "• 15-30 min: 5% still valid ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📱 <b>HOW TO USE</b>\n\n"
            "1️⃣ Access: [Menu] → [🕒 Last Call]\n\n"
            "2️⃣ You see recent calls with:\n"
            "• Time elapsed\n"
            "• Potential profit\n"
            "• Status (valid/expired)\n\n"
            "3️⃣ Click [Verify] to check current odds\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>REAL EXAMPLE</b>\n\n"
            "You miss 3 calls in the morning.\n"
            "At lunch, you check Last Call:\n"
            "• Call 1: Still valid! +$45\n"
            "• Call 2: Odds moved, skip\n"
            "• Call 3: Still good! +$32\n\n"
            "Total recovered: $77 that was lost!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>PREMIUM MEMBERS:</b>\n"
            "+$400/month average just from Last Call! 🔥\n\n"
        )
    keyboard_rows = [
        [InlineKeyboardButton(
            text="🏆 Next: Success Stories" if lang == 'en' else "🏆 Suivant: Success Stories",
            callback_data="guide_view_success_stories"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide Menu" if lang == 'en' else "◀️ Retour au Menu",
            callback_data="learn_guide_pro"
        )],
    ]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))
