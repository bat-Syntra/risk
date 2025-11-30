"""
Book Health Monitor Guide - Complete User Guide
Accessible to all users (FREE and ALPHA)
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode


async def show_book_health_intro(callback: types.CallbackQuery, lang: str):
    """🏥 Introduction - What is Book Health Monitor?"""
    
    if lang == 'fr':
        text = (
            "🏥 <b>BOOK HEALTH MONITOR</b>\n\n"
            "Ton système de protection contre les limites\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>C'EST QUOI?</b>\n\n"
            "Le Book Health Monitor analyse TON comportement de paris sur chaque casino "
            "pour prédire quand tu risques de te faire limiter ou bannir.\n\n"
            "🎯 <b>OBJECTIF:</b>\n"
            "Te prévenir AVANT que ça arrive pour que tu puisses ajuster ton jeu.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>DISCLAIMER IMPORTANT:</b>\n\n"
            "Ce système est en BETA TEST.\n\n"
            "• Pas 100% précis (c'est une estimation)\n"
            "• Tu peux être limité sans warning\n"
            "• Ou jamais limité malgré un score élevé\n"
            "• Utilise comme GUIDE, pas comme vérité absolue\n\n"
            "Les casinos changent leurs algorithmes.\n"
            "Aucun système ne peut prédire avec certitude.\n\n"
            "Mais avec tes données + celles de tous les users,\n"
            "on améliore constamment nos prédictions.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🏥 <b>BOOK HEALTH MONITOR</b>\n\n"
            "Your protection system against limits\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>WHAT IS IT?</b>\n\n"
            "Book Health Monitor analyzes YOUR betting behavior at each casino "
            "to predict when you risk being limited or banned.\n\n"
            "🎯 <b>OBJECTIVE:</b>\n"
            "Warn you BEFORE it happens so you can adjust your play.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>IMPORTANT DISCLAIMER:</b>\n\n"
            "This system is in BETA TEST.\n\n"
            "• Not 100% accurate (it's an estimate)\n"
            "• You can be limited without warning\n"
            "• Or never limited despite high score\n"
            "• Use as GUIDE, not absolute truth\n\n"
            "Casinos change their algorithms.\n"
            "No system can predict with certainty.\n\n"
            "But with your data + all users' data,\n"
            "we constantly improve our predictions.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ Pourquoi l'utiliser?" if lang == 'fr' else "➡️ Why use it?",
            callback_data="guide_book_health_why"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour au Menu" if lang == 'fr' else "◀️ Back to Menu",
            callback_data="learn_guide_pro"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_why(callback: types.CallbackQuery, lang: str):
    """💡 Why Use It?"""
    
    if lang == 'fr':
        text = (
            "💡 <b>POURQUOI UTILISER BOOK HEALTH?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. 🚨 ÉVITER LES SURPRISES</b>\n\n"
            "<b>Sans Book Health:</b>\n"
            "→ Tu paris normalement\n"
            "→ Un jour: \"Mise maximale: 5$\"\n"
            "→ Trop tard, t'es limité\n"
            "→ Impossible de withdraw tes profits\n\n"
            "<b>Avec Book Health:</b>\n"
            "→ Tu vois ton score monter\n"
            "→ Warning à 70/100\n"
            "→ Tu ajustes ton jeu\n"
            "→ Tu évites la limite\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>2. 📊 COMPRENDRE CE QUI CLOCHE</b>\n\n"
            "Book Health te dit EXACTEMENT pourquoi tu es à risque:\n\n"
            "\"🔴 Ton CLV est trop élevé (+4.2%)\"\n"
            "\"🟠 Tu paris trop vite (avg 45 secondes)\"\n"
            "\"🟡 Seulement 2 sports (pas assez diversifié)\"\n\n"
            "Tu sais quoi corriger.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>3. 🎯 MAXIMISER TES PROFITS</b>\n\n"
            "<b>Au lieu de:</b>\n"
            "→ Grind un casino à mort\n"
            "→ Te faire limiter après 3 mois\n"
            "→ Perdre accès à tes meilleures cotes\n\n"
            "<b>Tu peux:</b>\n"
            "→ Monitor plusieurs casinos\n"
            "→ Switcher quand score monte\n"
            "→ Garder tous les comptes actifs\n"
            "→ Profit long-terme maximisé\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>4. 🧠 INTELLIGENCE COLLECTIVE</b>\n\n"
            "Plus on est d'users, plus le système apprend:\n\n"
            "100 users → Détection basique\n"
            "500 users → Patterns clairs par casino\n"
            "1000+ users → Quasi-parfait\n\n"
            "En contribuant tes données, tu aides:\n"
            "→ Toi-même (meilleures prédictions)\n"
            "→ Tous les autres users\n"
            "→ On reverse-engineer les algos de chaque casino\n\n"
            "<b>ENSEMBLE ON EST + FORTS.</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "💡 <b>WHY USE BOOK HEALTH?</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. 🚨 AVOID SURPRISES</b>\n\n"
            "<b>Without Book Health:</b>\n"
            "→ You bet normally\n"
            "→ One day: \"Max bet: $5\"\n"
            "→ Too late, you're limited\n"
            "→ Can't withdraw profits\n\n"
            "<b>With Book Health:</b>\n"
            "→ You see your score rising\n"
            "→ Warning at 70/100\n"
            "→ You adjust your play\n"
            "→ You avoid the limit\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>2. 📊 UNDERSTAND WHAT'S WRONG</b>\n\n"
            "Book Health tells you EXACTLY why you're at risk:\n\n"
            "\"🔴 Your CLV is too high (+4.2%)\"\n"
            "\"🟠 You bet too fast (avg 45 seconds)\"\n"
            "\"🟡 Only 2 sports (not diversified)\"\n\n"
            "You know what to fix.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>3. 🎯 MAXIMIZE PROFITS</b>\n\n"
            "<b>Instead of:</b>\n"
            "→ Grinding one casino to death\n"
            "→ Getting limited after 3 months\n"
            "→ Losing access to best odds\n\n"
            "<b>You can:</b>\n"
            "→ Monitor multiple casinos\n"
            "→ Switch when score rises\n"
            "→ Keep all accounts active\n"
            "→ Maximize long-term profit\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>4. 🧠 COLLECTIVE INTELLIGENCE</b>\n\n"
            "More users = better system:\n\n"
            "100 users → Basic detection\n"
            "500 users → Clear patterns per casino\n"
            "1000+ users → Near-perfect\n\n"
            "By contributing your data, you help:\n"
            "→ Yourself (better predictions)\n"
            "→ All other users\n"
            "→ We reverse-engineer each casino's algo\n\n"
            "<b>TOGETHER WE'RE STRONGER.</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ Comment l'activer?" if lang == 'fr' else "➡️ How to activate?",
            callback_data="guide_book_health_activation"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_intro"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_activation(callback: types.CallbackQuery, lang: str):
    """🚀 Activation Guide"""
    
    if lang == 'fr':
        text = (
            "🚀 <b>ACTIVATION - ÉTAPE PAR ÉTAPE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ÉTAPE 1: COMMENCER</b>\n\n"
            "Dans le menu, clique:\n\n"
            "📊 My Stats → 🏥 Book Health Monitor\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ÉTAPE 2: SÉLECTIONNER TES CASINOS</b>\n\n"
            "Le bot va te montrer tous les casinos.\n\n"
            "Sélectionne TOUS ceux que tu utilises:\n\n"
            "✅ bet365\n"
            "✅ Betsson\n"
            "✅ Coolbet\n"
            "✅ BET99\n"
            "... etc.\n\n"
            "💡 TIP: Plus tu en ajoutes, mieux on te protège.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ÉTAPE 3: RÉPONDRE AUX QUESTIONS</b>\n\n"
            "Pour CHAQUE casino, 5 questions rapides:\n\n"
            "Q1: Depuis quand tu as ce compte?\n"
            "→ Exemple: \"6-12 mois\"\n\n"
            "Q2: Combien de paris au total?\n"
            "→ Exemple: \"200-500 bets\"\n\n"
            "Q3: Étais-tu actif avant RISK0?\n"
            "→ Exemple: \"Oui, moyennement\"\n\n"
            "Q4: Combien déposé au total?\n"
            "→ Exemple: \"$2k-$5k\"\n\n"
            "Q5: Que fais-tu sur ce casino?\n"
            "→ Sélectionne: Sports Betting, Casino, Poker, Live\n\n"
            "Prends 2 minutes, sois honnête.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ÉTAPE 4: CONFIRMER</b>\n\n"
            "Le bot résume tes réponses.\n\n"
            "Vérifie que c'est correct → [✅ Confirmer]\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ÉTAPE 5: C'EST FAIT!</b>\n\n"
            "✅ Book Health Monitor activé!\n\n"
            "À partir de maintenant:\n"
            "→ On track automatiquement tes paris\n"
            "→ Ton score est calculé quotidiennement\n"
            "→ Tu reçois des alertes si risque\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>TEMPS TOTAL: 5-10 minutes</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🚀 <b>ACTIVATION - STEP BY STEP</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>STEP 1: START</b>\n\n"
            "In the menu, click:\n\n"
            "📊 My Stats → 🏥 Book Health Monitor\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>STEP 2: SELECT YOUR CASINOS</b>\n\n"
            "The bot will show all casinos.\n\n"
            "Select ALL the ones you use:\n\n"
            "✅ bet365\n"
            "✅ Betsson\n"
            "✅ Coolbet\n"
            "✅ BET99\n"
            "... etc.\n\n"
            "💡 TIP: The more you add, the better we protect you.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>STEP 3: ANSWER QUESTIONS</b>\n\n"
            "For EACH casino, 5 quick questions:\n\n"
            "Q1: How long have you had this account?\n"
            "→ Example: \"6-12 months\"\n\n"
            "Q2: How many total bets?\n"
            "→ Example: \"200-500 bets\"\n\n"
            "Q3: Were you active before RISK0?\n"
            "→ Example: \"Yes, moderately\"\n\n"
            "Q4: How much deposited total?\n"
            "→ Example: \"$2k-$5k\"\n\n"
            "Q5: What do you do on this casino?\n"
            "→ Select: Sports Betting, Casino, Poker, Live\n\n"
            "Take 2 minutes, be honest.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>STEP 4: CONFIRM</b>\n\n"
            "The bot summarizes your answers.\n\n"
            "Verify it's correct → [✅ Confirm]\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>STEP 5: DONE!</b>\n\n"
            "✅ Book Health Monitor activated!\n\n"
            "From now on:\n"
            "→ We automatically track your bets\n"
            "→ Your score is calculated daily\n"
            "→ You receive alerts if at risk\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏱️ <b>TOTAL TIME: 5-10 minutes</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ Comprendre le score" if lang == 'fr' else "➡️ Understanding score",
            callback_data="guide_book_health_score"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_why"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_score(callback: types.CallbackQuery, lang: str):
    """📊 Understanding Your Score"""
    
    if lang == 'fr':
        text = (
            "📊 <b>COMPRENDRE TON SCORE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ton score = <b>0 à 100</b>\n\n"
            "Plus c'est HAUT, plus tu risques d'être limité.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟢 0-30: SAFE</b>\n"
            "├─ Statut: Tout va bien\n"
            "├─ Risque: Très faible\n"
            "├─ Temps estimé: 18+ mois avant limite\n"
            "└─ Action: Continue normalement\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟡 31-50: MONITOR</b>\n"
            "├─ Statut: Quelques signaux\n"
            "├─ Risque: Faible-moyen\n"
            "├─ Temps estimé: 12-18 mois\n"
            "└─ Action: Suis les recommendations légères\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟠 51-70: WARNING</b>\n"
            "├─ Statut: Plusieurs red flags\n"
            "├─ Risque: Moyen-élevé\n"
            "├─ Temps estimé: 6-12 mois\n"
            "└─ Action: IMPORTANT - ajuste ton jeu\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🔴 71-85: HIGH RISK</b>\n"
            "├─ Statut: Comportement très suspect\n"
            "├─ Risque: Élevé\n"
            "├─ Temps estimé: 3-6 mois\n"
            "└─ Action: URGENT - changements majeurs requis\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>⛔ 86-100: CRITICAL</b>\n"
            "├─ Statut: Limite imminente\n"
            "├─ Risque: Très élevé\n"
            "├─ Temps estimé: Semaines/jours\n"
            "└─ Action: CRITIQUE - retire fonds, stop arbs\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>EXEMPLE CONCRET:</b>\n\n"
            "Score: 58/100 🟠\n\n"
            "Ça veut dire quoi?\n\n"
            "→ T'as plusieurs comportements suspects\n"
            "→ Le casino te surveille probablement\n"
            "→ Pas urgent, mais faut ajuster\n"
            "→ Dans 6-12 mois tu risques la limite\n"
            "→ Suis les recommendations du bot\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "📊 <b>UNDERSTANDING YOUR SCORE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Your score = <b>0 to 100</b>\n\n"
            "Higher = More risk of being limited.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟢 0-30: SAFE</b>\n"
            "├─ Status: All good\n"
            "├─ Risk: Very low\n"
            "├─ Estimated time: 18+ months\n"
            "└─ Action: Continue normally\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟡 31-50: MONITOR</b>\n"
            "├─ Status: Some signals\n"
            "├─ Risk: Low-medium\n"
            "├─ Estimated time: 12-18 months\n"
            "└─ Action: Follow light recommendations\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟠 51-70: WARNING</b>\n"
            "├─ Status: Multiple red flags\n"
            "├─ Risk: Medium-high\n"
            "├─ Estimated time: 6-12 months\n"
            "└─ Action: IMPORTANT - adjust play\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🔴 71-85: HIGH RISK</b>\n"
            "├─ Status: Very suspicious behavior\n"
            "├─ Risk: High\n"
            "├─ Estimated time: 3-6 months\n"
            "└─ Action: URGENT - major changes required\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>⛔ 86-100: CRITICAL</b>\n"
            "├─ Status: Limit imminent\n"
            "├─ Risk: Very high\n"
            "├─ Estimated time: Weeks/days\n"
            "└─ Action: CRITICAL - withdraw funds, stop arbs\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Ce qu'on analyse" if lang == 'fr' else "📊 What we track",
            callback_data="guide_book_health_tracking"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_activation"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_tracking(callback: types.CallbackQuery, lang: str):
    """🔍 What We Analyze - Part 1"""
    
    if lang == 'fr':
        text = (
            "🔍 <b>CE QU'ON ANALYSE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Le système regarde 8 facteurs principaux:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1️⃣ WIN RATE (0-25 points)</b>\n\n"
            "Ton % de victoires.\n\n"
            "🟢 &lt; 53%: Normal\n"
            "🟡 53-55%: Légèrement élevé\n"
            "🟠 55-60%: Suspect\n"
            "🔴 60%+: TRÈS suspect\n\n"
            "Pourquoi?\n"
            "→ Bettors normaux gagnent 48-52%\n"
            "→ 60%+ = Sharp player évident\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>2️⃣ CLV - Closing Line Value (0-30 points)</b>\n\n"
            "Est-ce que tu bats la closing line?\n\n"
            "Exemple:\n"
            "→ Tu paris Lakers @ +105\n"
            "→ Closing line: Lakers @ -110\n"
            "→ CLV = +21.5% 🔥\n\n"
            "🟢 CLV négatif: Bon pour casino\n"
            "🟡 +1-2%: Acceptable\n"
            "🟠 +3-5%: Suspect\n"
            "🔴 +5%+: RED FLAG MAJEUR\n\n"
            "C'est LE facteur le + important.\n"
            "High CLV = Sharp bettor = Limite rapide.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>3️⃣ DIVERSITÉ (0-15 points)</b>\n\n"
            "Combien de sports/marchés tu couvres.\n\n"
            "🟢 5+ sports: Bon\n"
            "🟡 3-4 sports: Ok\n"
            "🟠 2 sports: Suspect\n"
            "🔴 1 sport: TRÈS suspect\n\n"
            "Pourquoi?\n"
            "→ Sharps se spécialisent (1-2 sports)\n"
            "→ Récréatifs parient sur tout\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>4️⃣ TIMING (0-15 points)</b>\n\n"
            "Vitesse de réaction aux lignes.\n\n"
            "🟢 5+ minutes: Normal\n"
            "🟡 2-5 minutes: Ok\n"
            "🟠 1-2 minutes: Suspect\n"
            "🔴 &lt; 1 minute: BOT-LIKE\n\n"
            "Pourquoi?\n"
            "→ Sharps/bots parient instantanément\n"
            "→ Récréatifs prennent leur temps\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🔍 <b>WHAT WE ANALYZE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "The system looks at 8 main factors:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1️⃣ WIN RATE (0-25 points)</b>\n\n"
            "Your win %.\n\n"
            "🟢 &lt; 53%: Normal\n"
            "🟡 53-55%: Slightly high\n"
            "🟠 55-60%: Suspicious\n"
            "🔴 60%+: VERY suspicious\n\n"
            "Why?\n"
            "→ Normal bettors win 48-52%\n"
            "→ 60%+ = Obvious sharp player\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>2️⃣ CLV - Closing Line Value (0-30 points)</b>\n\n"
            "Do you beat the closing line?\n\n"
            "Example:\n"
            "→ You bet Lakers @ +105\n"
            "→ Closing line: Lakers @ -110\n"
            "→ CLV = +21.5% 🔥\n\n"
            "🟢 Negative CLV: Good for casino\n"
            "🟡 +1-2%: Acceptable\n"
            "🟠 +3-5%: Suspicious\n"
            "🔴 +5%+: MAJOR RED FLAG\n\n"
            "This is THE most important factor.\n"
            "High CLV = Sharp bettor = Quick limit.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>3️⃣ DIVERSITY (0-15 points)</b>\n\n"
            "How many sports/markets you cover.\n\n"
            "🟢 5+ sports: Good\n"
            "🟡 3-4 sports: Ok\n"
            "🟠 2 sports: Suspicious\n"
            "🔴 1 sport: VERY suspicious\n\n"
            "Why?\n"
            "→ Sharps specialize (1-2 sports)\n"
            "→ Recreationals bet on everything\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>4️⃣ TIMING (0-15 points)</b>\n\n"
            "Speed of reaction to lines.\n\n"
            "🟢 5+ minutes: Normal\n"
            "🟡 2-5 minutes: Ok\n"
            "🟠 1-2 minutes: Suspicious\n"
            "🔴 &lt; 1 minute: BOT-LIKE\n\n"
            "Why?\n"
            "→ Sharps/bots bet instantly\n"
            "→ Recreationals take their time\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ Facteurs 5-8" if lang == 'fr' else "➡️ Factors 5-8",
            callback_data="guide_book_health_tracking2"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_score"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_tracking2(callback: types.CallbackQuery, lang: str):
    """🔍 What We Analyze - Part 2"""
    
    if lang == 'fr':
        text = (
            "🔍 <b>CE QU'ON ANALYSE (suite)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>5️⃣ PATTERN DE MISES (0-10 points)</b>\n\n"
            "Tes stakes sont calculées ou random?\n\n"
            "Mises arrondies ($50, $100): 🟢\n"
            "Mises précises ($47.23): 🔴\n\n"
            "Pourquoi?\n"
            "→ Mises précises = Kelly Criterion\n"
            "→ Kelly = Sharp player\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>6️⃣ TYPE DE BETS (0-20 points)</b>\n\n"
            "Ratio +EV / arb / middle vs récréatifs.\n\n"
            "🟢 &lt;70% sharp bets: Ok\n"
            "🟡 70-80% sharp: Attention\n"
            "🟠 80-90% sharp: Suspect\n"
            "🔴 90%+ sharp: ÉVIDENT\n\n"
            "Pourquoi?\n"
            "→ 100% +EV/arb = Grinder évident\n"
            "→ Faut mélanger avec récréatifs\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>7️⃣ CHANGEMENT D'ACTIVITÉ (0-15 points)</b>\n\n"
            "Si t'étais inactif avant RISK0, puis:\n"
            "→ Soudainement 200 bets/mois\n"
            "→ RED FLAG\n\n"
            "Pourquoi?\n"
            "→ Changement brutal = Suspect\n"
            "→ Casinos remarquent\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>8️⃣ RETRAITS (0-5 points)</b>\n\n"
            "Withdraws fréquents = Grinder.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>SCORE TOTAL = Somme des 8 facteurs</b>\n\n"
            "Exemple:\n"
            "Win rate: 15 pts\n"
            "CLV: 20 pts\n"
            "Diversité: 10 pts\n"
            "Timing: 12 pts\n"
            "Stakes: 6 pts\n"
            "Type bets: 16 pts\n"
            "Activité: 8 pts\n"
            "Retraits: 0 pts\n"
            "────────────\n"
            "TOTAL: 87/100 ⛔ CRITICAL!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🔍 <b>WHAT WE ANALYZE (cont.)</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>5️⃣ STAKE PATTERN (0-10 points)</b>\n\n"
            "Are your stakes calculated or random?\n\n"
            "Rounded stakes ($50, $100): 🟢\n"
            "Precise stakes ($47.23): 🔴\n\n"
            "Why?\n"
            "→ Precise stakes = Kelly Criterion\n"
            "→ Kelly = Sharp player\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>6️⃣ BET TYPE (0-20 points)</b>\n\n"
            "Ratio +EV / arb / middle vs recreational.\n\n"
            "🟢 &lt;70% sharp bets: Ok\n"
            "🟡 70-80% sharp: Caution\n"
            "🟠 80-90% sharp: Suspicious\n"
            "🔴 90%+ sharp: OBVIOUS\n\n"
            "Why?\n"
            "→ 100% +EV/arb = Obvious grinder\n"
            "→ Need to mix with recreational\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>7️⃣ ACTIVITY CHANGE (0-15 points)</b>\n\n"
            "If you were inactive before RISK0, then:\n"
            "→ Suddenly 200 bets/month\n"
            "→ RED FLAG\n\n"
            "Why?\n"
            "→ Sudden change = Suspicious\n"
            "→ Casinos notice\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>8️⃣ WITHDRAWALS (0-5 points)</b>\n\n"
            "Frequent withdrawals = Grinder.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>TOTAL SCORE = Sum of 8 factors</b>\n\n"
            "Example:\n"
            "Win rate: 15 pts\n"
            "CLV: 20 pts\n"
            "Diversity: 10 pts\n"
            "Timing: 12 pts\n"
            "Stakes: 6 pts\n"
            "Bet types: 16 pts\n"
            "Activity: 8 pts\n"
            "Withdrawals: 0 pts\n"
            "────────────\n"
            "TOTAL: 87/100 ⛔ CRITICAL!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ Utiliser le dashboard" if lang == 'fr' else "➡️ Using dashboard",
            callback_data="guide_book_health_dashboard"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_tracking"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_dashboard(callback: types.CallbackQuery, lang: str):
    """💡 Using the Dashboard"""
    
    if lang == 'fr':
        text = (
            "💡 <b>UTILISER LE DASHBOARD</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ACCÈS:</b>\n\n"
            "Tape: /health\n"
            "Ou clique: [Book Health] dans le menu\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>VUE PRINCIPALE:</b>\n\n"
            "Tu vois tous tes casinos avec:\n\n"
            "🔶 Betsson\n"
            "├─ Score: 🟠 58/100 ↗️\n"
            "├─ Statut: WARNING\n"
            "├─ Limite estimée: 9 mois\n"
            "└─ Bets: 147\n\n"
            "📗 bet365\n"
            "├─ Score: 🟢 23/100 →\n"
            "├─ Statut: SAFE\n"
            "├─ Limite estimée: 2+ ans\n"
            "└─ Bets: 89\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>VOIR DÉTAILS D'UN CASINO:</b>\n\n"
            "Clique sur le casino.\n\n"
            "Tu vois:\n\n"
            "📊 <b>SCORE DÉTAILLÉ</b>\n"
            "├─ Chaque facteur (win rate, CLV, etc.)\n"
            "├─ Graphique visuel\n"
            "└─ Tendance (↗️ monte, ↘️ baisse)\n\n"
            "💡 <b>RECOMMENDATIONS</b>\n"
            "├─ Actions prioritaires\n"
            "├─ CRITICAL / HIGH / MEDIUM / LOW\n"
            "└─ Quoi faire exactement\n\n"
            "📈 <b>STATS</b>\n"
            "├─ Total paris\n"
            "├─ Win rate\n"
            "├─ CLV moyen\n"
            "├─ Sports\n"
            "└─ Délai moyen\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>GRAPHIQUE DE TENDANCE:</b>\n\n"
            "Clique [📊 Voir Graphique]\n\n"
            "Montre l'évolution de ton score sur 30 jours.\n\n"
            "Si ça monte ↗️ = Danger\n"
            "Si ça baisse ↘️ = Bon signe\n"
            "Si stable → = Ok\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>FRÉQUENCE DE MISE À JOUR:</b>\n\n"
            "• Score calculé: QUOTIDIEN (3 AM)\n"
            "• Tu peux checker: QUAND TU VEUX\n"
            "• Alertes automatiques: SI CRITIQUE\n\n"
            "Tu n'as RIEN à faire manuellement.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "💡 <b>USING THE DASHBOARD</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>ACCESS:</b>\n\n"
            "Type: /health\n"
            "Or click: [Book Health] in menu\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>MAIN VIEW:</b>\n\n"
            "You see all your casinos with:\n\n"
            "🔶 Betsson\n"
            "├─ Score: 🟠 58/100 ↗️\n"
            "├─ Status: WARNING\n"
            "├─ Estimated limit: 9 months\n"
            "└─ Bets: 147\n\n"
            "📗 bet365\n"
            "├─ Score: 🟢 23/100 →\n"
            "├─ Status: SAFE\n"
            "├─ Estimated limit: 2+ years\n"
            "└─ Bets: 89\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>VIEW CASINO DETAILS:</b>\n\n"
            "Click on the casino.\n\n"
            "You see:\n\n"
            "📊 <b>DETAILED SCORE</b>\n"
            "├─ Each factor (win rate, CLV, etc.)\n"
            "├─ Visual graph\n"
            "└─ Trend (↗️ rising, ↘️ falling)\n\n"
            "💡 <b>RECOMMENDATIONS</b>\n"
            "├─ Priority actions\n"
            "├─ CRITICAL / HIGH / MEDIUM / LOW\n"
            "└─ What to do exactly\n\n"
            "📈 <b>STATS</b>\n"
            "├─ Total bets\n"
            "├─ Win rate\n"
            "├─ Average CLV\n"
            "├─ Sports\n"
            "└─ Average delay\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>TREND GRAPH:</b>\n\n"
            "Click [📊 View Graph]\n\n"
            "Shows evolution of your score over 30 days.\n\n"
            "Rising ↗️ = Danger\n"
            "Falling ↘️ = Good sign\n"
            "Stable → = Ok\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>UPDATE FREQUENCY:</b>\n\n"
            "• Score calculated: DAILY (3 AM)\n"
            "• You can check: ANYTIME\n"
            "• Auto alerts: IF CRITICAL\n\n"
            "You don't need to do ANYTHING manually.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➡️ FAQ" if lang == 'fr' else "➡️ FAQ",
            callback_data="guide_book_health_faq"
        )],
        [InlineKeyboardButton(
            text="◀️ Retour" if lang == 'fr' else "◀️ Back",
            callback_data="guide_book_health_tracking2"
        )]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def show_book_health_faq(callback: types.CallbackQuery, lang: str, is_premium: bool = False):
    """❓ FAQ"""
    
    if lang == 'fr':
        text = (
            "❓ <b>FAQ - QUESTIONS FRÉQUENTES</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q1: \"Le système est précis à combien?\"</b>\n\n"
            "R: On ne peut pas donner un %.\n\n"
            "Pourquoi?\n"
            "→ Chaque casino est différent\n"
            "→ Algos changent\n"
            "→ Pas assez de data encore (beta)\n\n"
            "Mais:\n"
            "→ 100 users: ~60-70% précis\n"
            "→ 500 users: ~75-85% précis\n"
            "→ 1000+ users: ~90%+ précis\n\n"
            "On s'améliore avec le temps.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q2: \"Mon score est 45 mais je me suis fait limiter. Pourquoi?\"</b>\n\n"
            "R: Plusieurs raisons possibles:\n\n"
            "1. Système en beta (pas parfait)\n"
            "2. Casino a changé son algo\n"
            "3. Tu as fait quelque chose de flagrant\n"
            "4. Malchance\n\n"
            "<b>IMPORTANT: Reporte la limite!</b>\n"
            "Ça nous aide à améliorer.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q3: \"Mon score est 85 depuis 2 mois, toujours pas limité?\"</b>\n\n"
            "R: Possible!\n\n"
            "Score = PROBABILITÉ, pas certitude.\n\n"
            "Pense comme la météo:\n"
            "→ 85% chance de pluie\n"
            "→ Parfois il pleut pas quand même\n\n"
            "Mais... tu joues avec le feu.\n"
            "Baisse ton score quand même!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q4: \"Combien de casinos dois-je ajouter?\"</b>\n\n"
            "R: TOUS ceux que tu utilises.\n\n"
            "Minimum recommandé: 3-4\n\n"
            "Plus = Mieux, car:\n"
            "→ Tu peux rotate\n"
            "→ Plus de protection\n"
            "→ Plus de profit long-term\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "❓ <b>FAQ - FREQUENTLY ASKED QUESTIONS</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q1: \"How accurate is the system?\"</b>\n\n"
            "A: We can't give a %.\n\n"
            "Why?\n"
            "→ Each casino is different\n"
            "→ Algorithms change\n"
            "→ Not enough data yet (beta)\n\n"
            "But:\n"
            "→ 100 users: ~60-70% accurate\n"
            "→ 500 users: ~75-85% accurate\n"
            "→ 1000+ users: ~90%+ accurate\n\n"
            "We improve over time.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q2: \"My score is 45 but I got limited. Why?\"</b>\n\n"
            "A: Several possible reasons:\n\n"
            "1. System in beta (not perfect)\n"
            "2. Casino changed its algo\n"
            "3. You did something obvious\n"
            "4. Bad luck\n\n"
            "<b>IMPORTANT: Report the limit!</b>\n"
            "It helps us improve.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q3: \"My score is 85 for 2 months, still not limited?\"</b>\n\n"
            "A: Possible!\n\n"
            "Score = PROBABILITY, not certainty.\n\n"
            "Think like weather:\n"
            "→ 85% chance of rain\n"
            "→ Sometimes it doesn't rain\n\n"
            "But... you're playing with fire.\n"
            "Lower your score anyway!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Q4: \"How many casinos should I add?\"</b>\n\n"
            "A: ALL the ones you use.\n\n"
            "Minimum recommended: 3-4\n\n"
            "More = Better, because:\n"
            "→ You can rotate\n"
            "→ More protection\n"
            "→ More long-term profit\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    # Boutons conditionnels selon le tier
    buttons = []
    
    # Bouton Activer Book Health
    buttons.append([InlineKeyboardButton(
        text="🚀 Activer Book Health" if lang == 'fr' else "🚀 Activate Book Health",
        callback_data="book_health_start_check"
    )])
    
    # Bouton Suivant (conditionnel selon tier)
    if is_premium:
        # ALPHA → CASHH
        buttons.append([InlineKeyboardButton(
            text="➡️ Suivant: CASHH" if lang == 'fr' else "➡️ Next: CASHH",
            callback_data="guide_view_cashh"
        )])
    else:
        # FREE → Success Stories
        buttons.append([InlineKeyboardButton(
            text="➡️ Suivant: Success Stories" if lang == 'fr' else "➡️ Next: Success Stories",
            callback_data="guide_view_success_stories"
        )])
    
    # Bouton retour
    buttons.append([InlineKeyboardButton(
        text="◀️ Menu Guide" if lang == 'fr' else "◀️ Guide Menu",
        callback_data="learn_guide_pro"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
