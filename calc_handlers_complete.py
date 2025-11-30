# Handlers complets pour le nouveau calculateur
# À intégrer dans main_new.py

@calc_router.callback_query(F.data.startswith("calc_risked_start_"))
async def calc_risked_start_handler(callback: types.CallbackQuery, state: FSMContext):
    """Start RISKED mode - ask for risk %"""
    await callback.answer()
    eid = callback.data.split('_')[3]
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    bankroll, lang, default_risk = _get_user_prefs(callback.from_user.id)
    
    # Save context for FSM
    await state.set_state(CalculatorStates.awaiting_risked_percent)
    await state.update_data(eid=eid, bankroll=bankroll, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    
    if lang == 'fr':
        msg = (
            f"⚠️ <b>MODE RISKED - AVANCÉ</b>\n\n"
            f"Dans ce mode, tu acceptes une PETITE PERTE possible pour un GROS gain potentiel.\n\n"
            f"🎯 <b>Comment ça marche?</b>\n\n"
            f"Au lieu de balancer 50/50, tu mises:\n"
            f"• Plus sur un côté (celui que tu penses va gagner)\n"
            f"• Moins sur l'autre (protection partielle)\n\n"
            f"<b>Résultat:</b>\n"
            f"✅ Si ton côté favori gagne → GROS profit\n"
            f"❌ Si l'autre gagne → Petite perte acceptée\n\n"
            f"<b>QUEL % ES-TU PRÊT À RISQUER?</b>\n\n"
            f"Exemples:\n"
            f"• 3% = Risque ~-$15, Gain potentiel ~+$80\n"
            f"• 5% = Risque ~-$25, Gain potentiel ~+$120\n"
            f"• 10% = Risque ~-$50, Gain potentiel ~+$200\n\n"
            f"<b>Entre un % (ex: 5) ou utilise les boutons:</b>"
        )
    else:
        msg = (
            f"⚠️ <b>RISKED MODE - ADVANCED</b>\n\n"
            f"In this mode, you accept a SMALL LOSS possibility for a BIG potential gain.\n\n"
            f"🎯 <b>How it works:</b>\n\n"
            f"Instead of balancing 50/50, you stake:\n"
            f"• More on one side (the one you think will win)\n"
            f"• Less on the other (partial protection)\n\n"
            f"<b>Result:</b>\n"
            f"✅ If your favored side wins → BIG profit\n"
            f"❌ If the other wins → Small accepted loss\n\n"
            f"<b>WHAT % ARE YOU WILLING TO RISK?</b>\n\n"
            f"Examples:\n"
            f"• 3% = Risk ~-$15, Potential gain ~+$80\n"
            f"• 5% = Risk ~-$25, Potential gain ~+$120\n"
            f"• 10% = Risk ~-$50, Potential gain ~+$200\n\n"
            f"<b>Enter a % (eg: 5) or use buttons:</b>"
        )
    
    # Quick buttons for common risk percentages
    kb = [
        [
            InlineKeyboardButton(text="3%", callback_data=f"calc_risk_set_{eid}|3"),
            InlineKeyboardButton(text="5%", callback_data=f"calc_risk_set_{eid}|5"),
            InlineKeyboardButton(text="10%", callback_data=f"calc_risk_set_{eid}|10"),
        ],
        [InlineKeyboardButton(text="◀️ Retour SAFE" if lang=='fr' else "◀️ Back SAFE", callback_data=f"calc_{eid}|safe")]
    ]
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("calc_risk_set_"))
async def calc_risk_set_handler(callback: types.CallbackQuery, state: FSMContext):
    """User selected risk % with button"""
    await callback.answer()
    parts = callback.data.split('|')
    eid = parts[0].split('_')[3]
    risk_pct = float(parts[1])
    
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    
    # Ask which side to favor
    outcomes = drop.get('outcomes', [])[:2]
    o1, o2 = outcomes
    
    if lang == 'fr':
        msg = f"⚠️ <b>RISKED {risk_pct}%</b>\n\n<b>Sur quel côté miser PLUS?</b>"
    else:
        msg = f"⚠️ <b>RISKED {risk_pct}%</b>\n\n<b>Which side to stake MORE?</b>"
    
    kb = [
        [InlineKeyboardButton(text=f"{get_casino_logo(o1.get('casino',''))} {o1.get('casino','')} - {o1.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|0")],
        [InlineKeyboardButton(text=f"{get_casino_logo(o2.get('casino',''))} {o2.get('casino','')} - {o2.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|1")],
        [InlineKeyboardButton(text="◀️ Retour" if lang=='fr' else "◀️ Back", callback_data=f"calc_risked_start_{eid}")]
    ]
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("calc_risk_favor_"))
async def calc_risk_favor_handler(callback: types.CallbackQuery):
    """Show RISKED calculation with chosen favor"""
    await callback.answer()
    parts = callback.data.split('|')
    eid = parts[0].split('_')[3]
    risk_pct = float(parts[1])
    favor = int(parts[2])
    
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    outcomes = drop.get('outcomes', [])[:2]
    o1, o2 = outcomes
    odds_list = [int(o1.get('odds', 0)), int(o2.get('odds', 0))]
    
    # Calculate RISKED
    res = ArbitrageCalculator.calculate_risked_stakes(bankroll, odds_list, risk_percentage=risk_pct, favor_outcome=favor)
    stakes = res.get('stakes', [0, 0])
    profits = res.get('profits', [0, 0])
    
    favored_name = o1.get('casino','') if favor == 0 else o2.get('casino','')
    other_name = o2.get('casino','') if favor == 0 else o1.get('casino','')
    
    odds1_str = f"+{odds_list[0]}" if odds_list[0] > 0 else str(odds_list[0])
    odds2_str = f"+{odds_list[1]}" if odds_list[1] > 0 else str(odds_list[1])
    
    if lang == 'fr':
        msg = (
            f"⚠️ <b>CALCUL RISKED - RISQUE {risk_pct}%</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"⚠️ Risque accepté: {risk_pct}% (${abs(profits[1-favor]):.2f})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Cote: {odds1_str}\n"
            f"💵 Miser: <b>${stakes[0]:.2f}</b>\n"
            f"📈 Si gagne → Profit: <b>${profits[0]:.2f}</b> {'🔥' if favor==0 else '😢'}\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Cote: {odds2_str}\n"
            f"💵 Miser: <b>${stakes[1]:.2f}</b>\n"
            f"📈 Si gagne → Profit: <b>${profits[1]:.2f}</b> {'🔥' if favor==1 else '😢'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Résumé RISKED:</b>\n\n"
            f"<b>SCÉNARIO 1 - {favored_name} gagne (ton favori):</b>\n"
            f"• {favored_name}: +${stakes[favor]:.2f} ✅\n"
            f"• {other_name}: -${stakes[1-favor]:.2f} ❌\n"
            f"• <b>NET: +${profits[favor]:.2f}</b> 🔥\n\n"
            f"<b>SCÉNARIO 2 - {other_name} gagne:</b>\n"
            f"• {favored_name}: -${stakes[favor]:.2f} ❌\n"
            f"• {other_name}: +${stakes[1-favor] * ArbitrageCalculator.american_to_decimal(odds_list[1-favor]):.2f} ✅\n"
            f"• <b>NET: ${profits[1-favor]:.2f}</b> 😢\n\n"
            f"⚠️ <b>C'EST PLUS DU PARI QUE DE L'ARBITRAGE!</b>\n\n"
            f"Tu paries que {favored_name} va gagner.\n"
            f"Si tu te trompes → perte de ${abs(profits[1-favor]):.2f}."
        )
    else:
        msg = (
            f"⚠️ <b>RISKED CALCULATION - RISK {risk_pct}%</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"⚠️ Accepted risk: {risk_pct}% (${abs(profits[1-favor]):.2f})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Odds: {odds1_str}\n"
            f"💵 Stake: <b>${stakes[0]:.2f}</b>\n"
            f"📈 If wins → Profit: <b>${profits[0]:.2f}</b> {'🔥' if favor==0 else '😢'}\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Odds: {odds2_str}\n"
            f"💵 Stake: <b>${stakes[1]:.2f}</b>\n"
            f"📈 If wins → Profit: <b>${profits[1]:.2f}</b> {'🔥' if favor==1 else '😢'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>RISKED Summary:</b>\n\n"
            f"<b>SCENARIO 1 - {favored_name} wins (your favorite):</b>\n"
            f"• {favored_name}: +${stakes[favor]:.2f} ✅\n"
            f"• {other_name}: -${stakes[1-favor]:.2f} ❌\n"
            f"• <b>NET: +${profits[favor]:.2f}</b> 🔥\n\n"
            f"<b>SCENARIO 2 - {other_name} wins:</b>\n"
            f"• {favored_name}: -${stakes[favor]:.2f} ❌\n"
            f"• {other_name}: +${stakes[1-favor] * ArbitrageCalculator.american_to_decimal(odds_list[1-favor]):.2f} ✅\n"
            f"• <b>NET: ${profits[1-favor]:.2f}</b> 😢\n\n"
            f"⚠️ <b>THIS IS MORE BETTING THAN ARBITRAGE!</b>\n\n"
            f"You're betting that {favored_name} will win.\n"
            f"If you're wrong → loss of ${abs(profits[1-favor]):.2f}."
        )
    
    # Buttons: adjust %, swap favor, back
    kb = [
        [
            InlineKeyboardButton(text="-1%", callback_data=f"calc_risk_favor_{eid}|{max(risk_pct-1, 0.5)}|{favor}"),
            InlineKeyboardButton(text=f"{risk_pct}%", callback_data="noop"),
            InlineKeyboardButton(text="+1%", callback_data=f"calc_risk_favor_{eid}|{risk_pct+1}|{favor}"),
        ],
        [InlineKeyboardButton(text="🔄 Swap favor" if lang=='en' else "🔄 Inverser favori", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|{1-favor}")],
        [InlineKeyboardButton(text="✅ Retour SAFE" if lang=='fr' else "✅ Back SAFE", callback_data=f"calc_{eid}|safe")],
        [InlineKeyboardButton(text="◀️ Retour menu" if lang=='fr' else "◀️ Back menu", callback_data=f"calc_{eid}|menu")],
    ]
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("calc_changeodds_"))
async def calc_changeodds_handler(callback: types.CallbackQuery, state: FSMContext):
    """Start change odds flow"""
    await callback.answer()
    eid = callback.data.split('_')[2]
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    outcomes = drop.get('outcomes', [])[:2]
    o1, o2 = outcomes
    
    # Save context
    await state.set_state(CalculatorStates.awaiting_odds_side1)
    await state.update_data(eid=eid, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    
    lang = _get_user_prefs(callback.from_user.id)[1]
    
    if lang == 'fr':
        msg = (
            f"🔄 <b>CHANGER LES COTES</b>\n\n"
            f"Entre les nouvelles cotes:\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Cote actuelle: {'+' if o1.get('odds',0)>0 else ''}{o1.get('odds',0)}\n"
            f"<b>Nouvelle cote?</b> (ex: +105, -110)"
        )
    else:
        msg = (
            f"🔄 <b>CHANGE ODDS</b>\n\n"
            f"Enter new odds:\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Current odds: {'+' if o1.get('odds',0)>0 else ''}{o1.get('odds',0)}\n"
            f"<b>New odds?</b> (eg: +105, -110)"
        )
    
    kb = [[InlineKeyboardButton(text="◀️ Annuler" if lang=='fr' else "◀️ Cancel", callback_data=f"calc_{eid}|safe")]]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.message(CalculatorStates.awaiting_odds_side1)
async def handle_odds_side1(message: types.Message, state: FSMContext):
    """Handle first odds input"""
    text = (message.text or "").strip()
    try:
        # Parse American odds (+150 or -110)
        odds1 = int(text.replace('+','').replace(' ',''))
    except Exception:
        await message.answer("❌ Cote invalide. Ex: +105 ou -110")
        return
    
    data = await state.get_data()
    eid = data.get('eid')
    drop = _get_drop(eid)
    
    if not drop:
        await message.answer("❌ Drop expiré")
        await state.clear()
        return
    
    outcomes = drop.get('outcomes', [])[:2]
    o2 = outcomes[1]
    
    # Update state and ask for second odds
    await state.update_data(odds1=odds1)
    await state.set_state(CalculatorStates.awaiting_odds_side2)
    
    lang = _get_user_prefs(message.from_user.id)[1]
    
    if lang == 'fr':
        msg = (
            f"✅ Parfait! {'+' if odds1>0 else ''}{odds1} pour le premier côté.\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>{o2.get('casino','')}</b> - Cote actuelle: {'+' if o2.get('odds',0)>0 else ''}{o2.get('odds',0)}\n"
            f"<b>Nouvelle cote?</b> (ex: +130, -115)"
        )
    else:
        msg = (
            f"✅ Perfect! {'+' if odds1>0 else ''}{odds1} for first side.\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>{o2.get('casino','')}</b> - Current odds: {'+' if o2.get('odds',0)>0 else ''}{o2.get('odds',0)}\n"
            f"<b>New odds?</b> (eg: +130, -115)"
        )
    
    await message.answer(msg, parse_mode=ParseMode.HTML)


@calc_router.message(CalculatorStates.awaiting_odds_side2)
async def handle_odds_side2(message: types.Message, state: FSMContext):
    """Handle second odds input and recalculate"""
    text = (message.text or "").strip()
    try:
        odds2 = int(text.replace('+','').replace(' ',''))
    except Exception:
        await message.answer("❌ Cote invalide. Ex: +130 ou -115")
        return
    
    data = await state.get_data()
    eid = data.get('eid')
    odds1 = data.get('odds1')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    
    drop = _get_drop(eid)
    if not drop:
        await message.answer("❌ Drop expiré")
        await state.clear()
        return
    
    bankroll, lang, _ = _get_user_prefs(message.from_user.id)
    
    # Calculate with new odds
    new_odds = [odds1, odds2]
    res = ArbitrageCalculator.calculate_safe_stakes(bankroll, new_odds)
    stakes = res.get('stakes', [0, 0])
    returns = res.get('returns', [0, 0])
    profit = res.get('profit', 0)
    roi_pct = (profit / bankroll * 100) if bankroll > 0 else 0
    
    outcomes = drop.get('outcomes', [])[:2]
    o1, o2 = outcomes
    
    odds1_str = f"+{new_odds[0]}" if new_odds[0] > 0 else str(new_odds[0])
    odds2_str = f"+{new_odds[1]}" if new_odds[1] > 0 else str(new_odds[1])
    
    if lang == 'fr':
        msg = (
            f"✅ <b>NOUVEAU CALCUL</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"✅ Profit: <b>${profit:.2f}</b> ({roi_pct:.2f}%)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Cote: {odds1_str}\n"
            f"💵 Miser: <b>${stakes[0]:.2f}</b>\n"
            f"📈 Si gagne → Retour: <b>${returns[0]:.2f}</b>\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Cote: {odds2_str}\n"
            f"💵 Miser: <b>${stakes[1]:.2f}</b>\n"
            f"📈 Si gagne → Retour: <b>${returns[1]:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = (
            f"✅ <b>NEW CALCULATION</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"✅ Profit: <b>${profit:.2f}</b> ({roi_pct:.2f}%)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Odds: {odds1_str}\n"
            f"💵 Stake: <b>${stakes[0]:.2f}</b>\n"
            f"📈 If wins → Return: <b>${returns[0]:.2f}</b>\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Odds: {odds2_str}\n"
            f"💵 Stake: <b>${stakes[1]:.2f}</b>\n"
            f"📈 If wins → Return: <b>${returns[1]:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    kb = [[InlineKeyboardButton(text="◀️ Retour" if lang=='fr' else "◀️ Back", callback_data=f"calc_{eid}|menu")]]
    
    # Send new message
    await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.clear()


# Noop handler for buttons that don't do anything (like the current % display)
@calc_router.callback_query(F.data == "noop")
async def noop_handler(callback: types.CallbackQuery):
    await callback.answer()
