"""
Add Bet Flow - Manual bet entry with step-by-step guidance
"""
import logging
from datetime import datetime, timedelta, date
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User
from models.bet import UserBet, DailyStats
from models.drop_event import DropEvent

router = Router()
logger = logging.getLogger(__name__)


class AddBetStates(StatesGroup):
    """FSM States for adding a bet"""
    select_type = State()
    select_sport = State()
    enter_match = State()
    select_date = State()
    enter_custom_date = State()
    enter_stake = State()
    select_result = State()
    enter_profit = State()
    confirm_bet = State()


@router.callback_query(F.data == "add_bet")
async def start_add_bet(callback: types.CallbackQuery, state: FSMContext):
    """Start the add bet flow"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        if lang == 'fr':
            text = (
                "➕ <b>NOUVEAU BET</b>\n\n"
                "Quel type de bet veux-tu ajouter?\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            text = (
                "➕ <b>NEW BET</b>\n\n"
                "What type of bet do you want to add?\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="⚖️ Arbitrage",
                callback_data="bettype_arbitrage"
            )],
            [InlineKeyboardButton(
                text="💎 Good +EV",
                callback_data="bettype_good_ev"
            )],
            [InlineKeyboardButton(
                text="🎯 Middle Bet",
                callback_data="bettype_middle"
            )],
            [InlineKeyboardButton(
                text="❌ Annuler" if lang == 'fr' else "❌ Cancel",
                callback_data="cancel_add_bet"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Initialize bet data
        await state.update_data(bet_data={})
        await state.set_state(AddBetStates.select_type)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("bettype_"), AddBetStates.select_type)
async def select_bet_type(callback: types.CallbackQuery, state: FSMContext):
    """Select bet type"""
    await callback.answer()
    
    bet_type = callback.data.replace("bettype_", "")
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Save bet type
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['type'] = bet_type
        await state.update_data(bet_data=bet_data)
        
        type_names = {
            'arbitrage': '⚖️ Arbitrage',
            'good_ev': '💎 Good +EV',
            'middle': '🎯 Middle Bet'
        }
        
        # Now ask for sport
        if lang == 'fr':
            text = (
                f"🏀 <b>SPORT</b>\n\n"
                f"Type: {type_names[bet_type]}\n\n"
                f"Quel sport?"
            )
        else:
            text = (
                f"🏀 <b>SPORT</b>\n\n"
                f"Type: {type_names[bet_type]}\n\n"
                f"Which sport?"
            )
        
        keyboard = [
            [
                InlineKeyboardButton(text="🏀 NBA", callback_data="sport_NBA"),
                InlineKeyboardButton(text="🏒 NHL", callback_data="sport_NHL")
            ],
            [
                InlineKeyboardButton(text="🏈 NFL", callback_data="sport_NFL"),
                InlineKeyboardButton(text="⚾ MLB", callback_data="sport_MLB")
            ],
            [
                InlineKeyboardButton(text="🥊 UFC", callback_data="sport_UFC"),
                InlineKeyboardButton(text="⚽ Soccer", callback_data="sport_Soccer")
            ],
            [
                InlineKeyboardButton(text="🎾 Tennis", callback_data="sport_Tennis"),
                InlineKeyboardButton(text="⛳ Golf", callback_data="sport_Golf")
            ],
            [
                InlineKeyboardButton(text="🎯 Autre" if lang == 'fr' else "🎯 Other", callback_data="sport_Other")
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                    callback_data="add_bet"
                )
            ]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AddBetStates.select_sport)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("sport_"), AddBetStates.select_sport)
async def select_sport(callback: types.CallbackQuery, state: FSMContext):
    """Select sport and ask for match name"""
    await callback.answer()
    
    sport = callback.data.replace("sport_", "")
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Save sport
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['sport'] = sport
        await state.update_data(bet_data=bet_data)
        
        type_names = {
            'arbitrage': '⚖️ Arbitrage',
            'good_ev': '💎 Good +EV',
            'middle': '🎯 Middle Bet'
        }
        
        # Ask for match name
        if lang == 'fr':
            text = (
                f"🏈 <b>MATCH / JOUEUR</b>\n\n"
                f"Type: {type_names[bet_data['type']]}\n"
                f"Sport: {sport}\n\n"
                f"Envoie le nom du match ou du joueur:\n\n"
                f"<b>Exemples:</b>\n"
                f"• Lakers vs Celtics\n"
                f"• Maple Leafs vs Canadiens\n"
                f"• LeBron James\n"
                f"• Patrick Mahomes\n\n"
                f"Écris le nom:"
            )
        else:
            text = (
                f"🏈 <b>MATCH / PLAYER</b>\n\n"
                f"Type: {type_names[bet_data['type']]}\n"
                f"Sport: {sport}\n\n"
                f"Send the match or player name:\n\n"
                f"<b>Examples:</b>\n"
                f"• Lakers vs Celtics\n"
                f"• Maple Leafs vs Canadiens\n"
                f"• LeBron James\n"
                f"• Patrick Mahomes\n\n"
                f"Type the name:"
            )
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML
        )
        
        await state.set_state(AddBetStates.enter_match)
        
    finally:
        db.close()


@router.message(AddBetStates.enter_match)
async def enter_match_name(message: types.Message, state: FSMContext):
    """Receive match name and proceed to date selection"""
    user_id = message.from_user.id
    match_name = message.text.strip()
    
    # Delete user's message
    try:
        await message.delete()
    except:
        pass
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Save match name
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['match'] = match_name
        await state.update_data(bet_data=bet_data)
        
        type_names = {
            'arbitrage': '⚖️ Arbitrage',
            'good_ev': '💎 Good +EV',
            'middle': '🎯 Middle Bet'
        }
        
        # Now ask for date
        if lang == 'fr':
            text = (
                f"📅 <b>DATE DU BET</b>\n\n"
                f"Type: {type_names[bet_data['type']]}\n"
                f"Sport: {bet_data['sport']}\n"
                f"Match: {match_name}\n\n"
                f"Quand as-tu placé ce bet?"
            )
        else:
            text = (
                f"📅 <b>BET DATE</b>\n\n"
                f"Type: {type_names[bet_data['type']]}\n"
                f"Sport: {bet_data['sport']}\n"
                f"Match: {match_name}\n\n"
                f"When did you place this bet?"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="📅 Aujourd'hui" if lang == 'fr' else "📅 Today",
                callback_data="date_today"
            )],
            [InlineKeyboardButton(
                text="📆 Hier" if lang == 'fr' else "📆 Yesterday",
                callback_data="date_yesterday"
            )],
            [InlineKeyboardButton(
                text="🗓️ Date personnalisée" if lang == 'fr' else "🗓️ Custom date",
                callback_data="date_custom"
            )],
            [InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="add_bet"
            )]
        ]
        
        # Send new message since we deleted the user's message
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AddBetStates.select_date)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("date_"), AddBetStates.select_date)
async def select_date(callback: types.CallbackQuery, state: FSMContext):
    """Select bet date"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        
        if callback.data == "date_today":
            bet_data['date'] = date.today()
        elif callback.data == "date_yesterday":
            bet_data['date'] = date.today() - timedelta(days=1)
        elif callback.data == "date_custom":
            if lang == 'fr':
                text = (
                    "📅 <b>DATE PERSONNALISÉE</b>\n\n"
                    "Envoie la date au format:\n"
                    "<code>YYYY-MM-DD</code>\n\n"
                    "Exemple: <code>2025-11-25</code>\n"
                    "ou <code>25/11/2025</code>"
                )
            else:
                text = (
                    "📅 <b>CUSTOM DATE</b>\n\n"
                    "Send the date in format:\n"
                    "<code>YYYY-MM-DD</code>\n\n"
                    "Example: <code>2025-11-25</code>\n"
                    "or <code>25/11/2025</code>"
                )
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
            await state.set_state(AddBetStates.enter_custom_date)
            return
        
        await state.update_data(bet_data=bet_data)
        await ask_for_stake(callback, state, lang, bet_data)
        
    finally:
        db.close()


