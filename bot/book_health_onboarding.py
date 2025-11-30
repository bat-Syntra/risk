"""
Book Health Onboarding Module
Handles questionnaire and profile setup
"""
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode

from database import SessionLocal
from sqlalchemy import text as sql_text

router = Router()
logger = logging.getLogger(__name__)

# FSM States
class BookHealthStates(StatesGroup):
    selecting_casinos = State()
    questionnaire_age = State()
    questionnaire_bets = State()
    questionnaire_active = State()
    questionnaire_deposit = State()
    questionnaire_types = State()
    confirming = State()

# Casino configuration
SUPPORTED_CASINOS = {
    'betsson': {'name': 'Betsson', 'emoji': '🔶'},
    'bet365': {'name': 'bet365', 'emoji': '📗'},
    'coolbet': {'name': 'Coolbet', 'emoji': '❄️'},
    'bet99': {'name': 'BET99', 'emoji': '💯'},
    'leovegas': {'name': 'LeoVegas', 'emoji': '🦁'},
    'betway': {'name': 'Betway', 'emoji': '⚡'},
    'bwin': {'name': 'bwin', 'emoji': '🎯'},
    'sportinteraction': {'name': 'Sports Interaction', 'emoji': '🏈'},
    'powerplay': {'name': 'PowerPlay', 'emoji': '⚡'},
    'mise_o_jeu': {'name': 'Mise-o-jeu', 'emoji': '🍁'}
}


@router.callback_query(F.data == "book_health_start")
async def start_onboarding(callback: CallbackQuery, state: FSMContext):
    """Start Book Health setup"""
    await callback.answer()
    
    text = """
🏥 <b>BOOK HEALTH MONITOR</b>

Ce système analyse ton comportement de paris pour prédire quand tu risques de te faire limiter.

⚠️ <b>BETA - DISCLAIMER:</b>

• Système basé sur patterns observés
• PAS 100% précis (estimation seulement)
• Tu peux être limité sans warning
• Ou jamais limité malgré score élevé
• Utilise comme GUIDE, pas garantie

<b>Veux-tu configurer ton Book Health Monitor?</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Commencer", callback_data="health_start_setup")],
        [InlineKeyboardButton(text="❌ Plus tard", callback_data="my_stats")]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data == "health_start_setup")
async def select_casinos(callback: CallbackQuery, state: FSMContext):
    """Step 1: Select casinos"""
    await callback.answer()
    
    await state.update_data(
        user_id=str(callback.from_user.id),
        selected_casinos=[], 
        temp_data={}
    )
    await state.set_state(BookHealthStates.selecting_casinos)
    
    keyboard_rows = []
    for key, casino_info in SUPPORTED_CASINOS.items():
        keyboard_rows.append([InlineKeyboardButton(
            text=f"{casino_info['emoji']} {casino_info['name']}", 
            callback_data=f"health_casino_{key}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="✅ Terminé", callback_data="health_casinos_done")])
    
    text = """
🏢 <b>ÉTAPE 1: SÉLECTION DES CASINOS</b>

Sur quels casinos veux-tu monitorer ta santé?

<b>Sélectionné:</b> Aucun

<i>💡 Tu peux en sélectionner plusieurs</i>
"""
    
    await callback.message.edit_text(
        text, 
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )


@router.callback_query(F.data.startswith("health_casino_"))
async def handle_casino_selection(callback: CallbackQuery, state: FSMContext):
    """Handle casino selection toggle"""
    casino_key = callback.data.replace("health_casino_", "")
    
    data = await state.get_data()
    selected = data.get('selected_casinos', [])
    
    if casino_key in selected:
        selected.remove(casino_key)
        await callback.answer(f"❌ {SUPPORTED_CASINOS[casino_key]['name']} retiré")
    else:
        selected.append(casino_key)
        await callback.answer(f"✅ {SUPPORTED_CASINOS[casino_key]['name']} ajouté")
    
    await state.update_data(selected_casinos=selected)
    
    # Update message
    keyboard_rows = []
    for key, casino_info in SUPPORTED_CASINOS.items():
        emoji = "✅" if key in selected else ""
        keyboard_rows.append([InlineKeyboardButton(
            text=f"{emoji} {casino_info['emoji']} {casino_info['name']}", 
            callback_data=f"health_casino_{key}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="✅ Terminé", callback_data="health_casinos_done")])
    
    selected_text = "\n".join([
        f"• {SUPPORTED_CASINOS[c]['emoji']} {SUPPORTED_CASINOS[c]['name']}" 
        for c in selected
    ]) if selected else "Aucun"
    
    text = f"""
