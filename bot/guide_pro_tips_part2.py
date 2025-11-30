"""
PRO TIPS - Parts 2a, 2b and 3
Section 2 split into 4 parts total for Telegram message length
Section 3: Execution Excellence
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode


async def show_pro_tips_section2_part2a(callback: types.CallbackQuery, lang: str):
    """Section 2 Part 2a: Recreational bets & Book selection"""
    
    if lang == 'fr':
        text = (
            "🛡️ <b>PRO TIPS - SECTION 2 (Part 2a)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>5️⃣ BETS 'RÉCRÉATIFS' STRATÉGIQUES</b>\n\n"
            "Controversé mais effectif.\n\n"
            "Les maths:\n"
            "• 95% arbs = $1,000/mois profit\n"
            "• 5% recreational = -$50/mois EV\n"
            "• Net: $950/mois\n"
            "• Lifespan: 2-3x plus long\n\n"
            "Types de bets récréatifs:\n"
            "• Parlays populaires ($10-20)\n"
            "• Big game spreads (Super Bowl, Finals)\n"
            "• Props mainstream\n"
            "• Losing bets mixés naturellement\n\n"
            "⚠️ Règles:\n"
            "• Moins de 5% de l'action totale\n"
            "• Small stakes seulement ($10-25)\n"
            "• Marchés populaires seulement\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>6️⃣ SÉLECTION DE BOOKS</b>\n\n"
            "🔵 <b>SHARP BOOKS</b> (Jamais/rarement limitent):\n"
            "• Pinnacle, Bookmaker, BetCRIS\n"
            "→ Accueillent winners, marges basses\n\n"
            "🟢 <b>SOFT BOOKS</b> (Smart play = années):\n"
            "• Betsson, BET99, Coolbet, bet365\n"
            "• Sports Interaction, Betway\n"
            "→ PEUVENT durer années si bien fait\n\n"
            "🟡 <b>LIMITEURS AGRESSIFS</b> (6-12 mois):\n"
            "• FanDuel, DraftKings (books US)\n"
            "→ Extrais value vite\n\n"
            "Stratégie:\n"
            "• Build core sur sharp books\n"
            "• Rotate soft books (1-3 ans chacun)\n"
            "• Burn aggressive books (extract & move)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🛡️ <b>PRO TIPS - SECTION 2 (Part 2a)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>5️⃣ STRATEGIC RECREATIONAL BETS</b>\n\n"
            "Controversial but effective.\n\n"
            "The math:\n"
            "• 95% arbs = $1,000/month profit\n"
            "• 5% recreational = -$50/month EV\n"
            "• Net: $950/month\n"
            "• Lifespan: 2-3x longer\n\n"
            "Types of recreational bets:\n"
            "• Popular parlays ($10-20)\n"
            "• Big game spreads (Super Bowl, Finals)\n"
            "• Mainstream props\n"
            "• Losing bets mixed naturally\n\n"
            "⚠️ Rules:\n"
            "• Under 5% of total action\n"
            "• Small stakes only ($10-25)\n"
            "• Popular markets only\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>6️⃣ BOOK SELECTION</b>\n\n"
            "🔵 <b>SHARP BOOKS</b> (Never/rarely limit):\n"
            "• Pinnacle, Bookmaker, BetCRIS\n"
            "→ Welcome winners, low margins\n\n"
            "🟢 <b>SOFT BOOKS</b> (Smart play = years):\n"
            "• Betsson, BET99, Coolbet, bet365\n"
            "• Sports Interaction, Betway\n"
            "→ CAN last years if done right\n\n"
            "🟡 <b>AGGRESSIVE LIMITERS</b> (6-12 months):\n"
            "• FanDuel, DraftKings (US books)\n"
            "→ Extract value fast\n\n"
            "Strategy:\n"
            "• Build core on sharp books\n"
            "• Rotate soft books (1-3 years each)\n"
            "• Burn aggressive books (extract & move)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    kb = [
        [InlineKeyboardButton(
            text="➡️ Part 2b: Multi-Accounts" if lang == 'en' else "➡️ Part 2b: Multi-Comptes",
            callback_data="guide_pro_tips_2c"
        )],
        [InlineKeyboardButton(
            text="◀️ Section 2 (Part 1)" if lang == 'en' else "◀️ Section 2 (Part 1)",
            callback_data="guide_pro_tips_2"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide" if lang == 'en' else "◀️ Retour au Guide",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


async def show_pro_tips_section2_part2b(callback: types.CallbackQuery, lang: str):
    """Section 2 Part 2b: Multi-account strategies"""
    
    if lang == 'fr':
        text = (
            "🛡️ <b>PRO TIPS - SECTION 2 (Part 2b)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>TACTIQUES AVANCÉES</b>\n\n"
            "⚠️ <b>DISCLAIMER:</b>\n"
            "Techniquement contre ToS.\n"
            "Présenté pour éducation.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>7️⃣ COMPTES DE CONFIANCE</b>\n\n"
            "Réalité: Beaucoup d'arbers utilisent comptes de confiance.\n\n"
            "✅ <b>Approche PLUS SÛRE:</b>\n"
            "• Ami/famille NOM DIFFÉRENT\n"
            "• Personne qui bet DÉJÀ récréativement\n"
            "• ILS contrôlent (pas toi)\n"
            "• Tu conseilles, ILS placent\n\n"
            "Pourquoi moins risqué:\n"
            "• Historique naturel\n"
            "• Pas que des arbs\n"
            "• KYC match personne\n"
            "• IP/device match\n\n"
            "🎯 <b>PRINCIPES CLÉS</b>\n\n"
            "1️⃣ POLYVALENCE = TOUT\n"
            "• Mix bets récréatifs\n"
            "• Look normal bettor\n\n"
            "2️⃣ PATTERNS NATURELS\n"
            "• Leur device/IP habituel\n"
            "• Ajoute arbs graduellement\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>LÉGAL & ÉTHIQUE</b>\n\n"
            "ToS prohibent:\n"
            "• Une personne = plusieurs comptes\n"
            "• Bet pour quelqu'un d'autre\n\n"
            "Violer ToS:\n"
            "• Fermeture compte\n"
            "• Confiscation fonds\n\n"
            "Au Canada: Pas illégal (civil)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>TIMELINES RÉALISTES</b>\n\n"
            "<b>Stratégie A:</b> Tes comptes only\n"
            "→ 6-18 mois, $15k-30k\n\n"
            "<b>Stratégie B:</b> Smart stealth\n"
            "→ 1-3 ans, $40k-80k\n\n"
            "<b>Stratégie C:</b> Multi-comptes\n"
            "→ 2-5 ans/compte, $100k-200k+\n\n"
            "💡 <b>VÉRITÉS:</b>\n"
            "1️⃣ Limites pas garanties\n"
            "2️⃣ Comportement > volume\n"
            "3️⃣ C'est un marathon\n\n"
            "Pro: Année 1: $30k-50k → Année 4+: $100k-200k/an\n"
            "Amateur: Mois 1-2: $5k-10k → Mois 3: Limité ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🛡️ <b>PRO TIPS - SECTION 2 (Part 2b)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>ADVANCED TACTICS</b>\n\n"
            "⚠️ <b>DISCLAIMER:</b>\n"
            "Technically against ToS.\n"
            "Educational purposes.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>7️⃣ TRUSTED ACCOUNTS</b>\n\n"
            "Reality: Many successful arbers use trusted accounts.\n\n"
            "✅ <b>SAFER approach:</b>\n"
            "• Friend/family DIFFERENT last name\n"
            "• Person who ALREADY bets recreationally\n"
            "• THEY control (not you)\n"
            "• You advise, THEY place\n\n"
            "Why less risky:\n"
            "• Natural history\n"
            "• Not just arbs\n"
            "• KYC matches person\n"
            "• IP/device matches\n\n"
            "🎯 <b>KEY PRINCIPLES</b>\n\n"
            "1️⃣ POLYVALENCE = EVERYTHING\n"
            "• Mix recreational bets\n"
            "• Look normal bettor\n\n"
            "2️⃣ NATURAL PATTERNS\n"
            "• Their usual device/IP\n"
            "• Add arbs gradually\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚖️ <b>LEGAL & ETHICAL</b>\n\n"
            "ToS prohibit:\n"
            "• One person = multiple accounts\n"
            "• Betting for someone else\n\n"
            "Violating ToS:\n"
            "• Account closure\n"
            "• Funds confiscation\n\n"
            "In Canada: Not illegal (civil)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>REALISTIC TIMELINES</b>\n\n"
            "<b>Strategy A:</b> Your accounts only\n"
            "→ 6-18 months, $15k-30k\n\n"
            "<b>Strategy B:</b> Smart stealth\n"
            "→ 1-3 years, $40k-80k\n\n"
            "<b>Strategy C:</b> Multi-accounts\n"
            "→ 2-5 years/account, $100k-200k+\n\n"
            "💡 <b>TRUTHS:</b>\n"
            "1️⃣ Limits NOT guaranteed\n"
            "2️⃣ Behavior > volume\n"
            "3️⃣ This is a marathon\n\n"
            "Pro: Year 1: $30k-50k → Year 4+: $100k-200k/year\n"
            "Amateur: Month 1-2: $5k-10k → Month 3: Limited ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    kb = [
        [InlineKeyboardButton(
            text="➡️ Section 3: Execution" if lang == 'en' else "➡️ Section 3: Exécution",
            callback_data="guide_pro_tips_3"
        )],
        [InlineKeyboardButton(
            text="◀️ Part 2a" if lang == 'en' else "◀️ Part 2a",
            callback_data="guide_pro_tips_2b"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide" if lang == 'en' else "◀️ Retour au Guide",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


async def show_pro_tips_section3(callback: types.CallbackQuery, lang: str):
    """⚡ Section 3: Execution Excellence"""
    
    if lang == 'fr':
        text = (
            "⚡ <b>PRO TIPS - SECTION 3</b>\n"
            "⚡ <b>EXCELLENCE D'EXÉCUTION</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>CHECKLIST PRE-BET</b>\n\n"
            "Avant chaque bet:\n\n"
            "☑️ 1. LINE VERIFICATION\n"
            "☑️ 2. ODDS CHECK\n"
            "☑️ 3. STAKE VERIFICATION\n"
            "☑️ 4. SIDE CONFIRMATION\n"
            "☑️ 5. SIMULTANEOUS READY\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚨 <b>DÉSASTRES COMMUNS</b>\n\n"
            "<b>1. WRONG SIDE</b> (-$1,303 💸)\n"
            "→ Color-coded system\n"
            "→ Dis à haute voix\n\n"
            "<b>2. LIGNE CHANGÉE</b>\n"
            "→ TOUJOURS re-check\n\n"
            "<b>3. COTES MOVED</b>\n"
            "→ Use calculator verify\n\n"
            "<b>4. STAKE TYPO</b>\n"
            "→ Visual check\n\n"
            "<b>5. PLAYER DNP</b>\n"
            "→ Check status before\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>TIMING OPTIMAL</b>\n\n"
            "🟢 Best times:\n"
            "• Lunch (12-1 PM)\n"
            "• Soir (7-9 PM)\n"
            "• Weekends\n\n"
            "🔴 Évite:\n"
            "• Bet immédiatement\n"
            "• 3:47 AM random league\n\n"
            "Smart > Fastest\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>TRACKING</b>\n\n"
            "Revue hebdo (I BET):\n"
            "• Total profit\n"
            "• ROI par book\n"
            "• ROI par sport\n"
            "• Taux erreur\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🧠 <b>MENTAL GAME</b>\n\n"
            "Quand tilted:\n"
            "🛑 STOP BETTING\n\n"
            "Recovery:\n"
            "1. Break 30-60 min\n"
            "2. Review objectivement\n"
            "3. Learn lesson\n"
            "4. Write it down\n"
            "5. Fresh tomorrow\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏆 <b>RÉSUMÉ FINAL</b>\n\n"
            "💰 Bankroll: 3-5% arb, 1-2% middle\n"
            "🛡️ Stealth: Round stakes, diversify\n"
            "⚡ Execution: Checklist every bet\n"
            "🎯 Mindset: Business not gambling\n"
            "🚀 Scale: Sustainable > aggressive\n\n"
            "$2,000/mois × 3 ans = $72,000 ✅\n"
            "$8,000/mois × 4 mois = Banned ❌\n\n"
            "<b>Play the long game. 🎯</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "⚡ <b>PRO TIPS - SECTION 3</b>\n"
            "⚡ <b>EXECUTION EXCELLENCE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>PRE-BET CHECKLIST</b>\n\n"
            "Before every bet:\n\n"
            "☑️ 1. LINE VERIFICATION\n"
            "☑️ 2. ODDS CHECK\n"
            "☑️ 3. STAKE VERIFICATION\n"
            "☑️ 4. SIDE CONFIRMATION\n"
            "☑️ 5. SIMULTANEOUS READY\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚨 <b>COMMON DISASTERS</b>\n\n"
            "<b>1. WRONG SIDE</b> (-$1,303 💸)\n"
            "→ Color-coded system\n"
            "→ Say out loud\n\n"
            "<b>2. LINE CHANGED</b>\n"
            "→ ALWAYS re-check\n\n"
            "<b>3. ODDS MOVED</b>\n"
            "→ Use calculator verify\n\n"
            "<b>4. STAKE TYPO</b>\n"
            "→ Visual check\n\n"
            "<b>5. PLAYER DNP</b>\n"
            "→ Check status before\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>OPTIMAL TIMING</b>\n\n"
            "🟢 Best times:\n"
            "• Lunch (12-1 PM)\n"
            "• Evening (7-9 PM)\n"
            "• Weekends\n\n"
            "🔴 Avoid:\n"
            "• Bet immediately\n"
            "• 3:47 AM random league\n\n"
            "Smart > Fastest\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>TRACKING</b>\n\n"
            "Weekly review (I BET):\n"
            "• Total profit\n"
            "• ROI per book\n"
            "• ROI per sport\n"
            "• Error rate\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🧠 <b>MENTAL GAME</b>\n\n"
            "When tilted:\n"
            "🛑 STOP BETTING\n\n"
            "Recovery:\n"
            "1. Break 30-60 min\n"
            "2. Review objectively\n"
            "3. Learn lesson\n"
            "4. Write it down\n"
            "5. Fresh tomorrow\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏆 <b>FINAL SUMMARY</b>\n\n"
            "💰 Bankroll: 3-5% arb, 1-2% middle\n"
            "🛡️ Stealth: Round stakes, diversify\n"
            "⚡ Execution: Checklist every bet\n"
            "🎯 Mindset: Business not gambling\n"
            "🚀 Scale: Sustainable > aggressive\n\n"
            "$2,000/month × 3 years = $72,000 ✅\n"
            "$8,000/month × 4 months = Banned ❌\n\n"
            "<b>Play the long game. 🎯</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    kb = [
        [InlineKeyboardButton(
            text="⚙️ Next: Settings Guide" if lang == 'en' else "⚙️ Suivant: Settings Guide",
            callback_data="guide_view_settings"
        )],
        [InlineKeyboardButton(
            text="◀️ Section 2 (Part 2b)" if lang == 'en' else "◀️ Section 2 (Part 2b)",
            callback_data="guide_pro_tips_2c"
        )],
        [InlineKeyboardButton(
            text="◀️ Back to Guide" if lang == 'en' else "◀️ Retour au Guide",
            callback_data="learn_guide_pro"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