@router.message(AddBetStates.enter_custom_date)
async def receive_custom_date(message: types.Message, state: FSMContext):
    """Receive custom date from user"""
    date_text = message.text.strip()
    
    user_id = message.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Try parsing date
        bet_date = None
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                bet_date = datetime.strptime(date_text, fmt).date()
                break
            except ValueError:
                continue
        
        if not bet_date:
            error_msg = "❌ Format invalide! Utilise: 2025-11-25 ou 25/11/2025" if lang == 'fr' else "❌ Invalid format! Use: 2025-11-25 or 25/11/2025"
            await message.answer(error_msg)
            return
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['date'] = bet_date
        await state.update_data(bet_data=bet_data)
        
        # Ask for stake
        if lang == 'fr':
            text = (
                f"💰 <b>MONTANT TOTAL MISÉ</b>\n\n"
                f"Date: {bet_date.strftime('%Y-%m-%d')}\n\n"
                f"Combien as-tu misé au total?\n\n"
                f"Exemple: <code>750</code> ou <code>1500.50</code>\n\n"
                f"👇 Envoie juste le montant"
            )
        else:
            text = (
                f"💰 <b>TOTAL AMOUNT STAKED</b>\n\n"
                f"Date: {bet_date.strftime('%Y-%m-%d')}\n\n"
                f"How much did you stake in total?\n\n"
                f"Example: <code>750</code> or <code>1500.50</code>\n\n"
                f"👇 Just send the amount"
            )
        
        await message.answer(text, parse_mode=ParseMode.HTML)
        await state.set_state(AddBetStates.enter_stake)
        
    finally:
        db.close()