🏢 <b>ÉTAPE 1: SÉLECTION DES CASINOS</b>

Sur quels casinos veux-tu monitorer ta santé?

<b>Sélectionné:</b>
{selected_text}

<i>💡 Tu peux en sélectionner plusieurs</i>
"""
    
    await callback.message.edit_text(
        text, 
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )


@router.callback_query(F.data == "health_casinos_done")
async def start_questionnaire(callback: CallbackQuery, state: FSMContext):
    """Start questionnaire for first casino"""
    data = await state.get_data()
    selected = data.get('selected_casinos', [])
    
    if not selected:
        await callback.answer("❌ Sélectionne au moins un casino!", show_alert=True)
        return
    
    await state.update_data(current_casino_index=0)
    await ask_account_age(callback, state)


async def ask_account_age(callback: CallbackQuery, state: FSMContext):
    """Question 1: Account age"""
    await callback.answer()
    data = await state.get_data()
    casino_index = data.get('current_casino_index', 0)
    selected = data['selected_casinos']
    casino_key = selected[casino_index]
    casino = SUPPORTED_CASINOS[casino_key]
    
    await state.update_data(current_casino=casino_key)
    await state.set_state(BookHealthStates.questionnaire_age)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="< 3 mois", callback_data="age_0-3")],
        [InlineKeyboardButton(text="3-6 mois", callback_data="age_3-6")],
        [InlineKeyboardButton(text="6-12 mois", callback_data="age_6-12")],
        [InlineKeyboardButton(text="1-2 ans", callback_data="age_12-24")],
        [InlineKeyboardButton(text="2+ ans", callback_data="age_24+")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

📅 <b>Question 1/5: Âge du compte</b>

Depuis combien de temps as-tu un compte sur {casino['name']}?
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("age_"))
async def handle_age_answer(callback: CallbackQuery, state: FSMContext):
    """Handle age answer and move to next question"""
    data = await state.get_data()
    casino = data['current_casino']
    temp_data = data.get('temp_data', {})
    
    if casino not in temp_data:
        temp_data[casino] = {}
    temp_data[casino]['age'] = callback.data
    
    await state.update_data(temp_data=temp_data)
    await ask_total_bets(callback, state)


async def ask_total_bets(callback: CallbackQuery, state: FSMContext):
    """Question 2: Total bets"""
    await callback.answer()
    data = await state.get_data()
    casino_key = data['current_casino']
    casino = SUPPORTED_CASINOS[casino_key]
    
    await state.set_state(BookHealthStates.questionnaire_bets)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="< 50 bets", callback_data="bets_0-50")],
        [InlineKeyboardButton(text="50-200 bets", callback_data="bets_50-200")],
        [InlineKeyboardButton(text="200-500 bets", callback_data="bets_200-500")],
        [InlineKeyboardButton(text="500-1000 bets", callback_data="bets_500-1000")],
        [InlineKeyboardButton(text="1000+ bets", callback_data="bets_1000+")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

🎯 <b>Question 2/5: Volume de paris</b>

Environ combien de paris as-tu placé sur {casino['name']} AU TOTAL?

<i>💡 Estimation approximative</i>
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("bets_"))
async def handle_bets_answer(callback: CallbackQuery, state: FSMContext):
    """Handle bets answer"""
    data = await state.get_data()
    casino = data['current_casino']
    temp_data = data.get('temp_data', {})
    
    if casino not in temp_data:
        temp_data[casino] = {}
    temp_data[casino]['bets'] = callback.data
    
    await state.update_data(temp_data=temp_data)
    await ask_activity_before(callback, state)


async def ask_activity_before(callback: CallbackQuery, state: FSMContext):
    """Question 3: Activity before RISK0"""
    await callback.answer()
    data = await state.get_data()
    casino_key = data['current_casino']
    casino = SUPPORTED_CASINOS[casino_key]
    
    await state.set_state(BookHealthStates.questionnaire_active)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Oui, très actif", callback_data="active_high")],
        [InlineKeyboardButton(text="Oui, moyennement", callback_data="active_medium")],
        [InlineKeyboardButton(text="Non, jamais actif", callback_data="active_no")],
        [InlineKeyboardButton(text="Nouveau compte", callback_data="active_new")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

📊 <b>Question 3/5: Activité passée</b>

AVANT de commencer avec RISK0, étais-tu actif régulièrement sur {casino['name']}?

<i>💡 Aide à comprendre si ton changement est suspect</i>
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("active_"))
async def handle_activity_answer(callback: CallbackQuery, state: FSMContext):
    """Handle activity answer"""
    data = await state.get_data()
    casino = data['current_casino']
    temp_data = data.get('temp_data', {})
    
    if casino not in temp_data:
        temp_data[casino] = {}
    temp_data[casino]['active'] = callback.data
    
    await state.update_data(temp_data=temp_data)
    await ask_total_deposited(callback, state)


async def ask_total_deposited(callback: CallbackQuery, state: FSMContext):
    """Question 4: Total deposited"""
    await callback.answer()
    data = await state.get_data()
    casino_key = data['current_casino']
    casino = SUPPORTED_CASINOS[casino_key]
    
    await state.set_state(BookHealthStates.questionnaire_deposit)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="< $500", callback_data="deposit_0-500")],
        [InlineKeyboardButton(text="$500-$2k", callback_data="deposit_500-2000")],
        [InlineKeyboardButton(text="$2k-$5k", callback_data="deposit_2000-5000")],
        [InlineKeyboardButton(text="$5k-$10k", callback_data="deposit_5000-10000")],
        [InlineKeyboardButton(text="$10k+", callback_data="deposit_10000+")],
        [InlineKeyboardButton(text="Préfère ne pas dire", callback_data="deposit_skip")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

💰 <b>Question 4/5: Dépôts totaux</b>

Environ combien as-tu déposé AU TOTAL sur {casino['name']}?

<i>💡 Info privée, aide à calculer le risque</i>
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("deposit_"))
async def handle_deposit_answer(callback: CallbackQuery, state: FSMContext):
    """Handle deposit answer"""
    data = await state.get_data()
    casino = data['current_casino']
    temp_data = data.get('temp_data', {})
    
    if casino not in temp_data:
        temp_data[casino] = {}
    temp_data[casino]['deposit'] = callback.data
    
    await state.update_data(temp_data=temp_data, activity_types=[])
    await ask_activity_types(callback, state)


async def ask_activity_types(callback: CallbackQuery, state: FSMContext):
    """Question 5: Activity types"""
    await callback.answer()
    data = await state.get_data()
    casino_key = data['current_casino']
    casino = SUPPORTED_CASINOS[casino_key]
    
    await state.set_state(BookHealthStates.questionnaire_types)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Sports Betting", callback_data="type_sports")],
        [InlineKeyboardButton(text="🎰 Casino/Slots", callback_data="type_casino")],
        [InlineKeyboardButton(text="🃏 Poker", callback_data="type_poker")],
        [InlineKeyboardButton(text="⚡ Live Betting", callback_data="type_live")],
        [InlineKeyboardButton(text="✅ Terminé", callback_data="type_done")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

🎲 <b>Question 5/5: Types d'activité</b>

Qu'est-ce que tu fais sur {casino['name']}?

<b>Sélectionné:</b> Aucun

<i>💡 Tu peux sélectionner plusieurs options</i>
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("type_"))
async def handle_activity_type(callback: CallbackQuery, state: FSMContext):
    """Handle activity type selection"""
    if callback.data == "type_done":
        await save_and_continue(callback, state)
        return
    
    activity_type = callback.data.replace("type_", "")
    data = await state.get_data()
    activity_types = data.get('activity_types', [])
    
    if activity_type in activity_types:
        activity_types.remove(activity_type)
        await callback.answer(f"❌ Retiré")
    else:
        activity_types.append(activity_type)
        await callback.answer(f"✅ Ajouté")
    
    await state.update_data(activity_types=activity_types)
    
    # Update message
    casino_key = data['current_casino']
    casino = SUPPORTED_CASINOS[casino_key]
    
    type_labels = {
        'sports': '⚽ Sports Betting',
        'casino': '🎰 Casino/Slots',
        'poker': '🃏 Poker',
        'live': '⚡ Live Betting'
    }
    
    selected_text = "\n".join([
        f"• {type_labels.get(t, t)}" for t in activity_types
    ]) if activity_types else "Aucun"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=("✅ " if 'sports' in activity_types else "") + "⚽ Sports Betting", 
            callback_data="type_sports"
        )],
        [InlineKeyboardButton(
            text=("✅ " if 'casino' in activity_types else "") + "🎰 Casino/Slots", 
            callback_data="type_casino"
        )],
        [InlineKeyboardButton(
            text=("✅ " if 'poker' in activity_types else "") + "🃏 Poker", 
            callback_data="type_poker"
        )],
        [InlineKeyboardButton(
            text=("✅ " if 'live' in activity_types else "") + "⚡ Live Betting", 
            callback_data="type_live"
        )],
        [InlineKeyboardButton(text="✅ Terminé", callback_data="type_done")]
    ])
    
    text = f"""
{casino['emoji']} <b>{casino['name'].upper()}</b>

