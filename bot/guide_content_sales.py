"""
Guide Sales Content - Success Stories, Comparisons, Upgr

CTAs
"""
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode


async def show_success_stories(callback: types.CallbackQuery, lang: str):
    """🏆 Real Success Stories"""
    
    if lang == 'fr':
        text = (
            "🏆 <b>Ce que disent les membres</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Utilisateur anonyme #1</b>\n"
            "Bankroll départ: $1,500\n\n"
            "\"J'ai commencé en gratuit pour 2 semaines, histoire de me\n"
            "familiariser. Les 5 calls/jour c'était correct pour apprendre.\n"
            "Après upgrade Alpha, j'ai pu faire 12-15 calls/jour et mes\n"
            "profits mensuels sont passés de $400 à environ $2,200.\n"
            "Maintenant je comprends mieux les patterns et je sais\n"
            "repérer les meilleurs moments.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Utilisateur anonyme #2</b>\n"
            "Bankroll départ: $800\n\n"
            "\"Honnêtement, j'étais sceptique au début. Mais après avoir\n"
            "placé mes premiers arbs en mode SAFE, j'ai vu que ça\n"
            "marchait vraiment. Le calculateur m'aide énormément parce\n"
            "que je suis nul en maths. Maintenant je fais entre $1,500\n"
            "et $2,000 par mois. Pas de quoi lâcher mon job mais c'est un\n"
            "bon complément de revenu.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Utilisateur anonyme #3</b>\n"
            "Bankroll départ: $3,000\n\n"
            "\"Le truc c'est d'être patient et régulier. Faut pas s'attendre\n"
            "à des miracles du jour au lendemain. J'ai mis 3 semaines avant\n"
            "de vraiment être à l'aise. Maintenant avec Last Call je peux\n"
            "check les opportunités que j'ai ratées le matin pendant ma pause\n"
            "lunch. Ça m'a permis de rajouter $500-700 de profit par mois\n"
            "sans effort supplémentaire.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>Note</b>\n\n"
            "Ces témoignages sont anonymisés pour protéger la vie privée\n"
            "des membres. Les résultats varient selon le temps investi,\n"
            "la bankroll et l'expérience.\n\n"
            "Version GRATUITE = bon pour apprendre les bases\n"
            "Version ALPHA = pour aller plus loin et scaler\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "🏆 <b>What members say</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Anonymous user #1</b>\n"
            "Starting bankroll: $1,500\n\n"
            "\"I started with the free version for 2 weeks to get familiar.\n"
            "5 calls/day was fine for learning. After upgrading to Alpha,\n"
            "I could do 12-15 calls/day and my monthly profits went from\n"
            "$400 to around $2,200. Now I understand the patterns better\n"
            "and know how to spot the best opportunities.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Anonymous user #2</b>\n"
            "Starting bankroll: $800\n\n"
            "\"Honestly, I was skeptical at first. But after placing my first\n"
            "arbs in SAFE mode, I saw it actually works. The calculator helps\n"
            "me a ton because I'm terrible at math. Now I make between\n"
            "$1,500 and $2,000 per month. Not enough to quit my job but\n"
            "it's a nice income supplement.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Anonymous user #3</b>\n"
            "Starting bankroll: $3,000\n\n"
            "\"The key is to be patient and consistent. Don't expect miracles\n"
            "overnight. Took me 3 weeks to really get comfortable. Now with\n"
            "Last Call I can check opportunities I missed in the morning during\n"
            "my lunch break. Added $500-700 in monthly profit without extra\n"
            "effort.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>Note</b>\n\n"
            "These testimonials are anonymized to protect members' privacy.\n"
            "Results vary based on time invested, bankroll and experience.\n\n"
            "FREE version = good for learning basics\n"
            "ALPHA version = to go further and scale\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="⚖️ Next: FREE vs ALPHA" if lang == 'en' else "⚖️ Suivant: GRATUIT vs ALPHA",
            callback_data="guide_view_free_vs_premium"
        )],
        [InlineKeyboardButton(
            text="🚀 Start Your Success Story" if lang == 'en' else "🚀 Commence Ton Histoire",
            callback_data="upgrade_premium"
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


async def show_free_vs_premium(callback: types.CallbackQuery, lang: str):
    """⚖️ FREE vs PREMIUM Comparison"""
    
    if lang == 'fr':
        text = (
            "⚖️ <b>BETA vs ALPHA - COMPARAISON CLAIRE</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>COMPARAISON DES FONCTIONNALITÉS</b>\n\n"
            "<b>                      BETA      ALPHA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Calls/jour              5       Illimité\n"
            "Profit maximum       2.5%       Illimité\n"
            "Mode RISKED           ❌           ✅\n"
            "Middle Bets           ❌           ✅\n"
            "Good Odds (+EV)       ❌           ✅\n"
            "Parlays (Beta)        ❌           ✅\n"
            "Book Health          ❌           ✅\n"
            "Calculateur        Basique     Avancé\n"
            "Statistiques          ❌       Dashboard\n"
            "Paramètres         Limité      Complet\n"
            "Last Call             ❌       24h history\n"
            "Support            Email       VIP Priority\n"
            "Guides           Partiel     100% débloqué\n"
            "Referral 20%          ❌           ✅\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>POTENTIEL DE PROFIT</b>\n\n"
            "<b>UTILISATEUR BETA:</b>\n"
            "• 5 calls/jour × $15 moy = $75/jour\n"
            "• Maximum 2.5% profit\n"
            "• Mensuel: <b>$600-900</b> 💰\n"
            "• An 1: $7,200-10,800\n\n"
            "<b>UTILISATEUR ALPHA:</b>\n"
            "• 15-25 arbs/jour × $20 moy = $300-500/jour\n"
            "• + Middle Bets (variance élevée)\n"
            "• + Good Odds (+EV)\n"
            "• + Parlays optimisés (corrélations)\n"
            "• Mensuel: <b>$3,500-7,000+</b> 🔥\n"
            "• An 1: $42,000-84,000+\n\n"
            "Coût: $2,400/an (ou $1,800 avec bonus 🎁)\n"
            "NET: <b>$40,200-82,200+</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>BETA EST POUR QUI?</b>\n\n"
            "✅ Débutants complets\n"
            "✅ Tester le concept\n"
            "✅ Apprendre l'arbitrage\n"
            "✅ Petit bankroll (moins de $500)\n"
            "✅ Temps limité (moins de 1h/jour)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>ALPHA EST POUR QUI?</b>\n\n"
            "✅ Sérieux avec les profits\n"
            "✅ CASHH $1,000+\n"
            "✅ Veut scaler\n"
            "✅ Peut dédier 1-3h/jour\n"
            "✅ Prêt à traiter ça comme un business\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 <b>NOTRE RECOMMANDATION:</b>\n\n"
            "Commence BETA pour 1-2 semaines.\n"
            "Apprends les bases.\n"
            "Place 10-20 arbs.\n"
            "Deviens confortable.\n\n"
            "Puis upgrade quand prêt à scaler.\n\n"
            "⚠️ Mais souviens-toi:\n"
            "Chaque jour en BETA = <b>$100-300 de profit manqué</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "⚖️ <b>BETA vs ALPHA - CLEAR COMPARISON</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>FEATURE COMPARISON</b>\n\n"
            "<b>                    BETA      ALPHA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Calls/day               5       Unlimited\n"
            "Max profit           2.5%       Unlimited\n"
            "RISKED mode           ❌           ✅\n"
            "Middle Bets           ❌           ✅\n"
            "Good Odds (+EV)       ❌           ✅\n"
            "Calculator         Basic       Advanced\n"
            "Statistics            ❌       Dashboard\n"
            "Settings           Limited     Complete\n"
            "Last Call             ❌       24h history\n"
            "Support            Email       VIP Priority\n"
            "Guides           Partial     100% unlock\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>PROFIT POTENTIAL</b>\n\n"
            "<b>BETA USER:</b>\n"
            "• 5 calls/day × $15 avg = $75/day\n"
            "• Max 2.5% profit\n"
            "• Monthly: <b>$600-900</b> 💰\n"
            "• Year 1: $7,200-10,800\n\n"
            "<b>ALPHA USER:</b>\n"
            "• 10-20 arbs/day × $20 avg = $200-400/day\n"
            "• + Middle Bets (high variance)\n"
            "• + Good Odds (+EV)\n"
            "• Monthly: <b>$3,000-6,000+</b> 🔥\n"
            "• Year 1: $36,000-72,000+\n\n"
            "Cost: $2,400/year\n"
            "NET: <b>$33,600-69,600+</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>WHO IS BETA FOR?</b>\n\n"
            "✅ Total beginners\n"
            "✅ Testing the concept\n"
            "✅ Learning arbitrage\n"
            "✅ Small bankroll (under $500)\n"
            "✅ Limited time (under 1h/day)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>WHO IS ALPHA FOR?</b>\n\n"
            "✅ Serious about profits\n"
            "✅ CASHH $1,000+\n"
            "✅ Want to scale\n"
            "✅ Can dedicate 1-3h/day\n"
            "✅ Ready to treat it like a business\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 <b>OUR RECOMMENDATION:</b>\n\n"
            "Start BETA for 1-2 weeks.\n"
            "Learn the basics.\n"
            "Place 10-20 arbs.\n"
            "Get comfortable.\n\n"
            "Then upgrade when ready to scale.\n\n"
            "⚠️ But remember:\n"
            "Every day on BETA = <b>$100-300 missed profit</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="💎 Next: ALPHA" if lang == 'en' else "💎 Suivant: ALPHA",
            callback_data="guide_view_upgrade"
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


async def show_upgrade(callback: types.CallbackQuery, lang: str):
    """💎 Upgrade to Premium CTA"""
    
    if lang == 'fr':
        text = (
            "💎 <b>UPGRADE VERS ALPHA</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔓 <b>DÉBLOQUEZ ACCÈS COMPLET</b>\n\n"
            "✅ Calls arbitrage illimités\n"
            "✅ Middle Bets (EV+ lottery)\n"
            "✅ Good Odds (Positive EV bets)\n"
            "✅ Mode RISKED (profits 2-3x)\n"
            "✅ Calculateur avancé\n"
            "✅ Dashboard statistiques pro\n"
            "✅ Contrôle complet paramètres\n"
            "✅ Système Last Call (24h)\n"
            "✅ Book Health Monitor\n"
            "✅ Tous les guides débloqués\n"
            "✅ Support VIP prioritaire\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>TARIFICATION</b>\n\n"
            "<s>$200</s> <b>$150 CAD/mois</b> 🎁\n"
            "(Rabais nouveau membre - premier mois)\n\n"
            "📈 ANALYSE ROI:\n"
            "• Break even: 1 jour\n"
            "• Profit mois 1: $2,000-3,000+\n"
            "• Coût: $150\n"
            "• NET: <b>$1,850-2,850+</b> 🚀\n\n"
            "💡 C'est un retour de 12-20x sur investissement!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>CE QUE DISENT LES MEMBRES:</b>\n\n"
            "\"Rentabilisé en 2 jours. Super content!\"\n"
            "— Utilisateur anonyme #1\n\n"
            "\"Le Last Call seul vaut le prix. Extra $600-800/mois.\"\n"
            "— Utilisateur anonyme #2\n\n"
            "\"Version gratuite était bien pour apprendre. ALPHA change la donne.\"\n"
            "— Utilisateur anonyme #3\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ <b>OFFRE NOUVEAU MEMBRE:</b>\n\n"
            "🎯 Vérifie ton éligibilité avec /bonus\n"
            "→ Premier mois: $150 (économise $50!)\n"
            "→ Offre valide 1 semaine après inscription\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "💎 <b>UPGRADE TO ALPHA</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔓 <b>UNLOCK COMPLETE ACCESS</b>\n\n"
            "✅ Unlimited arbitrage calls\n"
            "✅ Middle Bets (EV+ lottery)\n"
            "✅ Good Odds (Positive EV bets)\n"
            "✅ RISKED mode (2-3x profits)\n"
            "✅ Advanced calculator\n"
            "✅ Pro statistics dashboard\n"
            "✅ Full settings control\n"
            "✅ Last Call system (24h)\n"
            "✅ Book Health Monitor\n"
            "✅ All guides unlocked\n"
            "✅ VIP priority support\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>PRICING</b>\n\n"
            "<b>$200 CAD/month</b>\n\n"
            "📈 ROI ANALYSIS:\n"
            "• Break even: 1-2 days\n"
            "• Month 1 profit: $2,000-3,000+\n"
            "• Cost: $200\n"
            "• NET: <b>$1,800-2,800+</b> 🚀\n\n"
            "💡 That's a 10-15x return on investment!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎁 BENEFITS:\n\n"
            "✅ Unlimited calls (vs 5/day)\n"
            "✅ All bet types (Arb + Good Odds + Middle)\n"
            "✅ Advanced tools & filters\n"
            "✅ Complete guides unlocked\n"
            "✅ Priority support\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 <b>WHAT MEMBERS SAY:</b>\n\n"
            "\"Paid for itself in 2 days. Made $4.2k first month!\"\n"
            "— Alex, Toronto\n\n"
            "\"The Last Call feature alone is worth it. Caught $800 in missed calls.\"\n"
            "— Marie, Montreal\n\n"
            "\"Free version was good. ALPHA is insane. $3k/month now.\"\n"
            "— James, Vancouver\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ <b>LIMITED TIME OFFER:</b>\n\n"
            "🎯 Upgrade in next 48 hours:\n"
            "→ First month: $150 (save $50!)\n"
            "→ Lock in this price forever\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    keyboard = [
        [InlineKeyboardButton(
            text="🚀 UPGRADE TO ALPHA NOW" if lang == 'en' else "🚀 UPGRADE VERS ALPHA MAINTENANT",
            callback_data="upgrade_premium"
        )],
        [InlineKeyboardButton(
            text="💬 Questions? Contact Support" if lang == 'en' else "💬 Questions? Contactez le Support",
            callback_data="contact_support"
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
