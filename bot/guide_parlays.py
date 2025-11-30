"""
Parlays Guide - What are RISKO Parlays?
Explains the correlation parlay system (Beta feature)
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode


async def show_parlays_guide(callback: types.CallbackQuery, lang: str):
    """🎲 Parlays - Optimized correlation combos"""
    
    if lang == 'fr':
        text = (
            "🎲 <b>PARLAYS - PARIS COMBINÉS OPTIMISÉS</b> 🆕\n\n"
            "⚠️ <b>BETA TEST - Accès ALPHA</b>\n"
            "Fonctionnalité en test pour membres ALPHA.\n"
            "Déploiement BETA prévu après validation.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>C'EST QUOI?</b>\n\n"
            "Un parlay = combinaison de plusieurs paris en UN ticket.\n"
            "Tous doivent gagner → payout multiplié.\n\n"
            "💎 <b>RISKO vs Réguliers</b>\n\n"
            "Parlays réguliers: sélection aléatoire (5-15% win rate)\n"
            "Parlays RISKO: détection de CORRÉLATIONS (+EV garanti)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔬 <b>SYSTÈME DE CORRÉLATION</b>\n\n"
            "Analyse 1000+ matchs/jour pour détecter patterns:\n"
            "• NBA Blowout: Favorite large + Under points\n"
            "• NFL Underdog: 2 underdogs division rivale\n"
            "• NHL Defensive: Matchs défensifs + Under\n"
            "• Soccer Control: Équipe dominante + Under buts\n\n"
            "Boost corrélation: 1.30-1.42x\n"
            "Edge positif garanti sur chaque parlay\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>4 PROFILS DE RISQUE</b>\n\n"
            "🟢 CONSERVATIVE: 50-55% win | 8-12% ROI\n"
            "🟡 BALANCED: 42-48% win | 15-22% ROI\n"
            "🟠 AGGRESSIVE: 30-38% win | 25-40% ROI\n"
            "🔴 LOTTERY: 8-15% win | 50-150% ROI\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>EXEMPLE NBA</b>\n\n"
            "Pattern: NBA Blowout + Under\n\n"
            "Celtics -8.5 @ -110 + Under 215.5 @ -108\n"
            "+ Tatum Over 25.5 pts @ -115\n\n"
            "Mise $50 → Cote +580 → Payout $340 (+$290)\n"
            "Edge: +18% | Prob ajustée: 45%\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚙️ <b>UTILISATION (ALPHA)</b>\n\n"
            "1. /parlay_settings → Configure casinos + risque\n"
            "2. /parlays → Consulte opportunités\n"
            "3. Vérifie cotes (auto + /report_odds)\n"
            "4. Place 1-2% bankroll max\n\n"
            "⚠️ Gestion risque:\n"
            "• Jamais >2% bankroll par parlay\n"
            "• Diversifie profils de risque\n"
            "• Track résultats (My Stats)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>ACCÈS & FEEDBACK</b>\n\n"
            "Fonctionnalité ALPHA en test beta.\n"
            "Ton feedback aide à améliorer le système!\n\n"
            "/menu → Tiers Alpha pour y accéder\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>EN RÉSUMÉ</b>\n\n"
            "Les Parlays RISKO = système algorithmique\n"
            "de détection de corrélations qui booste\n"
            "tes probabilités via patterns mathématiques.\n\n"
            "• En BETA pour ALPHA uniquement\n"
            "• 4 profils de risque adaptés\n"
            "• Edge positif garanti par parlay\n"
            "• Complément parfait à l'arbitrage\n\n"
            "🚀 Diversifie tes profits avec les parlays!"
        )
    else:
        text = (
            "🎲 <b>PARLAYS - OPTIMIZED COMBOS</b> 🆕\n\n"
            "⚠️ <b>BETA TEST - ALPHA Access</b>\n"
            "Feature in testing for ALPHA members.\n"
            "BETA rollout planned after validation.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHAT IS IT?</b>\n\n"
            "Parlay = combine multiple bets into ONE ticket.\n"
            "All must win → multiplied payout.\n\n"
            "💎 <b>RISKO vs Regular</b>\n\n"
            "Regular parlays: random selection (5-15% win rate)\n"
            "RISKO parlays: CORRELATION detection (+EV guaranteed)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔬 <b>CORRELATION SYSTEM</b>\n\n"
            "Analyzes 1000+ games/day to detect patterns:\n"
            "• NBA Blowout: Heavy favorite + Under points\n"
            "• NFL Underdog: 2 underdogs rival division\n"
            "• NHL Defensive: Defensive games + Under\n"
            "• Soccer Control: Dominant team + Under goals\n\n"
            "Correlation boost: 1.30-1.42x\n"
            "Positive edge guaranteed on each parlay\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>4 RISK PROFILES</b>\n\n"
            "🟢 CONSERVATIVE: 50-55% win | 8-12% ROI\n"
            "🟡 BALANCED: 42-48% win | 15-22% ROI\n"
            "🟠 AGGRESSIVE: 30-38% win | 25-40% ROI\n"
            "🔴 LOTTERY: 8-15% win | 50-150% ROI\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>NBA EXAMPLE</b>\n\n"
            "Pattern: NBA Blowout + Under\n\n"
            "Celtics -8.5 @ -110 + Under 215.5 @ -108\n"
            "+ Tatum Over 25.5 pts @ -115\n\n"
            "Stake $50 → Odds +580 → Payout $340 (+$290)\n"
            "Edge: +18% | Adjusted prob: 45%\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚙️ <b>HOW TO USE (ALPHA)</b>\n\n"
            "1. /parlay_settings → Configure casinos + risk\n"
            "2. /parlays → Check opportunities\n"
            "3. Verify odds (auto + /report_odds)\n"
            "4. Place 1-2% bankroll max\n\n"
            "⚠️ Risk management:\n"
            "• Never >2% bankroll per parlay\n"
            "• Diversify risk profiles\n"
            "• Track results (My Stats)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>ACCESS & FEEDBACK</b>\n\n"
            "ALPHA feature in beta testing.\n"
            "Your feedback helps improve the system!\n\n"
            "/menu → Alpha Tiers to access\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>SUMMARY</b>\n\n"
            "RISKO Parlays = algorithmic system for\n"
            "correlation detection that boosts your\n"
            "win probability via mathematical patterns.\n\n"
            "• In BETA for ALPHA only\n"
            "• 4 adapted risk profiles\n"
            "• Positive edge guaranteed per parlay\n"
            "• Perfect complement to arbitrage\n\n"
            "🚀 Diversify your profits with parlays!"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="🏭 Suivant: Book Health Monitor" if lang == 'fr' else "🏭 Next: Book Health Monitor",
            callback_data="guide_book_health_intro"
        )],
        [InlineKeyboardButton(
            text="🏆 Success Stories" if lang == 'fr' else "🏆 Success Stories",
            callback_data="guide_view_success_stories"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour au Menu Guide" if lang == 'fr' else "◀️ Back to Guide Menu",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
