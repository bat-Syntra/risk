"""
Handler for Simulation & Risk button
Shows detailed analysis for Middle and Good EV alerts
"""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data.startswith("sim_"))
async def simulation_handler(callback: types.CallbackQuery):
    """Show detailed simulation and risk analysis"""
    await callback.answer()
    
    try:
        eid = callback.data.replace("sim_", "")
        
        # Get drop from DB instead of importing main_new (avoid circular import)
        from database import SessionLocal
        from models.drop_event import DropEvent
        from models.user import User
        
        db = SessionLocal()
        try:
            # Try to get drop from database by event_id
            drop_event = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
            
            # If not found by event_id, try by numeric ID
            if not drop_event:
                try:
                    numeric_id = int(eid)
                    drop_event = db.query(DropEvent).filter(DropEvent.id == numeric_id).first()
                except ValueError:
                    pass
            
            if not drop_event:
                await callback.answer("❌ Drop expiré" if callback.from_user.language_code == 'fr' else "❌ Drop expired", show_alert=True)
                return
            
            drop = drop_event.payload
            
            # Get user preferences
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            if user:
                bankroll = user.default_bankroll or 550.0
                lang = user.language or 'en'
            else:
                bankroll = 550.0
                lang = 'en'
        finally:
            db.close()
        
        if not drop:
            await callback.answer("❌ Drop expiré" if callback.from_user.language_code == 'fr' else "❌ Drop expired", show_alert=True)
            return
        
        bet_type = drop.get('bet_type', 'arbitrage')
        
        if bet_type == 'middle':
            msg = _format_middle_simulation(drop, bankroll, lang)
        elif bet_type == 'good_ev':
            msg = _format_goodev_simulation(drop, bankroll, lang)
        else:
            await callback.answer("❌ Type non supporté", show_alert=True)
            return
        
        kb = [[InlineKeyboardButton(
            text=("◀️ Retour à l'alerte" if lang=='fr' else "◀️ Back to alert"),
            callback_data=f"back_to_main_{eid}"
        )]]
        
        await callback.message.edit_text(
            msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        
    except Exception as e:
        logger.error(f"Error in simulation_handler: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


def _format_middle_simulation(drop: dict, bankroll: float, lang: str) -> str:
    """Format detailed Middle simulation"""
    # Extract data
    match = drop.get('match', '')
    market = drop.get('market', '')
    
    # Reconstruct side_a and side_b from outcomes (same as format_middle_message)
    outcomes = drop.get('outcomes', [])
    if len(outcomes) < 2:
        return "❌ Données incomplètes"
    
    o1, o2 = outcomes[0], outcomes[1]
    
    def _extract_line(sel: str) -> str:
        if not sel:
            return "0"
        parts = str(sel).split()
        for p in reversed(parts):
            try:
                float(p.replace('+', '').replace('−', '-'))
                return p
            except Exception:
                continue
        return "0"
    
    side_a = {
        'bookmaker': o1.get('casino') or o1.get('bookmaker', ''),
        'selection': o1.get('outcome', ''),
        'line': _extract_line(o1.get('outcome', '')),
        'odds': str(o1.get('odds', '0')),
        'market': market,
    }
    side_b = {
        'bookmaker': o2.get('casino') or o2.get('bookmaker', ''),
        'selection': o2.get('outcome', ''),
        'line': _extract_line(o2.get('outcome', '')),
        'odds': str(o2.get('odds', '0')),
        'market': market,
    }
    
    # Use classify_middle_type for accurate calculations (same as format_middle_message)
    from utils.middle_calculator import classify_middle_type
    from utils.oddsjam_formatters import describe_middle_zone
    
    cls = classify_middle_type(side_a, side_b, bankroll)
    
    total_stake = cls['total_stake']
    profit_a_only = cls['profit_scenario_1']
    profit_b_only = cls['profit_scenario_3']
    profit_middle = cls['profit_scenario_2']
    middle_prob = cls['middle_prob']
    min_profit = min(profit_a_only, profit_b_only)
    
    # Get zone description
    zone_desc = describe_middle_zone({
        'market': market,
        'side_a': side_a,
        'side_b': side_b,
    })
    
    times_middle = int(round(middle_prob * 100))
    times_no_middle = 100 - times_middle
    net_100 = times_middle * profit_middle + times_no_middle * min_profit
    ev_profit = (middle_prob * profit_middle) + ((1 - middle_prob) * min_profit)
    
    if lang == 'fr':
        msg = (
            f"📊 <b>SIMULATION & ANALYSE - MIDDLE</b>\n\n"
            f"🏀 <b>{match}</b>\n"
            f"📊 {market}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 <b>COMMENT ÇA MARCHE?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 Tu paries sur 2 lignes OPPOSÉES\n"
            f"📌 Les deux paris peuvent gagner SIMULTANÉMENT\n"
            f"📌 Si le score tombe dans la zone magique → 💰 JACKPOT!\n\n"
            f"<b>Exemple visuel:</b>\n"
            f"┌─────────────────────────┐\n"
            f"│ Score final: {zone_desc}      │\n"
            f"│ {'█' * min(int(middle_prob*20), 20)} {int(middle_prob*100)}% chance │\n"
            f"│ = LES DEUX GAGNENT! 🎰  │\n"
            f"└─────────────────────────┘\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>SIMULATEUR: 100 MIDDLES</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Si tu fais ce middle 100 fois:\n\n"
            f"🎰 <b>Jackpots: ~{times_middle} fois</b>\n"
            f"   → Profit: ${profit_middle * times_middle:,.0f}\n\n"
            f"💵 <b>Pas jackpot: ~{times_no_middle} fois</b>\n"
            f"   → Profit: ${min_profit * times_no_middle:,.0f}\n\n"
            f"💰 <b>TOTAL NET sur 100 paris:</b>\n"
            f"   <b>${net_100:+,.0f}</b> 🚀\n\n"
            f"📈 ROI moyen par pari: {(ev_profit/total_stake*100):.1f}%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <b>CONSEILS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Profit garanti minimum: ${min_profit:+.2f}\n"
            f"🛡️ Risque: ZÉRO (c'est un arbitrage!)\n"
            f"🎰 Bonus jackpot possible: ${profit_middle:+.2f}\n\n"
            f"⚠️ <b>Les cotes peuvent changer!</b>\n"
            f"Toujours vérifier avant de parier.\n"
        )
    else:
        msg = (
            f"📊 <b>SIMULATION & ANALYSIS - MIDDLE</b>\n\n"
            f"🏀 <b>{match}</b>\n"
            f"📊 {market}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 <b>HOW IT WORKS?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 You bet on 2 OPPOSITE lines\n"
            f"📌 Both bets can win SIMULTANEOUSLY\n"
            f"📌 If score lands in magic zone → 💰 JACKPOT!\n\n"
            f"<b>Visual example:</b>\n"
            f"┌─────────────────────────┐\n"
            f"│ Final score: {zone_desc}      │\n"
            f"│ {'█' * min(int(middle_prob*20), 20)} {int(middle_prob*100)}% chance │\n"
            f"│ = BOTH WIN! 🎰          │\n"
            f"└─────────────────────────┘\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>SIMULATOR: 100 MIDDLES</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"If you do this middle 100 times:\n\n"
            f"🎰 <b>Jackpots: ~{times_middle} times</b>\n"
            f"   → Profit: ${profit_middle * times_middle:,.0f}\n\n"
            f"💵 <b>No jackpot: ~{times_no_middle} times</b>\n"
            f"   → Profit: ${min_profit * times_no_middle:,.0f}\n\n"
            f"💰 <b>TOTAL NET over 100 bets:</b>\n"
            f"   <b>${net_100:+,.0f}</b> 🚀\n\n"
            f"📈 Average ROI per bet: {(ev_profit/total_stake*100):.1f}%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <b>TIPS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Minimum guaranteed profit: ${min_profit:+.2f}\n"
            f"🛡️ Risk: ZERO (it's an arbitrage!)\n"
            f"🎰 Possible jackpot bonus: ${profit_middle:+.2f}\n\n"
            f"⚠️ <b>Odds can change!</b>\n"
            f"Always verify before betting.\n"
        )
    
    return msg


def _format_goodev_simulation(drop: dict, bankroll: float, lang: str) -> str:
    """Format detailed Good EV simulation with risk management"""
    # Extract data
    match = drop.get('match', '')
    market = drop.get('market', '')
    outcomes = drop.get('outcomes', [])
    if not outcomes:
        return "❌ Données incomplètes"
    
    o1 = outcomes[0]
    try:
        odds = int(o1.get('odds', 0))
    except (ValueError, TypeError):
        odds = 100
    
    # Calculate EV stats
    from utils.oddsjam_parser import american_to_decimal
    decimal_odds = american_to_decimal(odds)
    true_prob = drop.get('true_probability', 0.5)
    ev_percent = drop.get('ev_percent', 5.0)
    
    # Recommended stake (Kelly fraction)
    kelly_fraction = 0.25
    edge = (decimal_odds * true_prob) - 1
    if edge > 0:
        kelly_stake = bankroll * (edge / (decimal_odds - 1)) * kelly_fraction
        kelly_stake = min(kelly_stake, bankroll * 0.05)  # Max 5% of bankroll
    else:
        kelly_stake = bankroll * 0.01
    
    profit_if_win = kelly_stake * (decimal_odds - 1)
    loss_if_lose = kelly_stake
    
    # Simulation over 10 bets
    times_win = int(round(true_prob * 10))
    times_lose = 10 - times_win
    net_10 = (times_win * profit_if_win) - (times_lose * loss_if_lose)
    
    # Long term
    ev_per_bet = (true_prob * profit_if_win) - ((1 - true_prob) * loss_if_lose)
    net_100 = ev_per_bet * 100
    
    # Kelly bankroll recommendation
    min_bankroll_kelly = kelly_stake / kelly_fraction
    
    if lang == 'fr':
        ev_quality = '🔥 EXCELLENT' if ev_percent >= 15 else '✅ BON' if ev_percent >= 10 else '⚠️ MOYEN' if ev_percent >= 5 else '❌ FAIBLE'
        msg = (
            f"📊 <b>SIMULATION & RISK - GOOD ODDS</b>\n\n"
            f"🏀 <b>{match}</b>\n"
            f"📊 {market}\n\n"
            f"💎 <b>QUALITÉ EV: {ev_quality} ({ev_percent:.1f}%)</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 <b>COMMENT ÇA MARCHE?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 Tu trouves des cotes MEILLEURES que le vrai %\n"
            f"📌 Exemple: Ta cote dit 50%, mais le vrai % est ~{int(true_prob*100)}%\n"
            f"📌 Sur le long terme = PROFIT GARANTI\n\n"
            f"⚠️ <b>CE N'EST PAS UN ARBITRAGE!</b>\n"
            f"→ Tu peux perdre plusieurs paris d'affilée\n"
            f"→ Le profit vient sur 50-100+ paris\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>SIMULATION: 10 PARIS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>💰 Mise par pari: ${kelly_stake:.0f}</b>\n"
            f"<b>💵 Total misé: ${kelly_stake * 10:.0f}</b>\n\n"
            f"✅ <b>Tu GAGNES ~{times_win} fois ({int(true_prob*100)}%):</b>\n"
            f"   → Profit: <b>${times_win * profit_if_win:.0f}</b> 🎉\n\n"
            f"❌ <b>Tu PERDS ~{times_lose} fois ({int((1-true_prob)*100)}%):</b>\n"
            f"   → Perte: <b>${times_lose * loss_if_lose:.0f}</b> 😢\n\n"
            f"💰 <b>RÉSULTAT NET: ${net_10:+.0f}</b>\n"
            f"📈 <b>ROI: {(net_10/(kelly_stake*10)*100):+.1f}%</b>\n\n"
            f"💡 <b>Pourquoi tu gagnes?</b>\n"
            f"Tu gagnes {int(true_prob*100)}% du temps au lieu de 50%!\n"
            f"Les {int((true_prob-0.5)*100)}% en plus = ton edge.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>LONG TERME (100 PARIS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>💵 Total misé: ${kelly_stake * 100:,.0f}</b>\n"
            f"<b>💰 Profit attendu: ${net_100:+,.0f}</b>\n"
            f"<b>📈 ROI moyen: {ev_percent:.1f}%</b>\n\n"
            f"⚡ Sur 100 paris, le profit est quasi-garanti!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>GESTION DU RISQUE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>🎯 Ta mise recommandée: ${kelly_stake:.0f}/pari</b>\n"
            f"<b>💼 Bankroll minimum: ${min_bankroll_kelly:,.0f}</b>\n"
            f"<b>🎲 Paris minimum: 50-100</b>\n\n"
            f"⚠️ <b>COURT TERME (10-20 paris):</b>\n"
            f"→ Tu peux être négatif (NORMAL!)\n"
            f"→ La variance joue contre toi\n"
            f"→ Ne panique pas, continue!\n\n"
            f"✅ <b>LONG TERME (100+ paris):</b>\n"
            f"→ Profit quasi-garanti mathématiquement\n"
            f"→ La variance s'annule\n"
            f"→ L'EV de {ev_percent:.1f}% se réalise\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>C'EST POUR QUI?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'✅ PARFAIT pour toi!' if ev_percent >= 12 else '⚠️ ACCEPTABLE si expérimenté' if ev_percent >= 8 else '❌ ÉVITE si débutant'}\n\n"
            f"<b>Tu DOIS avoir:</b>\n"
            f"• {'✅' if ev_percent >= 12 else '⚠️'} Expérience: 100+ paris\n"
            f"• {'✅' if min_bankroll_kelly <= 2000 else '⚠️'} Bankroll: >${min_bankroll_kelly:,.0f}\n"
            f"• ✅ Patience: accepter les pertes temporaires\n"
            f"• ✅ Discipline: ne pas paniquer\n\n"
            f"💡 <b>Conseil:</b> {'Fonce!' if ev_percent >= 12 else 'Attends un meilleur EV (12%+)' if ev_percent < 10 else 'OK si tu es patient'}\n"
        )
    else:
        ev_quality = '🔥 EXCELLENT' if ev_percent >= 15 else '✅ GOOD' if ev_percent >= 10 else '⚠️ AVERAGE' if ev_percent >= 5 else '❌ LOW'
        msg = (
            f"📊 <b>SIMULATION & RISK - GOOD ODDS</b>\n\n"
            f"🏀 <b>{match}</b>\n"
            f"📊 {market}\n\n"
            f"💎 <b>EV QUALITY: {ev_quality} ({ev_percent:.1f}%)</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎓 <b>HOW IT WORKS?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 You find odds BETTER than the true %\n"
            f"📌 Example: Your odds say 50%, but true % is ~{int(true_prob*100)}%\n"
            f"📌 Long term = GUARANTEED PROFIT\n\n"
            f"⚠️ <b>THIS IS NOT AN ARBITRAGE!</b>\n"
            f"→ You can lose several bets in a row\n"
            f"→ Profit comes over 50-100+ bets\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>SIMULATION: 10 BETS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>💰 Stake per bet: ${kelly_stake:.0f}</b>\n"
            f"<b>💵 Total staked: ${kelly_stake * 10:.0f}</b>\n\n"
            f"✅ <b>You WIN ~{times_win} times ({int(true_prob*100)}%):</b>\n"
            f"   → Profit: <b>${times_win * profit_if_win:.0f}</b> 🎉\n\n"
            f"❌ <b>You LOSE ~{times_lose} times ({int((1-true_prob)*100)}%):</b>\n"
            f"   → Loss: <b>${times_lose * loss_if_lose:.0f}</b> 😢\n\n"
            f"💰 <b>NET RESULT: ${net_10:+.0f}</b>\n"
            f"📈 <b>ROI: {(net_10/(kelly_stake*10)*100):+.1f}%</b>\n\n"
            f"💡 <b>Why do you win?</b>\n"
            f"You win {int(true_prob*100)}% of the time instead of 50%!\n"
            f"The extra {int((true_prob-0.5)*100)}% = your edge.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>LONG TERM (100 BETS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>💵 Total staked: ${kelly_stake * 100:,.0f}</b>\n"
            f"<b>💰 Expected profit: ${net_100:+,.0f}</b>\n"
            f"<b>📈 Average ROI: {ev_percent:.1f}%</b>\n\n"
            f"⚡ Over 100 bets, profit is almost guaranteed!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>RISK MANAGEMENT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>🎯 Your recommended stake: ${kelly_stake:.0f}/bet</b>\n"
            f"<b>💼 Minimum bankroll: ${min_bankroll_kelly:,.0f}</b>\n"
            f"<b>🎲 Minimum bets: 50-100</b>\n\n"
            f"⚠️ <b>SHORT TERM (10-20 bets):</b>\n"
            f"→ You can be negative (NORMAL!)\n"
            f"→ Variance plays against you\n"
            f"→ Don't panic, keep going!\n\n"
            f"✅ <b>LONG TERM (100+ bets):</b>\n"
            f"→ Profit almost mathematically guaranteed\n"
            f"→ Variance cancels out\n"
            f"→ The {ev_percent:.1f}% EV realizes\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>WHO IS THIS FOR?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'✅ PERFECT for you!' if ev_percent >= 12 else '⚠️ ACCEPTABLE if experienced' if ev_percent >= 8 else '❌ AVOID if beginner'}\n\n"
            f"<b>You MUST have:</b>\n"
            f"• {'✅' if ev_percent >= 12 else '⚠️'} Experience: 100+ bets\n"
            f"• {'✅' if min_bankroll_kelly <= 2000 else '⚠️'} Bankroll: >${min_bankroll_kelly:,.0f}\n"
            f"• ✅ Patience: accept temporary losses\n"
            f"• ✅ Discipline: don't panic\n\n"
            f"💡 <b>Advice:</b> {'Go for it!' if ev_percent >= 12 else 'Wait for better EV (12%+)' if ev_percent < 10 else 'OK if patient'}\n"
        )
    
    return msg