async def ask_for_stake(callback: types.CallbackQuery, state: FSMContext, lang: str, bet_data: dict):
    """Ask for stake amount"""
    bet_date = bet_data['date']
    
    if lang == 'fr':
        text = (
            f"💰 <b>MONTANT TOTAL MISÉ</b>\n\n"
            f"Date: {bet_date.strftime('%Y-%m-%d')}\n\n"
            f"Combien as-tu misé au total?\n\n"
            f"Exemple: <code>750</code> ou <code>1500.50</code>\n\n"
            f"👇 Envoie juste le montant"
        )
    else:
        text = (
            f"💰 <b>TOTAL AMOUNT STAKED</b>\n\n"
            f"Date: {bet_date.strftime('%Y-%m-%d')}\n\n"
            f"How much did you stake in total?\n\n"
            f"Example: <code>750</code> or <code>1500.50</code>\n\n"
            f"👇 Just send the amount"
        )
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await state.set_state(AddBetStates.enter_stake)


@router.message(AddBetStates.enter_stake)
async def receive_stake(message: types.Message, state: FSMContext):
    """Receive stake amount"""
    stake_text = message.text.strip().replace('$', '').replace(',', '')
    
    user_id = message.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        try:
            stake = float(stake_text)
            if stake <= 0:
                raise ValueError
        except ValueError:
            error_msg = "❌ Montant invalide! Entre un chiffre positif." if lang == 'fr' else "❌ Invalid amount! Enter a positive number."
            await message.answer(error_msg)
            return
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['stake'] = stake
        await state.update_data(bet_data=bet_data)
        
        # Ask for result
        if lang == 'fr':
            text = (
                f"🎲 <b>RÉSULTAT DU BET</b>\n\n"
                f"Montant misé: ${stake:,.2f}\n\n"
                f"Le bet est-il gagné ou perdu?"
            )
        else:
            text = (
                f"🎲 <b>BET RESULT</b>\n\n"
                f"Staked: ${stake:,.2f}\n\n"
                f"Did you win or lose?"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="✅ Gagné" if lang == 'fr' else "✅ Won",
                callback_data="result_won"
            )],
            [InlineKeyboardButton(
                text="❌ Perdu" if lang == 'fr' else "❌ Lost",
                callback_data="result_lost"
            )],
            [InlineKeyboardButton(
                text="⏳ En attente" if lang == 'fr' else "⏳ Pending",
                callback_data="result_pending"
            )]
        ]
        
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AddBetStates.select_result)
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("result_"), AddBetStates.select_result)
async def select_result(callback: types.CallbackQuery, state: FSMContext):
    """Select bet result"""
    await callback.answer()
    
    result = callback.data.replace("result_", "")
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['result'] = result
        
        if result == 'won':
            # Ask for profit
            if lang == 'fr':
                text = (
                    f"📈 <b>PROFIT RÉALISÉ</b>\n\n"
                    f"Montant misé: ${bet_data['stake']:,.2f}\n\n"
                    f"Combien as-tu gagné? (profit net)\n\n"
                    f"Exemple: <code>20.43</code> ou <code>233.50</code>\n\n"
                    f"👇 Envoie juste le montant"
                )
            else:
                text = (
                    f"📈 <b>REALIZED PROFIT</b>\n\n"
                    f"Staked: ${bet_data['stake']:,.2f}\n\n"
                    f"How much did you win? (net profit)\n\n"
                    f"Example: <code>20.43</code> or <code>233.50</code>\n\n"
                    f"👇 Just send the amount"
                )
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
            await state.update_data(bet_data=bet_data)
            await state.set_state(AddBetStates.enter_profit)
            
        elif result == 'lost':
            # Loss = -stake
            bet_data['profit'] = -bet_data['stake']
            await state.update_data(bet_data=bet_data)
            await show_confirmation(callback, state, lang, bet_data)
            
        else:  # pending
            bet_data['profit'] = 0
            await state.update_data(bet_data=bet_data)
            await show_confirmation(callback, state, lang, bet_data)
        
    finally:
        db.close()


