"""
Middle Bet Handlers
Gère les interactions avec les middle bets: Calculator, I BET, Change CASHH, etc.
"""
import hashlib
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from datetime import datetime
import sqlite3

from database import SessionLocal
from models.user import User
from utils.middle_calculator import classify_middle_type, describe_middle_zone, get_recommendation, get_unit
from core.casinos import get_casino_logo
from config import ADMIN_CHAT_ID

router = Router()

# In-memory storage for active middles (similar to DROPS in main_new.py)
ACTIVE_MIDDLES = {}  # {middle_hash: middle_data}
MIDDLE_TOKENS = {}   # {token: middle_hash}

class MiddleCashhStates(StatesGroup):
    """FSM states for changing CASHH amount"""
    awaiting_amount = State()


def _generate_middle_hash(data: dict) -> str:
    """Generate unique hash for middle bet"""
    key = f"{data['side_a']['bookmaker']}_{data['side_a']['line']}_{data['side_b']['bookmaker']}_{data['side_b']['line']}_{datetime.now().strftime('%Y%m%d%H')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _generate_token(middle_hash: str) -> str:
    """Generate short token for callback data"""
    token = hashlib.md5(middle_hash.encode()).hexdigest()[:8]
    MIDDLE_TOKENS[token] = middle_hash
    return token


def store_middle(middle_data: dict, calc: dict):
    """Store middle in memory and return hash"""
    middle_hash = _generate_middle_hash(middle_data)
    
    ACTIVE_MIDDLES[middle_hash] = {
        'data': middle_data,
        'calc': calc,
        'timestamp': datetime.now().isoformat()
    }
    
    return middle_hash


