"""
Complete guide sections with full bilingual content
Explains Middle and Good Odds to FREE users to drive upgrades
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode


async def show_start_here_complete(callback: types.CallbackQuery, lang: str):
    """🚀 START HERE - Complete version"""
    
    if lang == 'fr':
        text = (
            "🚀 <b>COMMENCER ICI - Pourquoi lire ce guide?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>CE GUIDE PEUT VOUS SAUVER $500+ D'ERREURS</b>\n\n"
            "L'arbitrage semble simple:\n"
            "1️⃣ Trouve 2 cotes opposées\n"
            "2️⃣ Parie sur les deux\n"
            "3️⃣ Profit garanti\n\n"
            "Mais la réalité est plus complexe...\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>ERREURS COURANTES (coûteuses!)</b>\n\n"
            "❌ Mauvaise gestion du CASHH\n"
            "→ Fonds bloqués, opportunités manquées\n\n"
            "❌ Se faire limiter trop vite\n"
            "→ Game over après 2 semaines\n\n"
            "❌ Ne pas tracker avec I BET\n"
            "→ Impossible de savoir si profitable\n\n"
            "❌ Utiliser le mauvais mode (SAFE vs RISKED)\n"
            "→ Soit trop conservateur, soit trop risqué\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>CE QUE CE GUIDE VA FAIRE</b>\n\n"
            "1. <b>Éviter les erreurs coûteuses</b>\n"
            "   Apprends des erreurs des autres\n\n"
            "2. <b>Maximiser tes profits</b>\n"
            "   Stratégies qui fonctionnent vraiment\n\n"
            "3. <b>Jouer le long jeu</b>\n"
            "   $1k/mois × 2 ans > $5k × 2 mois\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>COMMENCE PAR QUOI?</b>\n\n"
            "🆕 <b>Débutant total</b>\n"
            "→ Lis dans l'ordre (Introduction → Modes → etc.)\n\n"
            "📚 <b>Tu connais l'arbitrage</b>\n"
            "→ Saute à CASHH, How to Place, Avoid Bans\n\n"
            "💎 <b>Premium et sérieux</b>\n"
            "→ Focus sur Tools, Pro Tips, Last Call\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🚀 <b>START HERE - Why read this guide?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>THIS GUIDE CAN SAVE YOU $500+ IN MISTAKES</b>\n\n"
            "Arbitrage seems simple:\n"
            "1️⃣ Find 2 opposite odds\n"
            "2️⃣ Bet on both\n"
            "3️⃣ Guaranteed profit\n\n"
            "But reality is more complex...\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>COMMON MISTAKES (costly!)</b>\n\n"
            "❌ Poor CASHH management\n"
            "→ Funds locked, missed opportunities\n\n"
            "❌ Getting limited too fast\n"
            "→ Game over after 2 weeks\n\n"
            "❌ Not tracking with I BET\n"
            "→ Impossible to know if profitable\n\n"
            "❌ Using wrong mode (SAFE vs RISKED)\n"
            "→ Either too conservative or too risky\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>WHAT THIS GUIDE WILL DO</b>\n\n"
            "1. <b>Avoid costly mistakes</b>\n"
            "   Learn from others' errors\n\n"
            "2. <b>Maximize your profits</b>\n"
            "   Strategies that actually work\n\n"
            "3. <b>Play the long game</b>\n"
            "   $1k/month × 2 years > $5k × 2 months\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHERE TO START?</b>\n\n"
            "🆕 <b>Total beginner</b>\n"
            "→ Read in order (Introduction → Modes → etc.)\n\n"
            "📚 <b>You know arbitrage</b>\n"
            "→ Jump to CASHH, How to Place, Avoid Bans\n\n"
            "💎 <b>Premium and serious</b>\n"
            "→ Focus on Tools, Pro Tips, Last Call\n\n"
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


async def show_modes_complete(callback: types.CallbackQuery, lang: str, is_premium: bool):
    """🎯 Modes - SAFE vs RISKED explained"""
    
    if lang == 'fr':
        text = (
            "🎯 <b>MODES - SAFE vs RISKED</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>MODE SAFE (Arbitrage Pur)</b>\n\n"
            "✅ <b>Disponible pour TOUS (FREE + PREMIUM)</b>\n\n"
            "Comment ça marche:\n"
            "• Parie sur TOUS les résultats possibles\n"
            "• Profit GARANTI peu importe qui gagne\n"
            "• Zéro risque mathématique\n\n"
            "Exemple:\n"
            "Match: Real vs Barca\n"
            "• Real @ 2.10 (Betsson)\n"
            "• Barca @ 2.15 (bet365)\n"
            "• Profit: 2-4% garanti\n\n"
            "💰 <b>FREE TIER:</b>\n"
            "• 5 calls par jour max\n"
            "• Arbitrages ≤ 2.5% seulement\n"
            "• Espacés de 2 heures\n"
            "• Profit mensuel: $300-600\n\n"
            "💎 <b>PREMIUM TIER:</b>\n"
            "• Calls illimités\n"
            "• Tous les arbitrages\n"
            "• Temps réel\n"
            "• Profit mensuel: $3,000-6,000+\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        if not is_premium:
            text += (
                "🔥 <b>MODE RISKED (PREMIUM SEULEMENT)</b>\n\n"
                "🔒 <b>PAS DISPONIBLE EN FREE</b>\n\n"
                "Qu'est-ce que c'est?\n"
                "• Parie sur UN SEUL côté (pas les deux)\n"
                "• Profits 2-3x plus élevés\n"
                "• Petit risque de perte si mauvais côté\n\n"
                "Exemple:\n"
                "Match: Lakers vs Celtics\n"
                "• Lakers @ +350 (cote élevée)\n"
                "• EV calculé: +12.5%\n\n"
                "Scénarios:\n"
                "✅ Lakers gagnent: +$125 (35% chance)\n"
                "❌ Celtics gagnent: -$100 (65% chance)\n\n"
                "💡 Avec bonne sélection:\n"
                "→ Profit long terme > SAFE mode\n"
                "→ Mais variance plus élevée\n\n"
                "🚀 <b>UPGRADE PREMIUM pour débloquer!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            text += (
                "🔥 <b>MODE RISKED (PREMIUM)</b>\n\n"
                "✅ <b>TU AS ACCÈS!</b>\n\n"
                "Qu'est-ce que c'est?\n"
                "• Parie sur UN SEUL côté (pas les deux)\n"
                "• Profits 2-3x plus élevés que SAFE\n"
                "• Petit risque de perte si mauvais côté\n\n"
                "Exemple:\n"
                "Match: Lakers vs Celtics\n"
                "• Lakers @ +350 (cote élevée)\n"
                "• EV calculé: +12.5%\n\n"
                "Scénarios:\n"
                "✅ Lakers gagnent: +$125 (35% chance)\n"
                "❌ Celtics gagnent: -$100 (65% chance)\n\n"
                "💡 Stratégie:\n"
                "• Utilise 10-20% de ton bankroll en RISKED\n"
                "• Garde 80-90% en SAFE (base solide)\n"
                "• Long terme: Profits maximisés\n\n"
                "📊 Résultats typiques:\n"
                "• 100 paris SAFE: $4,000 profit (garanti)\n"
                "• + 20 paris RISKED: +$2,500 extra\n"
                "• Total: $6,500 vs $4,000 (SAFE seul)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
    else:
        # English version (similar structure)
        text = (
            "🎯 <b>MODES - SAFE vs RISKED</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>SAFE MODE (Pure Arbitrage)</b>\n\n"
            "✅ <b>Available for ALL (FREE + PREMIUM)</b>\n\n"
            "How it works:\n"
            "• Bet on ALL possible outcomes\n"
            "• GUARANTEED profit no matter who wins\n"
            "• Zero mathematical risk\n\n"
            "Example:\n"
            "Match: Real vs Barca\n"
            "• Real @ 2.10 (Betsson)\n"
            "• Barca @ 2.15 (bet365)\n"
            "• Profit: 2-4% guaranteed\n\n"
            "💰 <b>FREE TIER:</b>\n"
            "• 5 calls per day max\n"
            "• Arbs ≤ 2.5% only\n"
            "• 2 hours spacing\n"
            "• Monthly profit: $300-600\n\n"
            "💎 <b>PREMIUM TIER:</b>\n"
            "• Unlimited calls\n"
            "• All arbs\n"
            "• Real-time\n"
            "• Monthly profit: $3,000-6,000+\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        if not is_premium:
            text += (
                "🔥 <b>RISKED MODE (PREMIUM ONLY)</b>\n\n"
                "🔒 <b>NOT AVAILABLE IN FREE</b>\n\n"
                "What is it?\n"
                "• Bet on ONE side only (not both)\n"
                "• 2-3x higher profits\n"
                "• Small risk of loss if wrong side\n\n"
                "Example:\n"
                "Match: Lakers vs Celtics\n"
                "• Lakers @ +350 (high odds)\n"
                "• Calculated EV: +12.5%\n\n"
                "Scenarios:\n"
                "✅ Lakers win: +$125 (35% chance)\n"
                "❌ Celtics win: -$100 (65% chance)\n\n"
                "💡 With good selection:\n"
                "→ Long-term profit > SAFE mode\n"
                "→ But higher variance\n\n"
                "🚀 <b>UPGRADE PREMIUM to unlock!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            text += (
                "🔥 <b>RISKED MODE (PREMIUM)</b>\n\n"
                "✅ <b>YOU HAVE ACCESS!</b>\n\n"
                "What is it?\n"
                "• Bet on ONE side only (not both)\n"
                "• 2-3x higher profits than SAFE\n"
                "• Small risk of loss if wrong side\n\n"
                "Example:\n"
                "Match: Lakers vs Celtics\n"
                "• Lakers @ +350 (high odds)\n"
                "• Calculated EV: +12.5%\n\n"
                "Scenarios:\n"
                "✅ Lakers win: +$125 (35% chance)\n"
                "❌ Celtics win: -$100 (65% chance)\n\n"
                "💡 Strategy:\n"
                "• Use 10-20% of bankroll in RISKED\n"
                "• Keep 80-90% in SAFE (solid base)\n"
                "• Long term: Profits maximized\n\n"
                "📊 Typical results:\n"
                "• 100 SAFE bets: $4,000 profit (guaranteed)\n"
                "• + 20 RISKED bets: +$2,500 extra\n"
                "• Total: $6,500 vs $4,000 (SAFE only)\n\n"
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
    
    if not is_premium:
        keyboard.insert(1, [InlineKeyboardButton(
            text="🚀 Upgrade to ALPHA" if lang == 'en' else "🚀 Upgrade vers ALPHA",
            callback_data="upgrade_premium"
        )])
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
