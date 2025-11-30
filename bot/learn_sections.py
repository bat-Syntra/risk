"""
Learn System - Sections détaillées du guide
Toutes les 8 sections avec callbacks
"""
from aiogram import F, types, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

# Utilise le même router
from bot.learn_handlers import router
from database import SessionLocal
from models.user import User


@router.callback_query(F.data == "learn_intro")
async def learn_intro(callback: types.CallbackQuery):
    """Section 1: Introduction"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "📖 <b>QU'EST-CE QUE L'ARBITRAGE?</b>\n\n"
            "Parier sur <b>tous les résultats</b> pour garantir un profit.\n\n"
            "<b>📊 Exemple (format identique aux vrais calls):</b>\n\n"
            "🏟️ Canadiens vs Maple Leafs\n"
            "⚽ NHL - Moneyline\n"
            "💰 CASHH: $400.00\n"
            "✅ Profit garanti: $20.00\n"
            "📗 [BetMGM] Canadiens gagnent\n"
            "💵 Miser: $255.00 (-200) → Retour: $420.00\n"
            "❄️ [Coolbet] Maple Leafs gagnent\n"
            "💵 Miser: $145.00 (+255) → Retour: $420.00\n\n"
            "Dans <b>tous les cas</b> → Retour $420 → <b>+$20</b> 💰\n\n"
            "<b>🎯 Avantages</b>\n"
            "✅ Zéro risque mathématique\n"
            "✅ Pas besoin de connaître le sport\n"
            "✅ Le bot trouve les opportunités automatiquement"
        )
    else:
        message = (
            "📖 <b>WHAT IS ARBITRAGE?</b>\n\n"
            "Bet on <b>all outcomes</b> to lock in profit.\n\n"
            "<b>📊 Example (same format as real calls):</b>\n\n"
            "🏟️ Canadiens vs Maple Leafs\n"
            "⚽ NHL - Moneyline\n"
            "💰 CASHH: $400.00\n"
            "✅ Guaranteed Profit: $20.00\n"
            "📗 [BetMGM] Canadiens to win\n"
            "💵 Stake: $255.00 (-200) → Return: $420.00\n"
            "❄️ [Coolbet] Maple Leafs to win\n"
            "💵 Stake: $145.00 (+255) → Return: $420.00\n\n"
            "In <b>both cases</b> → Return $420 → <b>+$20</b> 💰\n\n"
            "<b>🎯 Benefits</b>\n"
            "✅ Zero mathematical risk\n"
            "✅ No sports knowledge required\n"
            "✅ The bot finds opportunities for you"
        )
    
    keyboard = [
        [InlineKeyboardButton(text="◀️ START HERE", callback_data="guide_start"),
         InlineKeyboardButton(text="Modes ▶️", callback_data="learn_modes")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_tools")
async def learn_tools(callback: types.CallbackQuery):
    """New Section: Tools - Calculator, Stats, Settings"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "📱 <b>OUTILS</b>\n\n"
            "🧮 <b>Calculatrice</b> — Vois SAFE / BALANCED / RISKED, ajuste % et favori.\n"
            "📊 <b>Mes Stats</b> — Tes totaux + <b>📜 My Bets</b> pour l’historique éditable.\n"
            "⚙️ <b>Paramètres</b> — CASHH par défaut, % de risk, langue, notifications.\n"
            "💎 <b>I BET</b> — Clique <b>après</b> avoir placé les 2 bets • Voir section <b>Using I BET</b>.\n"
        )
    else:
        msg = (
            "📱 <b>TOOLS</b>\n\n"
            "🧮 <b>Calculator</b> — View SAFE / BALANCED / RISKED, adjust % and favorite.\n"
            "📊 <b>My Stats</b> — Totals + <b>📜 My Bets</b> for editable history.\n"
            "⚙️ <b>Settings</b> — Default CASHH, risk %, language, notifications.\n"
            "💎 <b>I BET</b> — Click <b>after</b> placing both bets • See <b>Using I BET</b>.\n"
        )
    kb = [
        [InlineKeyboardButton(text="◀️ Mistakes", callback_data="learn_mistakes"),
         InlineKeyboardButton(text="Avoid Bans ▶️", callback_data="learn_avoid_bans")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "guide_start")
async def learn_start_here(callback: types.CallbackQuery):
    """New Section: START HERE"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "🚀 <b>POURQUOI LIRE CE GUIDE?</b>\n\n"
            "⏱️ <b>5 minutes = éviter $500+ d'erreurs</b>\n"
            "• Comprendre SAFE vs RISKED\n"
            "• Placer un arb en 2 minutes\n"
            "• Éviter les 5 erreurs fatales\n"
            "• Ne pas se faire limiter\n"
            "• Tracker tes profits avec I BET\n\n"
            "🎯 Après 5 minutes, tu peux faire ton premier arb rentable en confiance.\n\n"
            "Next → <b>Introduction</b>"
        )
        kb = [[InlineKeyboardButton(text="➡️ Introduction", callback_data="learn_intro")], [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]]
    else:
        msg = (
            "🚀 <b>WHY READ THIS GUIDE?</b>\n\n"
            "⏱️ <b>5 minutes = avoid $500+ mistakes</b>\n"
            "• Understand SAFE vs RISKED\n"
            "• Place an arb in 2 minutes\n"
            "• Avoid the 5 fatal mistakes\n"
            "• Don't get limited\n"
            "• Track profits with I BET\n\n"
            "🎯 After 5 minutes, you can confidently place your first profitable arb.\n\n"
            "Next → <b>Introduction</b>"
        )
        kb = [[InlineKeyboardButton(text="➡️ Introduction", callback_data="learn_intro")], [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_ibet")
async def learn_using_ibet(callback: types.CallbackQuery):
    """New Section: Using I BET"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "💎 <b>COMMENT UTILISER I BET</b>\n\n"
            "Quand <b>cliquer</b>: après avoir placé <b>les 2 paris</b> et screenshotté les tickets.\n\n"
            "📊 <b>Enregistrement auto</b>: nombre de bets, CASHH total, profit attendu, date/heure.\n\n"
            "Exemple d'update immédiat:\n"
            "✅ BET ENREGISTRÉ!\n"
            "📊 Aujourd'hui: • Bets: 3 • Misé: $1,200 • Profit prévu: $65.50\n\n"
            "🕐 <b>Le lendemain</b>: auto-question si tu as parié→ <b>Confirmer</b> ou <b>Corriger</b> (3 questions).\n\n"
            "📜 <b>My Bets</b>: historique complet, édition et ROI par bet.\n"
        )
    else:
        msg = (
            "💎 <b>HOW TO USE I BET</b>\n\n"
            "When to <b>click</b>: after placing <b>both bets</b> and screenshotting tickets.\n\n"
            "📊 <b>Auto save</b>: bets count, total CASHH, expected profit, timestamp.\n\n"
            "Instant example:\n"
            "✅ BET RECORDED!\n"
            "📊 Today: • Bets: 3 • Staked: $1,200 • Expected profit: $65.50\n\n"
            "🕐 <b>Next day</b>: auto-prompt if you bet → <b>Confirm</b> or <b>Correct</b> (3 questions).\n\n"
            "📜 <b>My Bets</b>: full history, editing, ROI per bet.\n"
        )
    kb = [
        [InlineKeyboardButton(text="◀️ How to Place", callback_data="learn_howto"),
         InlineKeyboardButton(text="Mistakes ▶️", callback_data="learn_mistakes")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_books")
async def learn_books(callback: types.CallbackQuery):
    """New Section: Bookmaker Guide"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "🏦 <b>GUIDE DES BOOKMAKERS</b>\n\n"
            "🥇 <b>TIER 1</b>: Betsson 🔶, Coolbet ❄️, BET99 💯, bet365 📗\n"
            "🥈 <b>TIER 2</b>: Sports Interaction, Betway, LeoVegas\n"
            "🥉 <b>TIER 3</b>: Mise-o-jeu, Proline, TonyBet\n\n"
            "✅ Setup: 6-8 books, KYC, premier dépôt, 1 pari normal (camouflage).\n"
            "⚠️ Règles d'or: diversifie, garde 20-30% réserve, stakes arrondis.\n"
        )
    else:
        msg = (
            "🏦 <b>BOOKMAKER GUIDE</b>\n\n"
            "🥇 <b>TIER 1</b>: Betsson 🔶, Coolbet ❄️, BET99 💯, bet365 📗\n"
            "🥈 <b>TIER 2</b>: Sports Interaction, Betway, LeoVegas\n"
            "🥉 <b>TIER 3</b>: Mise-o-jeu, Proline, TonyBet\n\n"
            "✅ Setup: 6-8 books, KYC, first deposit, 1 normal bet (camouflage).\n"
            "⚠️ Golden rules: diversify, keep 20-30% reserve, rounded stakes.\n"
        )
    kb = [
        [InlineKeyboardButton(text="◀️ Avoid Bans", callback_data="learn_avoid_bans"),
         InlineKeyboardButton(text="Good Odds ▶️", callback_data="learn_good_odds")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_good_odds")
async def learn_good_odds(callback: types.CallbackQuery):
    """New Section: Good Odds (Positive EV)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "💎 <b>GOOD ODDS - POSITIVE EV BETS</b>\n\n"
            "<b>C'est quoi?</b>\n"
            "Un SEUL pari avec une cote <b>meilleure que la vraie probabilité</b>.\n\n"
            "<b>📊 Exemple RÉEL (+125 odds, 7.5% EV):</b>\n\n"
            "Lakers vs Celtics, Lakers +125\n"
            "💎 EV: +7.5%\n"
            "💵 Stake: $750\n\n"
            "<b>Sur 10 bets ($7,500 total):</b>\n"
            "✅ Tu GAGNES ~5 fois (48%): $4,688\n"
            "❌ Tu PERDS ~5 fois (52%): -$3,750\n"
            "<b>NET: +$938 profit</b> 💰\n\n"
            "<b>💡 Clé importante:</b>\n"
            "Le win rate n'est PAS 50%! Avec +125 odds et 7.5% EV, tu gagnes ~48% (pas 50%!). Le profit vient des MEILLEURES cotes.\n\n"
            "<b>⚠️ Différence vs Arbitrage:</b>\n"
            "❌ PAS de profit garanti\n"
            "❌ Variance court terme (10-20 bets)\n"
            "✅ Profit mathématique long terme (100+ bets)\n\n"
            "<b>🎯 EV Quality (corrigé):</b>\n"
            "• < 5% = ❌ Trop faible\n"
            "• 5-8% = ⚠️ Minimum (bankroll 100x)\n"
            "• 8-12% = ✅ Bon (bankroll 50x)\n"
            "• 12-15% = 💎 Excellent (bankroll 40x)\n"
            "• 15%+ = 🔥 Elite (bankroll 30x)\n\n"
            "<b>📊 Gestion risque (Kelly Criterion):</b>\n"
            "Exemple: $750 stake, +125 odds, 7.5% EV\n"
            "→ Bankroll recommandé: <b>$16,000</b>\n"
            "→ Minimum 50-100 bets avant résultats\n\n"
            "<b>💡 Conseil:</b>\n"
            "Commence avec arbitrages (50+ bets) PUIS Good Odds. Accepte la variance!"
        )
    else:
        msg = (
            "💎 <b>GOOD ODDS - POSITIVE EV BETS</b>\n\n"
            "<b>What is it?</b>\n"
            "A SINGLE bet with odds <b>better than true probability</b>.\n\n"
            "<b>📊 REAL Example (+125 odds, 7.5% EV):</b>\n\n"
            "Lakers vs Celtics, Lakers +125\n"
            "💎 EV: +7.5%\n"
            "💵 Stake: $750\n\n"
            "<b>Over 10 bets ($7,500 total):</b>\n"
            "✅ You WIN ~5 times (48%): $4,688\n"
            "❌ You LOSE ~5 times (52%): -$3,750\n"
            "<b>NET: +$938 profit</b> 💰\n\n"
            "<b>💡 Key insight:</b>\n"
            "Win rate is NOT 50%! With +125 odds and 7.5% EV, you win ~48% (not 50%!). Profit comes from BETTER odds.\n\n"
            "<b>⚠️ Difference vs Arbitrage:</b>\n"
            "❌ NO guaranteed profit\n"
            "❌ Short-term variance (10-20 bets)\n"
            "✅ Mathematical long-term profit (100+ bets)\n\n"
            "<b>🎯 EV Quality (corrected):</b>\n"
            "• < 5% = ❌ Too low\n"
            "• 5-8% = ⚠️ Minimum (100x bankroll)\n"
            "• 8-12% = ✅ Good (50x bankroll)\n"
            "• 12-15% = 💎 Excellent (40x bankroll)\n"
            "• 15%+ = 🔥 Elite (30x bankroll)\n\n"
            "<b>📊 Risk management (Kelly Criterion):</b>\n"
            "Example: $750 stake, +125 odds, 7.5% EV\n"
            "→ Recommended bankroll: <b>$16,000</b>\n"
            "→ Minimum 50-100 bets before results\n\n"
            "<b>💡 Tip:</b>\n"
            "Start with arbitrages (50+ bets) THEN Good Odds. Accept variance!"
        )
    kb = [
        [InlineKeyboardButton(text="◀️ Bookmakers", callback_data="learn_books"),
         InlineKeyboardButton(text="Middle Bets ▶️", callback_data="learn_middle")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_middle")
async def learn_middle(callback: types.CallbackQuery):
    """New Section: Middle Bets"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "🎯 <b>MIDDLE BETS - EV+ LOTTERY</b>\n\n"
            "<b>C'est quoi?</b>\n"
            "Deux paris overlapping: petite perte fréquente, GROS gain rare.\n\n"
            "<b>Exemple:</b>\n"
            "LeBron Points\n"
            "🏀 Over 20.5 @ DraftKings (-118)\n"
            "🏀 Under 22.5 @ FanDuel (+114)\n\n"
            "<b>Scénarios:</b>\n"
            "• ≤20 ou ≥23 points: -$0.50 (85% du temps) ❌\n"
            "• 21 ou 22 points: +$46.50 (15% du temps) 🚀\n\n"
            "<b>EV Calculation:</b>\n"
            "(0.85 × -$0.50) + (0.15 × $46.50) = +$6.55 par bet!\n\n"
            "<b>⚠️ Différence vs Arbitrage:</b>\n"
            "❌ Tu PERDS souvent (85%)\n"
            "✅ Mais jackpot rare compense\n"
            "✅ EV+ long terme\n\n"
            "<b>📊 Gestion risque:</b>\n"
            "• Bankroll minimum: 100x total stake\n"
            "• Minimum bets: 50-100\n"
            "• Variance ÉLEVÉE!\n\n"
            "<b>💡 C'est comme:</b>\n"
            "Un billet de loto à EV+. Tu perds souvent, mais mathématiquement profitable.\n\n"
            "<b>🎯 Conseil:</b>\n"
            "Seulement si tu acceptes perdre souvent pour le gros gain rare."
        )
    else:
        msg = (
            "🎯 <b>MIDDLE BETS - EV+ LOTTERY</b>\n\n"
            "<b>What is it?</b>\n"
            "Two overlapping bets: small frequent loss, BIG rare gain.\n\n"
            "<b>Example:</b>\n"
            "LeBron Points\n"
            "🏀 Over 20.5 @ DraftKings (-118)\n"
            "🏀 Under 22.5 @ FanDuel (+114)\n\n"
            "<b>Scenarios:</b>\n"
            "• ≤20 or ≥23 points: -$0.50 (85% of time) ❌\n"
            "• 21 or 22 points: +$46.50 (15% of time) 🚀\n\n"
            "<b>EV Calculation:</b>\n"
            "(0.85 × -$0.50) + (0.15 × $46.50) = +$6.55 per bet!\n\n"
            "<b>⚠️ Difference vs Arbitrage:</b>\n"
            "❌ You LOSE often (85%)\n"
            "✅ But rare jackpot compensates\n"
            "✅ EV+ long term\n\n"
            "<b>📊 Risk management:</b>\n"
            "• Minimum bankroll: 100x total stake\n"
            "• Minimum bets: 50-100\n"
            "• HIGH variance!\n\n"
            "<b>💡 It's like:</b>\n"
            "An EV+ lottery ticket. You lose often, but mathematically profitable.\n\n"
            "<b>🎯 Tip:</b>\n"
            "Only if you accept frequent losses for rare big win."
        )
    kb = [
        [InlineKeyboardButton(text="◀️ Good Odds", callback_data="learn_good_odds"),
         InlineKeyboardButton(text="Pro Tips ▶️", callback_data="learn_advanced")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_legal")
async def learn_legal(callback: types.CallbackQuery):
    """New Section: Tax & Legal"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()
    if lang == 'fr':
        msg = (
            "⚖️ <b>TAXES & LÉGALITÉ (Canada)</b>\n\n"
            "✅ Arbitrage légal • Gains non imposables (loisir)\n"
            "⚠️ Exception: si revenu principal → consulte un comptable\n\n"
            "📋 Garde: screenshots, tableur mensuel, résumé annuel\n"
        )
    else:
        msg = (
            "⚖️ <b>TAX & LEGAL (Canada)</b>\n\n"
            "✅ Arbitrage is legal • Winnings generally non-taxable (hobby)\n"
            "⚠️ Exception: if main income → consult an accountant\n\n"
            "📋 Keep: tickets screenshots, monthly spreadsheet, annual summary\n"
        )
    kb = [
        [InlineKeyboardButton(text=("◀️ Pro Tips" if lang == 'en' else "◀️ Tips Avancés"), callback_data="learn_advanced"),
         InlineKeyboardButton(text=("FAQ ▶️" if lang == 'en' else "FAQ ▶️"), callback_data="learn_faq")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@router.callback_query(F.data == "learn_modes")
async def learn_modes(callback: types.CallbackQuery):
    """Section 2: SAFE vs RISKED"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "🎯 <b>SAFE vs RISKED — CLAIR & CONCRET</b>\n\n"
            "<b>✅ SAFE (recommandé)</b> — Profit GARANTI\n\n"
            "🏟️ Avalanche vs Maple Leafs\n"
            "⚽ NHL - Moneyline\n"
            "💰 CASHH: $500.00\n"
            "✅ Profit garanti: $23.45\n"
            "🔶 [Betsson] Avalanche gagne\n"
            "💵 Miser: $320.50 (-210) → Retour: $523.45\n"
            "❄️ [Coolbet] Maple Leafs gagnent\n"
            "💵 Miser: $179.50 (+191) → Retour: $523.45\n\n"
            "• Si Avalanche gagne: Retour $523.45 → <b>+$23.45</b>\n"
            "• Si Leafs gagnent: Retour $523.45 → <b>+$23.45</b>\n\n"
            "<b>⚠️ RISKED (avancé)</b> — Tu PEUX perdre\n\n"
            "🏟️ Chiefs vs Raiders\n"
            "⚽ NFL - Moneyline\n"
            "💰 CASHH: $500.00\n"
            "⚠️ Mode: RISKED\n"
            "🔶 [Betsson] Chiefs gagnent\n"
            "💵 Miser: $300.00 (-650) → Retour: $346.15\n"
            "🧱 [iBet] Raiders gagnent\n"
            "💵 Miser: $200.00 (+480) → Retour: $1,160.00\n\n"
            "• Chiefs gagnent (90%): $346.15 - $500 = <b>- $153.85</b> 😢\n"
            "• Raiders gagnent (10%): $1,160 - $500 = <b>+$660.00</b> 🔥\n\n"
            "<i>Conseil: fais 50-100 SAFE avant de tester RISKED (max 5-10% du CASHH).</i>"
        )
    else:
        message = (
            "🎯 <b>SAFE vs RISKED — CLEAR & CONCRETE</b>\n\n"
            "<b>✅ SAFE (recommended)</b> — GUARANTEED profit\n\n"
            "🏟️ Avalanche vs Maple Leafs\n"
            "⚽ NHL - Moneyline\n"
            "💰 CASHH: $500.00\n"
            "✅ Guaranteed Profit: $23.45\n"
            "🔶 [Betsson] Avalanche to win\n"
            "💵 Stake: $320.50 (-210) → Return: $523.45\n"
            "❄️ [Coolbet] Maple Leafs to win\n"
            "💵 Stake: $179.50 (+191) → Return: $523.45\n\n"
            "• If Avalanche win: Return $523.45 → <b>+$23.45</b>\n"
            "• If Leafs win: Return $523.45 → <b>+$23.45</b>\n\n"
            "<b>⚠️ RISKED (advanced)</b> — You CAN lose\n\n"
            "🏟️ Chiefs vs Raiders\n"
            "⚽ NFL - Moneyline\n"
            "💰 CASHH: $500.00\n"
            "⚠️ Mode: RISKED\n"
            "🔶 [Betsson] Chiefs to win\n"
            "💵 Stake: $300.00 (-650) → Return: $346.15\n"
            "🧱 [iBet] Raiders to win\n"
            "💵 Stake: $200.00 (+480) → Return: $1,160.00\n\n"
            "• Chiefs win (90%): $346.15 - $500 = <b>- $153.85</b> 😢\n"
            "• Raiders win (10%): $1,160 - $500 = <b>+$660.00</b> 🔥\n\n"
            "<i>Tip: do 50-100 SAFE first; if trying RISKED, keep it ≤10% of CASHH.</i>"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Intro" if lang == 'en' else "◀️ Intro"), callback_data="learn_intro")],
        [InlineKeyboardButton(text=("➡️ CASHH" if lang == 'en' else "➡️ CASHH"), callback_data="learn_bankroll")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_bankroll")
async def learn_bankroll(callback: types.CallbackQuery):
    """Section 3: Gestion bankroll"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "💰 <b>GESTION DE CASHH</b>\n\n"
            "<b>📊 CASHH MINIMUM (RÉALISTE)</b>\n"
            "Débutant: $500-1,000\n"
            "Intermédiaire: $2,000-5,000\n"
            "Avancé: $10,000+\n\n"
            "<b>🎯 STRATÉGIE</b>\n\n"
            "MODE SAFE (Arbitrage):\n"
            "└ Utilise 100% du CASHH\n"
            "└ Zéro risque!\n\n"
            "MODE RISKED (Arbitrage):\n"
            "└ Max 5-10% de risk\n"
            "└ Ex: $1000 → Risk $50-100\n\n"
            "GOOD ODDS (EV+):\n"
            "└ Bankroll Kelly: 30-100x stake\n"
            "└ Ex: $100 stake → $3,000-10,000 bankroll\n"
            "└ Accepte la variance!\n\n"
            "<b>💳 RÉPARTITION CASINOS</b>\n"
            "Ne mets PAS tout sur un casino!\n\n"
            "Idéal (CASHH $3000):\n"
            "└ 6-10 casinos × $200-400\n"
            "└ Reserve: $800\n\n"
            "<b>⚠️ RÈGLES D'OR:</b>\n"
            "1️⃣ Ne parie jamais l'argent dont tu as besoin\n"
            "2️⃣ Commence petit, scale progressivement\n"
            "3️⃣ Track TOUS tes bets\n"
            "4️⃣ Garde toujours une réserve"
        )
    else:
        message = (
            "💰 <b>CASHH MANAGEMENT</b>\n\n"
            "<b>📊 MINIMUM CASHH (REALISTIC)</b>\n"
            "Beginner: $500-1,000\n"
            "Intermediate: $2,000-5,000\n"
            "Advanced: $10,000+\n\n"
            "<b>🎯 STRATEGY</b>\n\n"
            "SAFE MODE (Arbitrage):\n"
            "└ Use 100% of CASHH\n"
            "└ Zero risk!\n\n"
            "RISKED MODE (Arbitrage):\n"
            "└ Max 5-10% risk\n"
            "└ Ex: $1000 → Risk $50-100\n\n"
            "GOOD ODDS (EV+):\n"
            "└ Kelly bankroll: 30-100x stake\n"
            "└ Ex: $100 stake → $3,000-10,000 bankroll\n"
            "└ Accept variance!\n\n"
            "<b>💳 SPREAD ACROSS BOOKS</b>\n"
            "Don't put everything on one book!\n\n"
            "Ideal (CASHH $3000):\n"
            "└ 6-10 books × $200-400\n"
            "└ Reserve: $800\n\n"
            "<b>⚠️ GOLDEN RULES:</b>\n"
            "1️⃣ Never bet money you need\n"
            "2️⃣ Start small, scale progressively\n"
            "3️⃣ Track ALL bets\n"
            "4️⃣ Always keep a reserve"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Modes" if lang == 'fr' else "◀️ Modes"), callback_data="learn_modes")],
        [InlineKeyboardButton(text=("➡️ Comment Placer" if lang == 'fr' else "➡️ How to Place"), callback_data="learn_howto")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_howto")
async def learn_howto(callback: types.CallbackQuery):
    """Section 4: Comment placer"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "⚡ <b>COMMENT PLACER UN ARB</b>\n\n"
            "<b>ÉTAPE 1: PRÉPARATION</b>\n"
            "✅ Comptes multi-casinos • ✅ KYC • ✅ Fonds • ✅ Devices\n\n"
            "<b>ÉTAPE 2: ALERTE</b>\n"
            "Reçois un message <b>comme ceci</b>:\n\n"
            "🏟️ Real Madrid vs Barcelona\n"
            "⚽ La Liga - Team Total Corners\n"
            "💰 CASHH: $400.00\n"
            "✅ Profit garanti: $18.20\n"
            "🧱 [iBet] Barcelona Over 4.5\n"
            "💵 Miser: $185.30 (+124) → Retour: $418.20\n"
            "🔶 [Betsson] Barcelona Under 4.5\n"
            "💵 Miser: $214.70 (-192) → Retour: $418.20\n\n"
            "<b>ÉTAPE 3: EXÉCUTION</b>\n"
            "1️⃣ Ouvre 2 devices (si possible 2 IP)\n"
            "2️⃣ Va au match sur chaque book\n"
            "3️⃣ Entre <b>les stakes EXACTS</b>\n"
            "4️⃣ <b>Place les 2 paris en même temps</b>\n"
            "5️⃣ Screenshot tes tickets\n\n"
            "<b>🚨 ERREURS FATALES:</b> mauvais côté, confondre Over/Under, oublier un leg, parier après changement de cotes\n\n"
            "<i>Après 10-20 arbs, tu seras à l'aise.</i>"
        )
    else:
        message = (
            "⚡ <b>HOW TO PLACE AN ARB</b>\n\n"
            "<b>STEP 1: PREP</b>\n"
            "✅ Multi-book accounts • ✅ KYC • ✅ Funds • ✅ Devices\n\n"
            "<b>STEP 2: ALERT</b>\n"
            "You’ll receive a message <b>like this</b>:\n\n"
            "🏟️ Real Madrid vs Barcelona\n"
            "⚽ La Liga - Team Total Corners\n"
            "💰 CASHH: $400.00\n"
            "✅ Guaranteed Profit: $18.20\n"
            "🧱 [iBet] Barcelona Over 4.5\n"
            "💵 Stake: $185.30 (+124) → Return: $418.20\n"
            "🔶 [Betsson] Barcelona Under 4.5\n"
            "💵 Stake: $214.70 (-192) → Return: $418.20\n\n"
            "<b>STEP 3: EXECUTION</b>\n"
            "1️⃣ Open 2 devices (2 IPs if possible)\n"
            "2️⃣ Navigate to the game on each book\n"
            "3️⃣ Enter <b>the EXACT stakes</b>\n"
            "4️⃣ <b>Place both bets at the same time</b>\n"
            "5️⃣ Screenshot your tickets\n\n"
            "<b>🚨 FATAL ERRORS:</b> wrong side, Over/Under mix-up, forget a leg, bet after odds change\n\n"
            "<i>After 10-20 arbs, you’ll be comfortable.</i>"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ CASHH" if lang == 'en' else "◀️ CASHH"), callback_data="learn_bankroll")],
        [InlineKeyboardButton(text=("➡️ Using I BET" if lang == 'en' else "➡️ Utiliser I BET"), callback_data="learn_ibet")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_avoid_bans")
async def learn_avoid_bans(callback: types.CallbackQuery):
    """Section 5: Éviter bans"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "🛡️ <b>ÉVITER LES BANS</b>\n\n"
            "<b>✅ TECHNIQUES DE CAMOUFLAGE</b>\n\n"
            "<b>1️⃣ ARRONDIS TES STAKES</b>\n"
            "❌ Mauvais: $255.32\n"
            "✅ Bon: $255 ou $260\n"
            "<i>Stakes précis = red flag!</i>\n\n"
            "<b>2️⃣ DUMMY BETS</b> (petits paris récréatifs)\n"
            "<b>3️⃣ VARIE TES SPORTS</b>\n"
            "<b>4️⃣ DEPOSITS & WITHDRAWS</b>: évite les retraits immédiats\n"
            "<b>5️⃣ ÉVITE GROS ARBS</b>: reste à 1-5%\n\n"
            "<b>📡 DISCRÉTION IP/APPAREILS</b>\n"
            "• Idéal: 2 téléphones avec <b>deux SIM/LTE différentes</b> (deux IP)\n"
            "• Demande à un proche d'ouvrir un casino sur son device (2e IP)\n"
            "• Évite de tout faire du même device/IP\n\n"
            "<b>💡 MENTALITÉ</b>\n"
            "Mieux: $2k/mois × 2 ans que $10k × 2 mois puis ban\n\n"
            "<i>Respecte les lois locales et les règles des plateformes.</i>"
        )
    else:
        message = (
            "🛡️ <b>AVOID GETTING LIMITED</b>\n\n"
            "<b>✅ CAMOUFLAGE TECHNIQUES</b>\n\n"
            "<b>1️⃣ ROUND YOUR STAKES</b>\n"
            "❌ Bad: $255.32\n"
            "✅ Good: $255 or $260\n"
            "<i>Exact cents = red flag!</i>\n\n"
            "<b>2️⃣ DUMMY BETS</b> (small recreational bets)\n"
            "<b>3️⃣ MIX SPORTS</b>\n"
            "<b>4️⃣ DEPOSITS/WITHDRAWS</b>: avoid instant cashouts\n"
            "<b>5️⃣ AVOID HUGE ARBS</b>: stick to 1-5%\n\n"
            "<b>📡 DEVICE/IP HYGIENE</b>\n"
            "• Ideally use <b>two phones with different SIM/LTE</b> (two IPs)\n"
            "• Ask a trusted person to open one book on their device (second IP)\n"
            "• Avoid doing everything from the same device/IP\n\n"
            "<b>💡 MINDSET</b>\n"
            "$2k/month × 2 years > $10k × 2 months then limited\n\n"
            "<i>Follow local laws and platform rules.</i>"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Tools" if lang == 'en' else "◀️ Outils"), callback_data="learn_tools")],
        [InlineKeyboardButton(text=("➡️ Bookmakers" if lang == 'en' else "➡️ Bookmakers"), callback_data="learn_books")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_advanced")
async def learn_advanced(callback: types.CallbackQuery):
    """Section 6: Tips avancés"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "🎓 <b>TIPS AVANCÉS</b>\n\n"
            "<b>🔥 MULTI-LEG ARBITRAGE</b> (3 issues+)\n\n"
            "Exemple 3-way (Hockey): A Domicile / Nul / Extérieur\n\n"
            "<b>💰 BONUS ABUSE</b>\n"
            "Combine arbing avec bonus (freebet → hedge)\n\n"
            "<b>🔧 OUTILS</b>\n"
            "Spreadsheet tracker (ROI, historique)\n\n"
            "<b>💡 MINDSET PRO</b>\n"
            "Business > gambling. Objectifs: Déb $500-1000, Inter $2-5k, Expert $10k+\n\n"
            "<i>Arbitrage = Marathon! 🏃</i>"
        )
    else:
        message = (
            "🎓 <b>ADVANCED TIPS</b>\n\n"
            "<b>🔥 MULTI-LEG ARBITRAGE</b> (3+ outcomes)\n\n"
            "Example 3-way (Hockey): Home / Draw / Away\n\n"
            "<b>💰 BONUS ABUSE</b>\n"
            "Combine arbing with bonuses (freebet → hedge)\n\n"
            "<b>🔧 TOOLS</b>\n"
            "Spreadsheet tracker (ROI, history)\n\n"
            "<b>💡 PRO MINDSET</b>\n"
            "Business > gambling. Targets: Beg $500-1000, Inter $2-5k, Expert $10k+\n\n"
            "<i>Arbitrage = Marathon! 🏃</i>"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Middle Bets" if lang == 'en' else "◀️ Middle Bets"), callback_data="learn_middle")],
        [InlineKeyboardButton(text=("➡️ Tax & Legal" if lang == 'en' else "➡️ Taxes & Légal"), callback_data="learn_legal")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_mistakes")
async def learn_mistakes(callback: types.CallbackQuery):
    """Section 7: Erreurs communes"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "⚠️ <b>ERREURS À ÉVITER</b>\n\n"
            "<b>🚨 ERREURS D'EXÉCUTION</b>\n\n"
            "<b>❌ #1: Mauvais côté</b> (Over/Under)\n"
            "<b>❌ #2: Cotes ont changé</b> mais tu paries quand même\n\n"
            "<b>💰 ERREURS CASHH</b>\n"
            "<b>❌ #3: Over-betting</b> (all-in sur 1 arb)\n"
            "<b>❌ #4: Stakes non-arrondis</b> ($247.83)\n\n"
            "<b>💡 CHECKLIST PRÉ-PARI</b>\n"
            "☑️ Bon match/market/côté?\n"
            "☑️ Bonnes cotes?\n"
            "☑️ Stakes arrondis?\n"
            "☑️ Les 2 prêts?\n\n"
            "<b>Si 1 seul ❌ → STOP! 🛑</b>\n\n"
            "<i>Mieux rater un arb que perdre $400!</i>"
        )
    else:
        message = (
            "⚠️ <b>MISTAKES TO AVOID</b>\n\n"
            "<b>🚨 EXECUTION</b>\n\n"
            "<b>❌ #1: Wrong side</b> (Over/Under mix-up)\n"
            "<b>❌ #2: Odds moved</b> but you still bet\n\n"
            "<b>💰 CASHH</b>\n"
            "<b>❌ #3: Over-betting</b> (all-in on 1 arb)\n"
            "<b>❌ #4: Non-rounded stakes</b> ($247.83)\n\n"
            "<b>💡 PRE-BET CHECKLIST</b>\n"
            "☑️ Correct game/market/side?\n"
            "☑️ Current odds okay?\n"
            "☑️ Rounded stakes?\n"
            "☑️ Both ready?\n\n"
            "<b>If 1 ❌ → STOP! 🛑</b>\n\n"
            "<i>Better to miss an arb than lose $400!</i>"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Using I BET" if lang == 'en' else "◀️ I BET"), callback_data="learn_ibet"),
         InlineKeyboardButton(text=("Tools ▶️" if lang == 'en' else "Outils ▶️"), callback_data="learn_tools")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "learn_faq")
async def learn_faq(callback: types.CallbackQuery):
    """Section 8: FAQ"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        message = (
            "❓ <b>FAQ</b>\n\n"
            "<b>Q: Est-ce légal?</b> OUI, au Canada.\n\n"
            "<b>Q: Combien je peux gagner?</b> Réaliste: Déb $300-500/mois, Inter $1k-2k, Expert $5k-15k+\n\n"
            "<b>Q: CASHH nécessaire?</b> Minimum $300-500, idéal $1000-2000\n\n"
            "<b>Q: Temps par jour?</b> 1-2h = 5-10 arbs = $50-200/jour\n\n"
            "<b>Q: Banni?</b> Parfois limité. Avec nos tips: 6-12+ mois facile.\n\n"
            "<b>Q: Puis-je perdre?</b> SAFE = non (math). RISKED = petite perte possible (risk). Erreurs humaines = vrai risque.\n\n"
            "<b>Q: Sports?</b> Pas besoin. C'est math.\n\n"
            "<b>Q: Petits profits?</b> 1-5%/arb × 5/jour = 15% jour. Effet composé!\n\n"
            "<b>Q: Combien de casinos?</b> 4-6 min, 10-15 optimal\n\n"
            "<b>Q: Plans?</b> FREE (2 alertes/jour) • PREMIUM (200 CAD/mois, illimité, ≥0.5%, RISKED, calc, stats, VIP)"
        )
    else:
        message = (
            "❓ <b>FAQ</b>\n\n"
            "<b>Q: Is it legal?</b> YES, in Canada.\n\n"
            "<b>Q: How much can I make?</b> Realistic: Beg $300-500/mo, Inter $1k-2k, Expert $5k-15k+\n\n"
            "<b>Q: Required CASHH?</b> Minimum $300-500, ideal $1000-2000\n\n"
            "<b>Q: Time per day?</b> 1-2h = 5-10 arbs = $50-200/day\n\n"
            "<b>Q: Will I get limited?</b> Some books may limit. With our tips: 6-12+ months is common.\n\n"
            "<b>Q: Can I lose?</b> SAFE = no (math). RISKED = small potential loss (risk). Human error = main risk.\n\n"
            "<b>Q: Need to know sports?</b> No. It's math.\n\n"
            "<b>Q: Why small profits?</b> 1-5%/arb × 5/day = 15% daily. Compounding!\n\n"
            "<b>Q: How many books?</b> 4-6 min, 10-15 optimal\n\n"
            "<b>Q: Plans?</b> FREE (2 alerts/day) • PREMIUM (200 CAD/mo, unlimited, ≥0.5%, RISKED, calc, stats, VIP)"
        )
    
    keyboard = [
        [InlineKeyboardButton(text=("◀️ Tax & Legal" if lang == 'en' else "◀️ Taxes & Légal"), callback_data="learn_legal")],
        [InlineKeyboardButton(text=("🏠 Menu" if lang == 'en' else "🏠 Menu"), callback_data="learn_menu")]
    ]
    
    await callback.message.edit_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