def build_middle_keyboard(middle_data: dict, calc: dict, middle_hash: str, bet_placed: bool = False):
    """
    Build keyboard for middle bet message
    
    Args:
        middle_data: Middle data
        calc: Calculation results
        middle_hash: Unique identifier
        bet_placed: If True, show different buttons (✅ + Cancel)
    """
    token = _generate_token(middle_hash)
    
    # Casino buttons
    keyboard = []
    
    bookmaker_a = middle_data['side_a']['bookmaker']
    bookmaker_b = middle_data['side_b']['bookmaker']
    
    # Get URLs (simplified - you can enhance with deep links later)
    from core.casinos import get_casino_referral_link
    from utils.odds_api_links import get_fallback_url
    
    url_a = get_casino_referral_link(bookmaker_a) or get_fallback_url(bookmaker_a)
    url_b = get_casino_referral_link(bookmaker_b) or get_fallback_url(bookmaker_b)
    
    if url_a and url_b:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{get_casino_logo(bookmaker_a)} {bookmaker_a}",
                url=url_a
            ),
            InlineKeyboardButton(
                text=f"{get_casino_logo(bookmaker_b)} {bookmaker_b}",
                url=url_b
            )
        ])
    
    if not bet_placed:
        # Normal mode: I BET, Calculator, Change CASHH
        profit_min = min(calc['profit_scenario_1'], calc['profit_scenario_3'])
        profit_max = calc['profit_scenario_2']
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"💰 I BET (${profit_min:.2f} to ${profit_max:.2f})",
                callback_data=f"midnew_bet_{token}"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🧮 Calculator",
                callback_data=f"midnew_calc_{token}"
            ),
            InlineKeyboardButton(
                text="💵 Change CASHH",
                callback_data=f"midnew_cashh_{token}"
            )
        ])
    else:
        # Bet placed mode: ✅ + Oops button
        keyboard.append([
            InlineKeyboardButton(
                text="✅ BET PLACED!",
                callback_data="noop"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Oops, mistake!",
                callback_data=f"midnew_cancel_{token}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_middle_message_with_calc(middle_data: dict, calc: dict, lang: str = 'fr') -> str:
    """Format middle message (reuse from test but cleaner)"""
    
    total_stake = calc['total_stake']
    emoji_a = get_casino_logo(middle_data['side_a']['bookmaker'])
    emoji_b = get_casino_logo(middle_data['side_b']['bookmaker'])
    
    # Determine type
    is_safe = calc['type'] == 'middle_safe'
    
    player_line = f"👤 {middle_data.get('player', '')} - {middle_data.get('market', '')}\n" if middle_data.get('player') else ""
    
    if is_safe:
        # Middle Safe
        min_profit = min(calc['profit_scenario_1'], calc['profit_scenario_3'])
        middle_profit = calc['profit_scenario_2']
        
        message = f"""✅🎰 <b>MIDDLE SAFE - PROFIT GARANTI + JACKPOT!</b> 🎰✅

🏈 <b>{middle_data['team1']} vs {middle_data['team2']}</b>
📊 {middle_data['league']}
{player_line}🕐 {middle_data.get('time', 'Today')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>CONFIGURATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji_a} <b>[{middle_data['side_a']['bookmaker']}]</b> {middle_data['side_a']['selection']}
💵 Mise: <b>${calc['stake_a']:.2f}</b> ({middle_data['side_a']['odds']})
📈 Retour: ${calc['return_a']:.2f}

{emoji_b} <b>[{middle_data['side_b']['bookmaker']}]</b> {middle_data['side_b']['selection']}
💵 Mise: <b>${calc['stake_b']:.2f}</b> ({middle_data['side_b']['odds']})
📈 Retour: ${calc['return_b']:.2f}

💰 <b>Total: ${total_stake:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>SCÉNARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>1. {middle_data['side_a']['selection']} hits seul</b>
✅ Profit: <b>${calc['profit_scenario_1']:.2f}</b> ({calc['profit_scenario_1']/total_stake*100:.1f}%)

<b>2. MIDDLE HIT! 🎰</b>
🚀 <b>Zone magique: {describe_middle_zone(middle_data)}</b>
🚀 <b>LES DEUX PARIS GAGNENT!</b>
💰 <b>Profit: ${middle_profit:.2f}</b> ({middle_profit/total_stake*100:.0f}% ROI!)

<b>3. {middle_data['side_b']['selection']} hits seul</b>
✅ Profit: <b>${calc['profit_scenario_3']:.2f}</b> ({calc['profit_scenario_3']/total_stake*100:.1f}%)

💡 <b>Gap:</b> {calc['middle_zone']} {get_unit(middle_data.get('market', ''))}
🎲 <b>Prob middle:</b> ~{calc['middle_prob']*100:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>POURQUOI C'EST INCROYABLE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Profit MIN garanti:</b> ${min_profit:.2f}
🛡️ <b>Risque:</b> ZÉRO (arbitrage!)
🎰 <b>Chance jackpot:</b> ~{calc['middle_prob']*100:.0f}%
🚀 <b>Jackpot si hit:</b> ${middle_profit:.2f}

⚡ <b>{get_recommendation(calc['middle_zone'])}</b> ⚡"""

    else:
        # Middle Risqué
        worst_loss = min(calc['profit_scenario_1'], calc['profit_scenario_3'])
        
        message = f"""🎯 <b>MIDDLE RISQUÉ - {calc['ev_percent']:.1f}% EV</b> 🎯

🏈 <b>{middle_data['team1']} vs {middle_data['team2']}</b>
📊 {middle_data['league']}
{player_line}🕐 {middle_data.get('time', 'Today')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>CONFIGURATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji_a} <b>[{middle_data['side_a']['bookmaker']}]</b> {middle_data['side_a']['selection']}
💵 Mise: <b>${calc['stake_a']:.2f}</b> ({middle_data['side_a']['odds']})

{emoji_b} <b>[{middle_data['side_b']['bookmaker']}]</b> {middle_data['side_b']['selection']}
💵 Mise: <b>${calc['stake_b']:.2f}</b> ({middle_data['side_b']['odds']})

💰 <b>Total: ${calc['total_stake']:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎲 <b>SCÉNARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Si UN seul gagne</b> (~{(1-calc['middle_prob'])*100:.0f}%)
❌ Petite perte: <b>${worst_loss:.2f}</b>

<b>Si LES DEUX gagnent - MIDDLE!</b> (~{calc['middle_prob']*100:.0f}%)
🚀 <b>GROS GAIN: ${calc['profit_scenario_2']:.2f}</b> 💰

💡 <b>Gap:</b> {calc['middle_zone']} {get_unit(middle_data.get('market', ''))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>EXPECTED VALUE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>EV Moyen:</b> +{calc['ev_percent']:.1f}%
<b>Profit moyen/bet:</b> ${calc['ev']:+.2f}

<b>Ratio gain/perte:</b> {calc['profit_scenario_2']/abs(worst_loss):.0f}:1

⚠️ <b>Ce N'EST PAS un arbitrage!</b>"""

    return message


@router.callback_query(F.data.startswith("midnew_bet_"))
async def handle_middle_i_bet(callback: types.CallbackQuery):
    """Handle 'I BET' button click"""
    print(f"🎯 MIDDLE I BET HANDLER CALLED! Data: {callback.data}")
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        print(f"🎯 Token extracted: {token}")
        middle_hash = MIDDLE_TOKENS.get(token)
        print(f"🎯 Middle hash: {middle_hash}")
        print(f"🎯 MIDDLE_TOKENS: {MIDDLE_TOKENS}")
        print(f"🎯 ACTIVE_MIDDLES keys: {list(ACTIVE_MIDDLES.keys())}")
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            print(f"❌ Middle expired or not found! Hash: {middle_hash}")
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        middle_info = ACTIVE_MIDDLES[middle_hash]
        middle_data = middle_info['data']
        calc = middle_info['calc']
        
        # Save to database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            
            if not user:
                await callback.answer("❌ User non trouvé", show_alert=True)
                return
            
            # Insert into middle_bets table
            conn = sqlite3.connect('arbitrage.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO middle_bets (
                    user_id, team1, team2, league, market, player,
                    middle_type, stake_a, stake_b, total_stake,
                    bookmaker_a, bookmaker_b, line_a, line_b,
                    odds_a, odds_b, selection_a, selection_b,
                    profit_scenario_1, profit_scenario_2, profit_scenario_3,
                    middle_zone, middle_prob, ev, ev_percent,
                    result, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.telegram_id,
                middle_data.get('team1'),
                middle_data.get('team2'),
                middle_data.get('league'),
                middle_data.get('market'),
                middle_data.get('player'),
                calc['type'],
                calc['stake_a'],
                calc['stake_b'],
                calc['total_stake'],
                middle_data['side_a']['bookmaker'],
                middle_data['side_b']['bookmaker'],
                float(middle_data['side_a']['line']),
                float(middle_data['side_b']['line']),
                int(middle_data['side_a']['odds'].replace('+', '')),
                int(middle_data['side_b']['odds'].replace('+', '')),
                middle_data['side_a']['selection'],
                middle_data['side_b']['selection'],
                calc['profit_scenario_1'],
                calc['profit_scenario_2'],
                calc['profit_scenario_3'],
                calc['middle_zone'],
                calc['middle_prob'],
                calc['ev'],
                calc['ev_percent'],
                'pending',
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Update message with ✅ and new keyboard
            new_keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=True)
            
            # Add checkmark to message
            current_text = callback.message.text or callback.message.caption or ""
            if not current_text.startswith("✅"):
                new_text = "✅ " + current_text
            else:
                new_text = current_text
            
            await callback.message.edit_text(
                text=new_text,
                reply_markup=new_keyboard,
                parse_mode=ParseMode.HTML
            )
            
            await callback.answer("✅ Bet enregistré!", show_alert=True)
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error in middle_i_bet: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("midnew_cancel_"))
async def handle_middle_cancel(callback: types.CallbackQuery):
    """Handle 'Oops, mistake!' button"""
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        # Delete from database (most recent for this user)
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM middle_bets
            WHERE user_id = ? AND result = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
        """, (callback.from_user.id,))
        
        conn.commit()
        conn.close()
        
        # Restore original keyboard
        middle_info = ACTIVE_MIDDLES[middle_hash]
        middle_data = middle_info['data']
        calc = middle_info['calc']
        
        original_keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=False)
        
        # Remove checkmark from message
        current_text = callback.message.text or callback.message.caption or ""
        if current_text.startswith("✅ "):
            new_text = current_text[2:]
        else:
            new_text = current_text
        
        await callback.message.edit_text(
            text=new_text,
            reply_markup=original_keyboard,
            parse_mode=ParseMode.HTML
        )
        
        await callback.answer("❌ Bet annulé", show_alert=True)
        
    except Exception as e:
        print(f"❌ Error in middle_cancel: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("midnew_cashh_"))
async def handle_middle_change_cashh(callback: types.CallbackQuery):
    """Show CASHH change options"""
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        # Show quick amounts
        amounts = [100, 200, 300, 500, 1000]
        keyboard = []
        
        for amt in amounts:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"${amt}",
                    callback_data=f"midnew_amt_{token}_{amt}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="✏️ Montant personnalisé",
                callback_data=f"midnew_cust_{token}"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour",
                callback_data=f"midnew_back_{token}"
            )
        ])
        
        await callback.message.edit_text(
            "💰 <b>Changer CASHH (par appel)</b>\nChoisis un montant rapide:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        print(f"❌ Error in middle_change_cashh: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("midnew_amt_"))
async def handle_middle_amount_select(callback: types.CallbackQuery):
    """Handle quick amount selection"""
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        token = parts[2]
        amount = float(parts[3])
        
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        middle_info = ACTIVE_MIDDLES[middle_hash]
        middle_data = middle_info['data']
        
        # Get user's rounding preference
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            user_rounding = user.stake_rounding if user else 0
        finally:
            db.close()
        
        # Recalculate with new amount and rounding
        calc = classify_middle_type(
            middle_data['side_a'],
            middle_data['side_b'],
            amount,
            user_rounding or 0
        )
        
        # Update storage
        middle_info['calc'] = calc
        
        # Rebuild message and keyboard
        new_text = format_middle_message_with_calc(middle_data, calc)
        new_keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=False)
        
        await callback.message.edit_text(
            text=new_text,
            reply_markup=new_keyboard,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        print(f"❌ Error in middle_amount_select: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("midnew_cust_"))
async def handle_middle_custom_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Prompt for custom amount"""
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash:
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        await state.set_state(MiddleCashhStates.awaiting_amount)
        await state.update_data(
            middle_hash=middle_hash,
            token=token,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
        
        await callback.message.edit_text("💰 Entre un montant personnalisé ($):\nEx: 350")
        
    except Exception as e:
        print(f"❌ Error in middle_custom_prompt: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.message(MiddleCashhStates.awaiting_amount)
async def handle_middle_custom_amount(message: types.Message, state: FSMContext):
    """Handle custom amount input"""
    text = (message.text or "").strip().replace('$', '').replace(',', '')
    
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("❌ Montant invalide. Ex: 350")
        return
    
    data = await state.get_data()
    middle_hash = data.get('middle_hash')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    
    if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
        await message.answer("❌ Middle expiré")
        await state.clear()
        return
    
    middle_info = ACTIVE_MIDDLES[middle_hash]
    middle_data = middle_info['data']
    
    # Get user's rounding preference
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        user_rounding = user.stake_rounding if user else 0
    finally:
        db.close()
    
    # Recalculate with rounding
    calc = classify_middle_type(
        middle_data['side_a'],
        middle_data['side_b'],
        amount,
        user_rounding or 0
    )
    
    # Update storage
    middle_info['calc'] = calc
    
    # Rebuild message
    new_text = format_middle_message_with_calc(middle_data, calc)
    new_keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=False)
    
    # Edit original message
    from aiogram import Bot
    import os
    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=new_text,
            reply_markup=new_keyboard,
            parse_mode=ParseMode.HTML
        )
    finally:
        await bot.session.close()
    
    # Delete user's message
    try:
        await message.delete()
    except:
        pass
    
    await state.clear()


@router.callback_query(F.data.startswith("midnew_back_"))
async def handle_middle_back(callback: types.CallbackQuery):
    """Return to main middle view"""
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        middle_info = ACTIVE_MIDDLES[middle_hash]
        middle_data = middle_info['data']
        calc = middle_info['calc']
        
        # Rebuild original view
        text = format_middle_message_with_calc(middle_data, calc)
        keyboard = build_middle_keyboard(middle_data, calc, middle_hash, bet_placed=False)
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        print(f"❌ Error in middle_back: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data.startswith("midnew_calc_"))
async def handle_middle_calculator(callback: types.CallbackQuery):
    """Show calculator (simplified for now)"""
    print(f"🧮 MIDDLE CALCULATOR HANDLER CALLED! Data: {callback.data}")
    await callback.answer()
    
    try:
        token = callback.data.split('_', 2)[2]
        print(f"🧮 Token: {token}, MIDDLE_TOKENS: {MIDDLE_TOKENS}")
        middle_hash = MIDDLE_TOKENS.get(token)
        
        if not middle_hash or middle_hash not in ACTIVE_MIDDLES:
            print(f"❌ Calculator: Middle expired! Hash: {middle_hash}")
            await callback.answer("❌ Middle expiré", show_alert=True)
            return
        
        middle_info = ACTIVE_MIDDLES[middle_hash]
        calc = middle_info['calc']
        
        calc_text = f"""🧮 <b>CALCULATEUR MIDDLE</b>

💰 <b>Stakes calculés:</b>
• Side A: ${calc['stake_a']:.2f}
• Side B: ${calc['stake_b']:.2f}
• Total: ${calc['total_stake']:.2f}

📊 <b>Profits possibles:</b>
• Scénario 1: ${calc['profit_scenario_1']:.2f}
• Middle: ${calc['profit_scenario_2']:.2f}
• Scénario 3: ${calc['profit_scenario_3']:.2f}

💡 <b>Type:</b> {calc['type']}
📈 <b>EV:</b> {calc['ev_percent']:.1f}%
🎲 <b>Prob middle:</b> {calc['middle_prob']*100:.0f}%"""

        keyboard = [[InlineKeyboardButton(text="◀️ Retour", callback_data=f"midnew_back_{token}")]]
        
        await callback.message.edit_text(
            text=calc_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        print(f"❌ Error in middle_calculator: {e}")
        await callback.answer("❌ Erreur", show_alert=True)


@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    """No-op callback for disabled buttons"""
    await callback.answer()