@router.message(AddBetStates.enter_profit)
async def receive_profit(message: types.Message, state: FSMContext):
    """Receive profit amount"""
    profit_text = message.text.strip().replace('$', '').replace(',', '')
    
    user_id = message.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        try:
            profit = float(profit_text)
        except ValueError:
            error_msg = "❌ Montant invalide!" if lang == 'fr' else "❌ Invalid amount!"
            await message.answer(error_msg)
            return
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        bet_data['profit'] = profit
        bet_data['roi'] = (profit / bet_data['stake'] * 100) if bet_data['stake'] > 0 else 0
        await state.update_data(bet_data=bet_data)
        
        # Show confirmation
        if lang == 'fr':
            text = await build_confirmation_text_fr(bet_data)
        else:
            text = await build_confirmation_text_en(bet_data)
        
        keyboard = [
            [InlineKeyboardButton(
                text="💾 Sauvegarder" if lang == 'fr' else "💾 Save",
                callback_data="save_newbet"
            )],
            [InlineKeyboardButton(
                text="❌ Annuler" if lang == 'fr' else "❌ Cancel",
                callback_data="cancel_add_bet"
            )]
        ]
        
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AddBetStates.confirm_bet)
        
    finally:
        db.close()


async def show_confirmation(callback: types.CallbackQuery, state: FSMContext, lang: str, bet_data: dict):
    """Show confirmation summary"""
    if lang == 'fr':
        text = await build_confirmation_text_fr(bet_data)
    else:
        text = await build_confirmation_text_en(bet_data)
    
    keyboard = [
        [InlineKeyboardButton(
            text="💾 Sauvegarder" if lang == 'fr' else "💾 Save",
            callback_data="save_newbet"
        )],
        [InlineKeyboardButton(
            text="❌ Annuler" if lang == 'fr' else "❌ Cancel",
            callback_data="cancel_add_bet"
        )]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(AddBetStates.confirm_bet)


async def build_confirmation_text_fr(bet_data: dict) -> str:
    """Build confirmation text in French"""
    type_names = {
        'arbitrage': '⚖️ Arbitrage',
        'good_ev': '💎 Good +EV',
        'middle': '🎯 Middle Bet'
    }
    
    result_names = {
        'won': '✅ GAGNÉ',
        'lost': '❌ PERDU',
        'pending': '⏳ EN ATTENTE'
    }
    
    text = (
        "✅ <b>CONFIRME TON BET</b>\n\n"
        "Résumé:\n\n"
        f"{type_names[bet_data['type']]}\n"
        f"📅 {bet_data['date'].strftime('%Y-%m-%d')}\n"
        f"🎲 {result_names[bet_data['result']]}\n\n"
    )
    
    # Add sport and match if available
    if 'sport' in bet_data:
        text += f"🏀 <b>Sport:</b> {bet_data['sport']}\n"
    if 'match' in bet_data:
        text += f"🏈 <b>Match:</b> {bet_data['match']}\n\n"
    
    text += (
        f"💰 <b>Montant misé:</b> ${bet_data['stake']:,.2f}\n"
        f"📈 <b>Profit:</b> ${bet_data['profit']:+,.2f}\n"
    )
    
    if 'roi' in bet_data:
        text += f"📊 <b>ROI:</b> {bet_data['roi']:+.1f}%\n"
    
    text += "\nTout est correct?"
    
    return text


async def build_confirmation_text_en(bet_data: dict) -> str:
    """Build confirmation text in English"""
    type_names = {
        'arbitrage': '⚖️ Arbitrage',
        'good_ev': '💎 Good +EV',
        'middle': '🎯 Middle Bet'
    }
    
    result_names = {
        'won': '✅ WON',
        'lost': '❌ LOST',
        'pending': '⏳ PENDING'
    }
    
    text = (
        "✅ <b>CONFIRM YOUR BET</b>\n\n"
        "Summary:\n\n"
        f"{type_names[bet_data['type']]}\n"
        f"📅 {bet_data['date'].strftime('%Y-%m-%d')}\n"
        f"🎲 {result_names[bet_data['result']]}\n\n"
    )
    
    # Add sport and match if available
    if 'sport' in bet_data:
        text += f"🏀 <b>Sport:</b> {bet_data['sport']}\n"
    if 'match' in bet_data:
        text += f"🏈 <b>Match:</b> {bet_data['match']}\n\n"
    
    text += (
        f"💰 <b>Staked:</b> ${bet_data['stake']:,.2f}\n"
        f"📈 <b>Profit:</b> ${bet_data['profit']:+,.2f}\n"
    )
    
    if 'roi' in bet_data:
        text += f"📊 <b>ROI:</b> {bet_data['roi']:+.1f}%\n"
    
    text += "\nEverything correct?"
    
    return text


@router.callback_query(F.data == "save_newbet", AddBetStates.confirm_bet)
async def save_new_bet(callback: types.CallbackQuery, state: FSMContext):
    """Save the new bet to database"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        data = await state.get_data()
        bet_data = data.get('bet_data', {})
        
        # Create DropEvent if sport and match are provided
        drop_event_id = None
        if 'sport' in bet_data and 'match' in bet_data:
            # Generate a unique event_id for manual bets
            import uuid
            event_id = f"manual_{user_id}_{uuid.uuid4().hex[:8]}"
            
            drop_event = DropEvent(
                event_id=event_id,
                league=bet_data['sport'],  # Use sport as league
                match=bet_data['match'],
                arb_percentage=bet_data.get('roi', 0.0)
            )
            db.add(drop_event)
            db.flush()  # Get the ID
            drop_event_id = drop_event.id
        
        # Create UserBet
        user_bet = UserBet(
            user_id=user_id,
            drop_event_id=drop_event_id,
            bet_type=bet_data['type'],
            bet_date=bet_data['date'],
            total_stake=bet_data['stake'],
            expected_profit=bet_data['profit'],
            actual_profit=bet_data['profit'] if bet_data['result'] != 'pending' else None,
            status='completed' if bet_data['result'] != 'pending' else 'pending'
        )
        db.add(user_bet)
        
        # Update DailyStats
        daily_stat = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == bet_data['date']
        ).first()
        
        if daily_stat:
            daily_stat.total_bets += 1
            daily_stat.total_staked += bet_data['stake']
            daily_stat.total_profit += bet_data['profit']
        else:
            daily_stat = DailyStats(
                user_id=user_id,
                date=bet_data['date'],
                total_bets=1,
                total_staked=bet_data['stake'],
                total_profit=bet_data['profit'],
                confirmed=True
            )
            db.add(daily_stat)
        
        db.commit()
        
        # Success message
        type_emojis = {
            'arbitrage': '⚖️',
            'good_ev': '💎',
            'middle': '🎯'
        }
        
        emoji = type_emojis.get(bet_data['type'], '🎲')
        
        if lang == 'fr':
            text = (
                f"✅ <b>BET AJOUTÉ AVEC SUCCÈS!</b>\n\n"
                f"{emoji} {bet_data['type'].title()}\n"
                f"💰 ${bet_data['stake']:,.2f} → ${bet_data['profit']:+,.2f}\n"
            )
            if 'roi' in bet_data:
                text += f"📊 ROI: {bet_data['roi']:+.1f}%\n"
            text += "\nTes stats ont été mises à jour!"
        else:
            text = (
                f"✅ <b>BET ADDED SUCCESSFULLY!</b>\n\n"
                f"{emoji} {bet_data['type'].title()}\n"
                f"💰 ${bet_data['stake']:,.2f} → ${bet_data['profit']:+,.2f}\n"
            )
            if 'roi' in bet_data:
                text += f"📊 ROI: {bet_data['roi']:+.1f}%\n"
            text += "\nYour stats have been updated!"
        
        keyboard = [
            [InlineKeyboardButton(
                text="📊 Voir mes stats" if lang == 'fr' else "📊 View stats",
                callback_data="my_stats"
            )],
            [InlineKeyboardButton(
                text="➕ Ajouter un autre" if lang == 'fr' else "➕ Add another",
                callback_data="add_bet"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error saving new bet: {e}")
        error_msg = "❌ Erreur lors de la sauvegarde" if lang == 'fr' else "❌ Error saving bet"
        await callback.answer(error_msg, show_alert=True)
        db.rollback()
    finally:
        db.close()


@router.callback_query(F.data == "cancel_add_bet")
async def cancel_add_bet(callback: types.CallbackQuery, state: FSMContext):
    """Cancel adding a bet"""
    await callback.answer("❌ Annulé" if callback.from_user.language_code == 'fr' else "❌ Cancelled")
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        text = "❌ Ajout annulé.\n\nAucune modification." if lang == 'fr' else "❌ Cancelled.\n\nNo changes made."
        
        keyboard = [[InlineKeyboardButton(
            text="◀️ Retour stats" if lang == 'fr' else "◀️ Back to stats",
            callback_data="my_stats"
        )]]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.clear()
        
    finally:
        db.close()