🎲 <b>Question 5/5: Types d'activité</b>

Qu'est-ce que tu fais sur {casino['name']}?

<b>Sélectionné:</b>
{selected_text}

<i>💡 Tu peux sélectionner plusieurs options</i>
"""
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def save_and_continue(callback: CallbackQuery, state: FSMContext):
    """Save profile and continue to next casino or finish"""
    await callback.answer()
    
    # Save current casino profile
    data = await state.get_data()
    casino = data['current_casino']
    temp_data = data.get('temp_data', {}).get(casino, {})
    activity_types = data.get('activity_types', [])
    
    # Store activity types in temp_data
    temp_data['types'] = activity_types
    data['temp_data'][casino] = temp_data
    await state.update_data(temp_data=data['temp_data'])
    
    # Save to database
    saved = await save_profile(data['user_id'], casino, temp_data)
    
    if not saved:
        await callback.message.edit_text(
            "❌ Erreur lors de la sauvegarde. Réessaye plus tard.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    # Check if more casinos to configure
    casino_index = data.get('current_casino_index', 0)
    selected_casinos = data.get('selected_casinos', [])
    
    if casino_index + 1 < len(selected_casinos):
        # Move to next casino
        await state.update_data(
            current_casino_index=casino_index + 1,
            activity_types=[]
        )
        await ask_account_age(callback, state)
    else:
        # All done!
        await complete_onboarding(callback, state)


async def save_profile(user_id: str, casino: str, temp_data: dict) -> bool:
    """Save casino profile to database"""
    # Parse values
    age_map = {'0-3': 2, '3-6': 5, '6-12': 9, '12-24': 18, '24+': 36}
    bets_map = {'0-50': 25, '50-200': 125, '200-500': 350, '500-1000': 750, '1000+': 1500}
    deposit_map = {'0-500': 250, '500-2000': 1250, '2000-5000': 3500, '5000-10000': 7500, '10000+': 15000, 'skip': None}
    active_map = {'high': True, 'medium': True, 'no': False, 'new': False}
    
    db = SessionLocal()
    try:
        # Parse data
        age_key = temp_data.get('age', 'age_0-3').split('_')[1]
        bets_key = temp_data.get('bets', 'bets_0-50').split('_')[1]
        active_key = temp_data.get('active', 'active_no').split('_')[1]
        deposit_key = temp_data.get('deposit', 'deposit_skip').split('_')[1]
        types = temp_data.get('types', [])
        
        # Check if exists
        existing = db.execute(sql_text("""
            SELECT profile_id FROM user_casino_profiles 
            WHERE user_id = :user_id AND casino = :casino
        """), {"user_id": user_id, "casino": casino}).first()
        
        if existing:
            # Update
            db.execute(sql_text("""
                UPDATE user_casino_profiles SET
                    account_age_months = :age,
                    estimated_total_bets = :bets,
                    was_active_before = :active,
                    total_deposited = :deposit,
                    does_sports_betting = :sports,
                    does_casino_games = :casino_games,
                    does_poker = :poker,
                    does_live_betting = :live,
                    updated_at = :now
                WHERE user_id = :user_id AND casino = :casino
            """), {
                "user_id": user_id,
                "casino": casino,
                "age": age_map.get(age_key, 6),
                "bets": bets_map.get(bets_key, 50),
                "active": active_map.get(active_key, False),
                "deposit": deposit_map.get(deposit_key),
                "sports": 'sports' in types,
                "casino_games": 'casino' in types,
                "poker": 'poker' in types,
                "live": 'live' in types,
                "now": datetime.utcnow()
            })
        else:
            # Insert
            import uuid
            db.execute(sql_text("""
                INSERT INTO user_casino_profiles (
                    profile_id, user_id, casino, account_age_months, 
                    estimated_total_bets, was_active_before, total_deposited,
                    does_sports_betting, does_casino_games, does_poker, does_live_betting
                ) VALUES (
                    :id, :user_id, :casino, :age, :bets, :active, :deposit,
                    :sports, :casino_games, :poker, :live
                )
            """), {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "casino": casino,
                "age": age_map.get(age_key, 6),
                "bets": bets_map.get(bets_key, 50),
                "active": active_map.get(active_key, False),
                "deposit": deposit_map.get(deposit_key),
                "sports": 'sports' in types,
                "casino_games": 'casino' in types,
                "poker": 'poker' in types,
                "live": 'live' in types
            })
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        db.rollback()
        return False
    finally:
        db.close()


async def complete_onboarding(callback: CallbackQuery, state: FSMContext):
    """Complete onboarding and show success message"""
    data = await state.get_data()
    selected_casinos = data.get('selected_casinos', [])
    
    casino_list = "\n".join([
        f"• {SUPPORTED_CASINOS[c]['emoji']} {SUPPORTED_CASINOS[c]['name']}"
        for c in selected_casinos
    ])
    
    text = f"""
✅ <b>BOOK HEALTH MONITOR ACTIVÉ!</b>

Ton profil est configuré pour:
{casino_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>PROCHAINES ÉTAPES:</b>

1. Continue à utiliser RISK0 normalement
2. On va tracker tes paris automatiquement
3. Dans 7 jours, tu recevras ton premier rapport
4. Score mis à jour quotidiennement

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>RAPPEL:</b>

• Système en BETA (pas 100% précis)
• Utilise comme guide seulement
• Aucune garantie de prédiction exacte

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Voir Dashboard", callback_data="book_health_dashboard")],
        [InlineKeyboardButton(text="📈 Retour Stats", callback_data="my_stats")]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    await state.clear()
