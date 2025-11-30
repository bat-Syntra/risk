"""
Parlay Preferences Handler - User settings and interactive menus
"""
import logging
import json
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from sqlalchemy import text
from utils.risk_profile_system import RiskProfile, RISK_PROFILES
from models.user import User, TierLevel

logger = logging.getLogger(__name__)
router = Router()

# ... (rest of the code remains the same)

# Add a rate limiting system
rate_limits = {}
class ParlaySettingsStates(StatesGroup):
    """FSM states for parlay settings"""
    setting_bankroll = State()
    setting_min_edge = State()
    setting_max_legs = State()
    setting_max_daily = State()


class UserPreferencesManager:
    """Manage user parlay preferences"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    async def get_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences"""
        result = self.db.execute(text("""
            SELECT * FROM user_preferences WHERE user_id = :user_id
        """), {'user_id': user_id})
        
        prefs = result.fetchone()
        if prefs:
            prefs_dict = dict(prefs._mapping)
            # Parse JSON fields
            import json
            for field in ['preferred_casinos', 'blocked_casinos', 'risk_profiles', 'preferred_sports', 'blocked_sports']:
                if prefs_dict.get(field) and isinstance(prefs_dict[field], str):
                    try:
                        prefs_dict[field] = json.loads(prefs_dict[field])
                    except:
                        prefs_dict[field] = []
            return prefs_dict
        
        # Return defaults if no preferences
        return {
            'user_id': user_id,
            'preferred_casinos': [],
            'blocked_casinos': [],
            'risk_profiles': ['BALANCED'],
            'min_parlay_edge': 0.10,
            'max_parlay_legs': 3,
            'notification_mode': 'push',
            'max_daily_notifications': 10,
            'preferred_sports': [],
            'blocked_sports': [],
            'bankroll': None
        }
    
    async def save_preferences(self, user_id: int, updates: Dict[str, Any]):
        """Save user preferences"""
        try:
            import json
            # Get current preferences
            current = await self.get_preferences(user_id)
            
            # Update with new values
            for key, value in updates.items():
                if key in current:
                    current[key] = value
            
            # Convert lists to JSON strings for SQLite
            for field in ['preferred_casinos', 'blocked_casinos', 'risk_profiles', 'preferred_sports', 'blocked_sports']:
                if isinstance(current[field], list):
                    current[field] = json.dumps(current[field])
            
            # Save to database
            self.db.execute(text("""
                INSERT OR REPLACE INTO user_preferences (
                    user_id, preferred_casinos, blocked_casinos,
                    risk_profiles, min_parlay_edge, max_parlay_legs,
                    notification_mode, max_daily_notifications,
                    preferred_sports, blocked_sports, bankroll,
                    updated_at
                ) VALUES (
                    :user_id, :preferred_casinos, :blocked_casinos,
                    :risk_profiles, :min_edge, :max_legs,
                    :notif_mode, :max_daily, :preferred_sports,
                    :blocked_sports, :bankroll, CURRENT_TIMESTAMP
                )
            """), {
                'user_id': user_id,
                'preferred_casinos': current['preferred_casinos'],
                'blocked_casinos': current['blocked_casinos'],
                'risk_profiles': current['risk_profiles'],
                'min_edge': current['min_parlay_edge'],
                'max_legs': current['max_parlay_legs'],
                'notif_mode': current['notification_mode'],
                'max_daily': current['max_daily_notifications'],
                'preferred_sports': current['preferred_sports'],
                'blocked_sports': current['blocked_sports'],
                'bankroll': current['bankroll']
            })
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            self.db.rollback()
            return False
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()


# Command handlers
@router.message(Command("parlay_settings"))
async def cmd_parlay_settings(message: types.Message):
    """Main settings menu for parlays"""
    logger.info(f"📋 /parlay_settings called by user {message.from_user.id}")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🏢 Sélectionner Casinos", callback_data="settings_casinos")],
        [types.InlineKeyboardButton(text="📊 Profil de Risque", callback_data="settings_risk")],
        [types.InlineKeyboardButton(text="🏀 Filtrer Sports", callback_data="settings_sports")],
        [types.InlineKeyboardButton(text="🔔 Notifications", callback_data="settings_notifications")],
        [types.InlineKeyboardButton(text="💰 Définir Bankroll", callback_data="settings_bankroll")],
        [types.InlineKeyboardButton(text="📈 Paramètres Avancés", callback_data="settings_advanced")]
    ])
    
    await message.answer(
        "⚙️ <b>PARAMÈTRES PARLAYS</b>\n\n"
        "Personnalisez votre expérience:\n\n"
        "• Choisissez vos casinos préférés\n"
        "• Définissez votre tolérance au risque\n"
        "• Filtrez par sports\n"
        "• Contrôlez les notifications\n"
        "• Suivez votre bankroll\n\n"
        "Que souhaitez-vous configurer?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "settings_casinos")
async def handle_casino_selection(callback: types.CallbackQuery):
    """Casino selection menu"""
    await callback.answer()
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(callback.from_user.id)
    selected = prefs.get('preferred_casinos', [])
    
    # Get available casinos from drop_events payload (hardcoded list for now)
    db = SessionLocal()
    
    # For now, use a hardcoded list of known casinos
    # TODO: Extract from drop_events payload JSON when structure is stable
    casino_list = [
        ('BET99', 142),
        ('Betsson', 98),
        ('bet365', 87),
        ('Pinnacle', 76),
        ('LeoVegas', 65),
        ('Sports Interaction', 54),
        ('BetVictor', 43),
        ('888sport', 32),
        ('Mise-o-jeu', 21),
        ('TonyBet', 19),
        ('Stake', 15),
        ('Casumo', 12),
        ('Coolbet', 8),
        ('iBet', 5)
    ]
    
    # Convert to match expected format
    class CasinoResult:
        def __init__(self, bookmaker, count):
            self.bookmaker = bookmaker
            self.count = count
    
    casinos = [CasinoResult(name, count) for name, count in casino_list]
    db.close()
    
    # Build keyboard
    keyboard_buttons = []
    for casino in casinos:
        name = casino.bookmaker
        count = casino.count
        is_selected = name in selected
        emoji = "✅" if is_selected else "⬜"
        
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"{emoji} {name} ({count} parlays)",
                callback_data=f"toggle_casino_{name[:20]}"  # Limit length
            )
        ])
    
    # Add control buttons
    keyboard_buttons.extend([
        [
            types.InlineKeyboardButton(text="✅ Tout Sélectionner", callback_data="casinos_select_all"),
            types.InlineKeyboardButton(text="❌ Tout Effacer", callback_data="casinos_clear_all")
        ],
        [types.InlineKeyboardButton(text="« Retour", callback_data="settings_main")]
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    selected_text = "Tous les casinos" if len(selected) == 0 else ", ".join(selected[:5])
    if len(selected) > 5:
        selected_text += f" (+{len(selected) - 5} autres)"
    
    await callback.message.edit_text(
        f"🏢 <b>SÉLECTIONNER CASINOS</b>\n\n"
        f"Choisissez les casinos pour recevoir des parlays:\n\n"
        f"<b>Actuellement sélectionnés:</b> {selected_text}\n\n"
        f"Cliquez pour basculer la sélection:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    manager.close()


@router.callback_query(F.data.startswith("toggle_casino_"))
async def handle_casino_toggle(callback: types.CallbackQuery):
    """Toggle casino selection"""
    await callback.answer()
    
    casino = callback.data.replace("toggle_casino_", "")
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    selected = prefs.get('preferred_casinos', [])
    
    # Toggle selection
    if casino in selected:
        selected.remove(casino)
        await callback.answer(f"❌ {casino} retiré")
    else:
        selected.append(casino)
        await callback.answer(f"✅ {casino} ajouté")
    
    # Save
    await manager.save_preferences(user_id, {'preferred_casinos': selected})
    manager.close()
    
    # Refresh menu
    await handle_casino_selection(callback)


@router.callback_query(F.data == "settings_risk")
async def handle_risk_profile_selection(callback: types.CallbackQuery):
    """Risk profile selection menu"""
    await callback.answer()
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(callback.from_user.id)
    selected = prefs.get('risk_profiles', ['BALANCED'])
    
    # Build keyboard
    keyboard_buttons = []
    
    for profile_key in ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE', 'LOTTERY']:
        profile = RISK_PROFILES[RiskProfile[profile_key]]
        is_selected = profile_key in selected
        emoji = "✅" if is_selected else "⬜"
        
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"{emoji} {profile['name_fr']}",
                callback_data=f"toggle_risk_{profile_key}"
            )
        ])
    
    keyboard_buttons.append([types.InlineKeyboardButton(text="« Retour", callback_data="settings_main")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Build descriptions
    descriptions = {
        'CONSERVATIVE': '🟢 Win rate: 50-55%, ROI: 8-12%',
        'BALANCED': '🟡 Win rate: 42-48%, ROI: 15-22%',
        'AGGRESSIVE': '🟠 Win rate: 30-38%, ROI: 25-40%',
        'LOTTERY': '🔴 Win rate: 8-15%, ROI: 50-150%+'
    }
    
    selected_desc = "\n".join([f"✅ <b>{p}</b>: {descriptions[p]}" for p in selected])
    
    await callback.message.edit_text(
        f"📊 <b>PROFIL DE RISQUE</b>\n\n"
        f"Sélectionnez votre tolérance au risque:\n\n"
        f"{selected_desc}\n\n"
        f"Vous pouvez sélectionner plusieurs profils pour recevoir une variété de parlays.",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    manager.close()


@router.callback_query(F.data.startswith("toggle_risk_"))
async def handle_risk_toggle(callback: types.CallbackQuery):
    """Toggle risk profile selection"""
    profile = callback.data.replace("toggle_risk_", "")
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    selected = prefs.get('risk_profiles', [])
    
    # Toggle selection
    if profile in selected:
        if len(selected) > 1:  # Keep at least one
            selected.remove(profile)
            await callback.answer(f"❌ {profile} retiré")
        else:
            await callback.answer("⚠️ Gardez au moins un profil", show_alert=True)
            return
    else:
        selected.append(profile)
        await callback.answer(f"✅ {profile} ajouté")
    
    # Save
    await manager.save_preferences(user_id, {'risk_profiles': selected})
    manager.close()
    
    # Refresh menu
    await handle_risk_profile_selection(callback)


@router.callback_query(F.data == "settings_notifications")
async def handle_notification_settings(callback: types.CallbackQuery):
    """Notification settings menu"""
    await callback.answer()
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(callback.from_user.id)
    
    mode = prefs.get('notification_mode', 'push')
    max_daily = prefs.get('max_daily_notifications', 10)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=f"{'🔔' if mode == 'push' else '⬜'} Notifications Push",
                callback_data="notif_mode_push"
            ),
            types.InlineKeyboardButton(
                text=f"{'📥' if mode == 'pull' else '⬜'} Manuel",
                callback_data="notif_mode_pull"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=f"Max par jour: {max_daily}",
                callback_data="notif_adjust_max"
            )
        ],
        [
            types.InlineKeyboardButton(text="➖", callback_data="notif_max_minus"),
            types.InlineKeyboardButton(text=f"{max_daily}", callback_data="noop"),
            types.InlineKeyboardButton(text="➕", callback_data="notif_max_plus")
        ],
        [types.InlineKeyboardButton(text="« Retour", callback_data="settings_main")]
    ])
    
    await callback.message.edit_text(
        f"🔔 <b>PARAMÈTRES NOTIFICATIONS</b>\n\n"
        f"<b>Mode actuel:</b> {'🔔 Push' if mode == 'push' else '📥 Manuel'}\n\n"
        f"<b>Mode Push:</b> Recevez les notifications dès que de nouveaux parlays sont trouvés\n"
        f"<b>Mode Manuel:</b> Utilisez /parlays pour vérifier les nouvelles opportunités\n\n"
        f"<b>Max Notifications/Jour:</b> {max_daily}",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    manager.close()


@router.callback_query(F.data.startswith("notif_mode_"))
async def handle_notification_mode(callback: types.CallbackQuery):
    """Change notification mode"""
    mode = callback.data.replace("notif_mode_", "")
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    await manager.save_preferences(user_id, {'notification_mode': mode})
    manager.close()
    
    await callback.answer(f"✅ Mode {'Push' if mode == 'push' else 'Manuel'} activé")
    await handle_notification_settings(callback)


@router.callback_query(F.data == "notif_max_minus")
async def handle_max_notif_decrease(callback: types.CallbackQuery):
    """Decrease max daily notifications"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('max_daily_notifications', 10)
    
    if current > 1:
        new_value = current - 1
        await manager.save_preferences(user_id, {'max_daily_notifications': new_value})
        await callback.answer(f"✅ Max: {new_value}/jour")
    else:
        await callback.answer("⚠️ Minimum: 1", show_alert=True)
    
    manager.close()
    await handle_notification_settings(callback)


@router.callback_query(F.data == "notif_max_plus")
async def handle_max_notif_increase(callback: types.CallbackQuery):
    """Increase max daily notifications"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('max_daily_notifications', 10)
    
    if current < 50:
        new_value = current + 1
        await manager.save_preferences(user_id, {'max_daily_notifications': new_value})
        await callback.answer(f"✅ Max: {new_value}/jour")
    else:
        await callback.answer("⚠️ Maximum: 50", show_alert=True)
    
    manager.close()
    await handle_notification_settings(callback)


@router.callback_query(F.data == "settings_bankroll")
async def handle_bankroll_setting(callback: types.CallbackQuery, state: FSMContext):
    """Start bankroll setting flow"""
    await callback.answer()
    
    await callback.message.edit_text(
        "💰 <b>DÉFINIR BANKROLL</b>\n\n"
        "Entrez votre bankroll totale (en $):\n\n"
        "Ceci aidera à calculer les mises recommandées.\n\n"
        "Exemples:\n"
        "• 1000\n"
        "• 5000\n"
        "• 10000\n\n"
        "Tapez le montant:",
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(ParlaySettingsStates.setting_bankroll)


@router.message(ParlaySettingsStates.setting_bankroll)
async def process_bankroll_input(message: types.Message, state: FSMContext):
    """Process bankroll input"""
    try:
        bankroll = float(message.text.replace('$', '').replace(',', ''))
        
        if bankroll < 100:
            await message.answer("⚠️ Bankroll minimum: $100")
            return
        
        if bankroll > 1000000:
            await message.answer("⚠️ Bankroll maximum: $1,000,000")
            return
        
        # Save bankroll
        manager = UserPreferencesManager()
        await manager.save_preferences(message.from_user.id, {'bankroll': bankroll})
        manager.close()
        
        await message.answer(
            f"✅ <b>Bankroll définie: ${bankroll:,.0f}</b>\n\n"
            f"Recommandations de mise:\n"
            f"• 🟢 Conservative: ${bankroll * 0.025:,.0f} (2.5%)\n"
            f"• 🟡 Balanced: ${bankroll * 0.015:,.0f} (1.5%)\n"
            f"• 🟠 Aggressive: ${bankroll * 0.0075:,.0f} (0.75%)\n"
            f"• 🔴 Lottery: $10-20 fixe\n\n"
            f"Utilisez /parlay_settings pour ajuster d'autres paramètres.",
            parse_mode=ParseMode.HTML
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Montant invalide. Entrez un nombre (ex: 5000)")


@router.callback_query(F.data == "settings_advanced")
async def handle_advanced_settings(callback: types.CallbackQuery):
    """Advanced settings menu"""
    await callback.answer()
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(callback.from_user.id)
    
    min_edge = int(prefs.get('min_parlay_edge', 0.10) * 100)
    max_legs = prefs.get('max_parlay_legs', 3)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=f"Edge Minimum: {min_edge}%",
                callback_data="noop"
            )
        ],
        [
            types.InlineKeyboardButton(text="➖", callback_data="edge_minus"),
            types.InlineKeyboardButton(text=f"{min_edge}%", callback_data="noop"),
            types.InlineKeyboardButton(text="➕", callback_data="edge_plus")
        ],
        [
            types.InlineKeyboardButton(
                text=f"Max Legs: {max_legs}",
                callback_data="noop"
            )
        ],
        [
            types.InlineKeyboardButton(text="➖", callback_data="legs_minus"),
            types.InlineKeyboardButton(text=f"{max_legs}", callback_data="noop"),
            types.InlineKeyboardButton(text="➕", callback_data="legs_plus")
        ],
        [types.InlineKeyboardButton(text="« Retour", callback_data="settings_main")]
    ])
    
    await callback.message.edit_text(
        f"📈 <b>PARAMÈTRES AVANCÉS</b>\n\n"
        f"<b>Edge Minimum:</b> {min_edge}%\n"
        f"Ne recevoir que des parlays avec au moins {min_edge}% d'avantage\n\n"
        f"<b>Max Legs:</b> {max_legs}\n"
        f"Nombre maximum de paris dans un parlay\n\n"
        f"💡 Recommandations:\n"
        f"• Débutants: Edge 10%+, Max 2 legs\n"
        f"• Intermédiaire: Edge 8%+, Max 3 legs\n"
        f"• Avancé: Edge 5%+, Max 4 legs",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    manager.close()


@router.callback_query(F.data == "settings_main")
async def handle_back_to_main(callback: types.CallbackQuery):
    """Go back to main settings menu"""
    # Create a new message object from callback
    await cmd_parlay_settings(callback.message)
    await callback.answer()

@router.callback_query(F.data == "settings_sports")
async def handle_sports_filter(callback: types.CallbackQuery):
    """Sports filtering menu"""
    await callback.answer()
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(callback.from_user.id)
    blocked_sports = prefs.get('blocked_sports', [])
    
    # Available sports
    sports = ['NBA', 'NHL', 'NFL', 'MLB', 'Soccer', 'Tennis']
    
    keyboard_buttons = []
    for sport in sports:
        is_blocked = sport in blocked_sports
        emoji = "🚫" if is_blocked else "✅"
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"{emoji} {sport}",
                callback_data=f"toggle_sport_{sport}"
            )
        ])
    
    keyboard_buttons.append([types.InlineKeyboardButton(text="« Retour", callback_data="settings_main")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "🏀 <b>FILTRER SPORTS</b>\n\n"
        "✅ = Autorisé\n"
        "🚫 = Bloqué\n\n"
        "Cliquez pour basculer:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    manager.close()

@router.callback_query(F.data.startswith("toggle_sport_"))
async def handle_sport_toggle(callback: types.CallbackQuery):
    """Toggle sport blocking"""
    sport = callback.data.replace("toggle_sport_", "")
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    blocked_sports = prefs.get('blocked_sports', [])
    
    if sport in blocked_sports:
        blocked_sports.remove(sport)
        await callback.answer(f"✅ {sport} autorisé")
    else:
        blocked_sports.append(sport)
        await callback.answer(f"🚫 {sport} bloqué")
    
    await manager.save_preferences(user_id, {'blocked_sports': blocked_sports})
    manager.close()
    await handle_sports_filter(callback)

@router.callback_query(F.data == "casinos_select_all")
async def handle_casinos_select_all(callback: types.CallbackQuery):
    """Select all casinos"""
    user_id = callback.from_user.id
    
    # Get all casino names
    casino_list = [
        'BET99', 'Betsson', 'bet365', 'Pinnacle', 'LeoVegas',
        'Sports Interaction', 'BetVictor', '888sport', 'Mise-o-jeu',
        'TonyBet', 'Stake', 'Casumo', 'Coolbet', 'iBet'
    ]
    
    manager = UserPreferencesManager()
    await manager.save_preferences(user_id, {'preferred_casinos': casino_list})
    manager.close()
    
    await callback.answer("✅ Tous les casinos sélectionnés")
    await handle_casino_selection(callback)

@router.callback_query(F.data == "casinos_clear_all")
async def handle_casinos_clear_all(callback: types.CallbackQuery):
    """Clear all casino selections"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    await manager.save_preferences(user_id, {'preferred_casinos': []})
    manager.close()
    
    await callback.answer("❌ Sélection effacée")
    await handle_casino_selection(callback)

@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    """No operation - for display only buttons"""
    await callback.answer()

@router.callback_query(F.data == "edge_minus")
async def handle_edge_decrease(callback: types.CallbackQuery):
    """Decrease minimum edge"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('min_parlay_edge', 0.10)
    
    if current > 0.05:
        new_value = max(0.05, current - 0.01)
        await manager.save_preferences(user_id, {'min_parlay_edge': new_value})
        await callback.answer(f"✅ Edge min: {int(new_value*100)}%")
    else:
        await callback.answer("⚠️ Minimum: 5%", show_alert=True)
    
    manager.close()
    await handle_advanced_settings(callback)

@router.callback_query(F.data == "edge_plus")
async def handle_edge_increase(callback: types.CallbackQuery):
    """Increase minimum edge"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('min_parlay_edge', 0.10)
    
    if current < 0.30:
        new_value = min(0.30, current + 0.01)
        await manager.save_preferences(user_id, {'min_parlay_edge': new_value})
        await callback.answer(f"✅ Edge min: {int(new_value*100)}%")
    else:
        await callback.answer("⚠️ Maximum: 30%", show_alert=True)
    
    manager.close()
    await handle_advanced_settings(callback)

@router.callback_query(F.data == "legs_minus")
async def handle_legs_decrease(callback: types.CallbackQuery):
    """Decrease max legs"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('max_parlay_legs', 3)
    
    if current > 2:
        new_value = current - 1
        await manager.save_preferences(user_id, {'max_parlay_legs': new_value})
        await callback.answer(f"✅ Max legs: {new_value}")
    else:
        await callback.answer("⚠️ Minimum: 2 legs", show_alert=True)
    
    manager.close()
    await handle_advanced_settings(callback)

@router.callback_query(F.data == "legs_plus")
async def handle_legs_increase(callback: types.CallbackQuery):
    """Increase max legs"""
    user_id = callback.from_user.id
    
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    current = prefs.get('max_parlay_legs', 3)
    
    if current < 5:
        new_value = current + 1
        await manager.save_preferences(user_id, {'max_parlay_legs': new_value})
        await callback.answer(f"✅ Max legs: {new_value}")
    else:
        await callback.answer("⚠️ Maximum: 5 legs", show_alert=True)
    
    manager.close()
    await handle_advanced_settings(callback)

@router.callback_query(F.data.startswith("view_casino_"))
async def handle_view_casino_parlays(callback: types.CallbackQuery):
    """View parlays for a specific casino with pagination"""
    await callback.answer()
    
    # Check if user is ALPHA (PREMIUM)
    user_id = callback.from_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    db.close()
    
    if not user or user.tier != TierLevel.PREMIUM:
        # FREE user - show upgrade message
        await callback.message.edit_text(
            "🔒 <b>RÉSERVÉ AUX ALPHA</b>\n\n"
            "Les parlays sont une fonctionnalité exclusive pour les membres ALPHA.\n\n"
            "Active ALPHA pour accéder aux parlays optimisés!",
            parse_mode=ParseMode.HTML,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="👑 Devenir ALPHA", callback_data="show_tiers")],
                [types.InlineKeyboardButton(text="« Retour Menu", callback_data="main_menu")]
            ])
        )
        return
    
    # Parse callback data (format: view_casino_CasinoName or view_casino_CasinoName_page_2)
    parts = callback.data.replace("view_casino_", "").split("_page_")
    casino = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 1
    
    # Get parlays for this casino
    db = SessionLocal()
    result = db.execute(text("""
        SELECT * FROM parlays
        WHERE date(created_at) = date('now')
            AND status = 'pending'
        ORDER BY quality_score DESC, calculated_edge DESC
    """))
    
    parlays = result.fetchall()
    db.close()
    
    # Filter for this casino - EXACT MATCH ONLY
    casino_parlays = []
    for parlay in parlays:
        # Parse bookmakers JSON
        if isinstance(parlay.bookmakers, str):
            try:
                bookmakers = json.loads(parlay.bookmakers)
            except:
                bookmakers = []
        else:
            bookmakers = parlay.bookmakers or []
        
        # ONLY include if parlay is AVAILABLE on this specific casino
        # (not just if it appears in the bookmaker list)
        if casino in bookmakers:
            casino_parlays.append(parlay)
    
    if not casino_parlays:
        await callback.message.edit_text(
            f"📭 <b>AUCUN PARLAY POUR {casino}</b>\n\n"
            "Aucun parlay disponible pour ce casino aujourd'hui.",
            parse_mode=ParseMode.HTML,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="« Retour", callback_data="back_to_parlays")
            ]])
        )
        return
    
    # PAGINATION: 2 parlays per page to avoid MESSAGE_TOO_LONG
    PARLAYS_PER_PAGE = 2
    total_parlays = len(casino_parlays)
    total_pages = (total_parlays + PARLAYS_PER_PAGE - 1) // PARLAYS_PER_PAGE  # Ceiling division
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    # Get parlays for current page
    start_idx = (page - 1) * PARLAYS_PER_PAGE
    end_idx = start_idx + PARLAYS_PER_PAGE
    page_parlays = casino_parlays[start_idx:end_idx]
    
    # Build response
    response_text = (
        f"🏢 <b>PARLAYS {casino}</b>\n"
        f"Page {page}/{total_pages} ({total_parlays} total)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # Display parlays for this page
    for i, parlay in enumerate(page_parlays, start=start_idx + 1):
        # Parse leg count
        legs = parlay.leg_count or 2
        
        # Format odds
        if parlay.combined_american_odds > 0:
            odds_str = f"+{parlay.combined_american_odds}"
        else:
            odds_str = str(parlay.combined_american_odds)
        
        # Risk emoji and description
        risk_info = {
            'CONSERVATIVE': ('🟢', 'Sûr', '50-55% win rate'),
            'BALANCED': ('🟡', 'Équilibré', '42-48% win rate'),
            'AGGRESSIVE': ('🟠', 'Risqué', '30-38% win rate'),
            'LOTTERY': ('🔴', 'Loterie', '8-15% win rate')
        }.get(parlay.risk_profile, ('⚪', 'Unknown', 'N/A'))
        
        response_text += (
            f"<b>PARLAY #{i}</b> - {risk_info[0]} {risk_info[1]}\n"
            f"<b>{legs} legs</b> (2-3 legs = meilleur ROI long terme)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        # Check if we have match details
        legs_detail = []
        if hasattr(parlay, 'legs_detail') and parlay.legs_detail:
            try:
                legs_detail = json.loads(parlay.legs_detail)
            except:
                pass
        
        if legs_detail:
            # Show PROFESSIONAL match details
            for j, leg in enumerate(legs_detail, 1):
                # Sport emoji
                sport = leg.get('sport', 'Sports')
                sport_emoji = {'NBA': '🏀', 'NHL': '🏒', 'NFL': '🏈', 'MLB': '⚾', 'MLS': '⚽'}.get(sport, '🎯')
                
                # Format odds CORRECTLY
                american_odds = leg.get('american_odds', 100)
                
                # Convert to int if string
                try:
                    american_odds = int(american_odds)
                except (ValueError, TypeError):
                    american_odds = 100
                
                # Calculate decimal from american (correct math!)
                if american_odds > 0:
                    decimal_odds = (american_odds / 100) + 1
                    american_str = f"+{american_odds}"
                elif american_odds < 0:
                    decimal_odds = (100 / abs(american_odds)) + 1
                    american_str = str(american_odds)
                else:
                    decimal_odds = leg.get('odds', 2.0)
                    american_str = "+100"
                
                # Parse market to show WHAT we're betting
                market = leg.get('market', 'Unknown')
                match = leg.get('match', '')
                bet_description = market
                
                # Extract teams for context (replace @ with vs)
                teams_display = match.replace('@', 'vs') if match else ''
                teams = match.split('@') if '@' in match else match.split('vs') if 'vs' in match else []
                
                # Try to make it clearer
                if 'ML' in market.upper() or 'MONEYLINE' in market.upper():
                    # Moneyline
                    if len(teams) == 2:
                        # Assume market contains winner
                        if teams[1].strip() in market:
                            bet_description = f"✅ {teams[1].strip()} GAGNE"
                        elif teams[0].strip() in market:
                            bet_description = f"✅ {teams[0].strip()} GAGNE"
                        else:
                            bet_description = f"Moneyline: {market}"
                    else:
                        bet_description = f"Moneyline: {market}"
                        
                elif 'OVER' in market.upper() or 'UNDER' in market.upper():
                    # Over/Under - GARDER le contexte de ce qu'on bet!
                    direction = '📈' if 'OVER' in market.upper() else '📉'
                    direction_text = 'Over' if 'OVER' in market.upper() else 'Under'
                    
                    # Extract number (220.5, 59.5, etc.)
                    import re
                    numbers = re.findall(r'\d+\.?\d*', market)
                    line_number = numbers[0] if numbers else ''
                    
                    # Check if it's player prop or team total
                    if 'PLAYER' in market.upper():
                        # Player prop - garder tout
                        bet_description = f"👤 {market}"
                    elif 'TOTAL POINTS' in market.upper() or 'TOTALS' in market.upper():
                        # Total des deux équipes
                        bet_description = f"{direction} Total du match - {direction_text} {line_number} points"
                    elif 'TEAM TOTAL' in market.upper():
                        # Total d'une équipe spécifique
                        bet_description = f"{direction} {market}"
                    elif teams_display and line_number:
                        # Generic over/under - garder le market original mais ajouter le match
                        # Enlever juste Over/Under du market pour éviter duplication
                        market_clean = market.replace('Over', '').replace('Under', '').replace('OVER', '').replace('UNDER', '').strip()
                        if market_clean and market_clean != line_number:
                            bet_description = f"{direction} {market_clean} - {direction_text} {line_number}"
                        else:
                            # Si market_clean est vide ou juste le numéro, utiliser un défaut
                            bet_description = f"{direction} Total - {direction_text} {line_number}"
                    else:
                        # Fallback: garder le market original
                        bet_description = f"{direction} {market}"
                        
                elif 'SPREAD' in market.upper() or ('+' in market and len(teams) > 0) or ('-' in market and len(teams) > 0):
                    # Spread with context
                    if teams_display:
                        bet_description = f"📊 {teams_display} - {market}"
                    else:
                        bet_description = f"📊 {market}"
                        
                elif 'PLAYER' in market.upper():
                    bet_description = f"👤 {market}"
                else:
                    # Default: just show market
                    bet_description = market
                
                # Format match display (replace @ with vs)
                match_display = leg.get('match', 'Unknown Match').replace('@', 'vs')
                
                response_text += (
                    f"\n<b>🎯 LEG {j} – {sport}</b>\n"
                    f"{sport_emoji} {match_display}\n"
                    f"⏰ {leg.get('time', 'Today 7:00 PM ET')}\n\n"
                    f"<b>PARI: {bet_description}</b>\n"
                    f"<b>COTES: {american_str} (≈{decimal_odds:.2f} décimal)</b>\n"
                )
                
                # Show API support status (simplified)
                api_supported = leg.get('api_supported', False)
                if api_supported is True:
                    response_text += f"\n✅ Vérifiable automatiquement\n"
                else:
                    response_text += f"\n⚠️ À vérifier manuellement sur {casino}\n"
                
                # Add WHY it's +EV (HONNÊTE - pas de garanties!)
                edge = leg.get('edge', 0)
                if edge > 0:
                    response_text += f"\n📈 <b>Edge estimé: +{edge:.1f}% de value</b>\n"
                    response_text += f"   (théorique, pas un profit garanti)\n"
                
                # Add link if available (only if not a non-supported bookmaker)
                if 'link' in leg and leg['link']:
                    # Check if it's a real deep link or just a fallback
                    link_url = leg['link']
                    # Bookmakers not supported by The Odds API shouldn't show "open match" link
                    non_api_bookmakers = ['Mise-o-jeu', 'BET99', 'Coolbet', 'LeoVegas']
                    if any(bk.lower() in casino.lower() for bk in non_api_bookmakers):
                        response_text += f"\n💡 <i>Recherchez manuellement ce match sur {casino}</i>\n"
                    else:
                        response_text += f"\n<a href=\"{link_url}\">🔗 Ouvrir le match sur {casino}</a>\n"
                
                response_text += "━━━━━━━━━━━━━━━\n"
        else:
            # Fallback to generic info
            response_text += f"\n{legs} matchs combinés (détails à venir)\n"
        
        # Add CLEAR section: WHERE TO PLACE THIS PARLAY
        response_text += (
            f"\n🎯 <b>PARLAY À PLACER (chez {casino})</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Combiner en 1 SEUL parlay :</b>\n\n"
        )
        
        # List legs clearly
        if legs_detail:
            for j, leg in enumerate(legs_detail, 1):
                market = leg.get('market', 'Unknown')
                # Simplify for listing
                if 'ML' in market.upper():
                    match = leg.get('match', '')
                    teams = match.split('@') if '@' in match else match.split('vs')
                    if len(teams) == 2 and teams[1].strip() in market:
                        simple_desc = f"{teams[1].strip()} gagne"
                    else:
                        simple_desc = market
                else:
                    simple_desc = market
                response_text += f"{j}) {simple_desc}\n"
        
        # Calculate profits for different stakes
        decimal_odds = parlay.combined_decimal_odds or 2.0
        profit_10 = (10 * decimal_odds) - 10
        profit_20 = (20 * decimal_odds) - 20
        profit_50 = (50 * decimal_odds) - 50
        
        response_text += (
            f"\n<b>Cote totale:</b> {odds_str} ({decimal_odds:.2f}x décimal)\n\n"
            f"<b>💰 EXEMPLES DE MISE :</b>\n"
            f"• Mise 10$ → Retour {int(10 * decimal_odds)}$ → <b>Profit +{int(profit_10)}$</b>\n"
            f"• Mise 20$ → Retour {int(20 * decimal_odds)}$ → <b>Profit +{int(profit_20)}$</b>\n"
            f"• Mise 50$ → Retour {int(50 * decimal_odds)}$ → <b>Profit +{int(profit_50)}$</b>\n\n"
            f"📊 <b>Estimation théorique (non garantie) :</b>\n"
            f"• Edge global estimé: ≈+{int(parlay.calculated_edge * 100)}% de value\n"
            f"• Win rate basé sur modèle interne\n"
            f"  (résultats réels peuvent différer fortement)\n\n"
            f"💡 <b>Gestion de bankroll (conseil générique):</b>\n"
            f"• Taille recommandée: {parlay.stake_guidance}\n\n"
        )
    
    # Build navigation buttons
    nav_buttons = []
    
    # Pagination row
    if total_pages > 1:
        pagination_row = []
        
        # Previous button (only if not on first page)
        if page > 1:
            pagination_row.append(
                types.InlineKeyboardButton(
                    text="◀️ Précédent",
                    callback_data=f"view_casino_{casino}_page_{page-1}"
                )
            )
        
        # Page indicator
        pagination_row.append(
            types.InlineKeyboardButton(
                text=f"📄 {page}/{total_pages}",
                callback_data="noop"  # Non-clickable
            )
        )
        
        # Next button (only if not on last page)
        if page < total_pages:
            pagination_row.append(
                types.InlineKeyboardButton(
                    text="Suivant ▶️",
                    callback_data=f"view_casino_{casino}_page_{page+1}"
                )
            )
        
        nav_buttons.append(pagination_row)
    
    # Action buttons
    nav_buttons.append([
        types.InlineKeyboardButton(text="📝 Placer Pari", callback_data=f"place_parlay_{casino}"),
        types.InlineKeyboardButton(text="🔍 Vérifier Cotes", callback_data=f"verify_odds_{casino}_page_{page}")
    ])
    nav_buttons.append([
        types.InlineKeyboardButton(text="« Retour aux Parlays", callback_data="back_to_parlays")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=nav_buttons)
    
    await callback.message.edit_text(
        response_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    """Handle non-clickable buttons"""
    await callback.answer()  # Just acknowledge, do nothing

@router.callback_query(F.data.startswith("verify_odds_"))
async def handle_verify_odds(callback: types.CallbackQuery):
    """Verify parlay odds in real-time with rate limiting"""
    user_id = callback.from_user.id
    
    # Check if user is ALPHA (PREMIUM)
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    db.close()
    
    if not user or user.tier != TierLevel.PREMIUM:
        # FREE user - show upgrade message
        await callback.answer("🔒 Fonctionnalité ALPHA uniquement", show_alert=True)
        return
    
    # Rate limiting: max 1 verification per 5 minutes
    rate_limit_key = f"verify_odds_{user_id}"
    now = datetime.now()
    
    if rate_limit_key in rate_limits:
        last_check = rate_limits[rate_limit_key]
        time_since = (now - last_check).total_seconds()
        
        if time_since < 300:  # 5 minutes = 300 seconds
            remaining = int(300 - time_since)
            minutes = remaining // 60
            seconds = remaining % 60
            await callback.answer(
                f"⏱️ Attendez {minutes}m {seconds}s avant de vérifier à nouveau",
                show_alert=True
            )
            return
    
    # Update rate limit
    rate_limits[rate_limit_key] = now
    
    await callback.answer("🔍 Vérification en cours...")
    
    # Parse callback data
    parts = callback.data.replace("verify_odds_", "").split("_page_")
    casino = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 1
    
    # Get parlays for this page
    db = SessionLocal()
    result = db.execute(text("""
        SELECT * FROM parlays
        WHERE date(created_at) = date('now')
            AND status = 'pending'
        ORDER BY quality_score DESC, calculated_edge DESC
    """))
    
    parlays = result.fetchall()
    db.close()
    
    # Filter for casino
    casino_parlays = []
    for parlay in parlays:
        if isinstance(parlay.bookmakers, str):
            try:
                bookmakers = json.loads(parlay.bookmakers)
            except:
                bookmakers = []
        else:
            bookmakers = parlay.bookmakers or []
        
        if casino in bookmakers:
            casino_parlays.append(parlay)
    
    # VÉRIFIER SEULEMENT LA PAGE ACTUELLE (économise les appels API!)
    PARLAYS_PER_PAGE = 2
    start_idx = (page - 1) * PARLAYS_PER_PAGE
    end_idx = start_idx + PARLAYS_PER_PAGE
    page_parlays = casino_parlays[start_idx:end_idx]
    
    if not page_parlays:
        await callback.message.edit_text(
            "❌ Aucun parlay à vérifier sur cette page\n\n"
            "Utilisez les boutons pour naviguer.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Import verifier
    try:
        from utils.odds_verifier import OddsVerifier
        verifier = OddsVerifier()
    except:
        await callback.message.edit_text(
            "❌ Service de vérification temporairement indisponible\n\n"
            "Réessayez plus tard.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Import smart updater
    try:
        from smart_parlay_updater import SmartParlayUpdater
        updater = SmartParlayUpdater()
        smart_updates = True
    except:
        smart_updates = False
    
    # Verify each parlay
    total_to_verify = len(page_parlays)
    total_pages = (len(casino_parlays) + PARLAYS_PER_PAGE - 1) // PARLAYS_PER_PAGE
    
    verification_text = f"🔍 <b>VÉRIFICATION INTELLIGENTE - {casino}</b>\n"
    verification_text += f"Page {page}/{total_pages} - {total_to_verify} parlay{'s' if total_to_verify > 1 else ''}\n"
    verification_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    actions_taken = {'kept': 0, 'updated': 0, 'replaced': 0, 'deleted': 0}
    
    for i, parlay in enumerate(page_parlays, start=start_idx + 1):
        # Parse legs
        legs_detail = []
        if hasattr(parlay, 'legs_detail') and parlay.legs_detail:
            try:
                legs_detail = json.loads(parlay.legs_detail)
            except:
                pass
        
        if not legs_detail:
            continue
        
        verification_text += f"<b>PARLAY #{i}</b>\n"
        
        # Use smart updater to decide action
        if smart_updates:
            action_result = await updater.smart_update_parlay(parlay.parlay_id)
            actions_taken[action_result['action']] += 1
            
            verification_text += f"{action_result['message']}\n"
            
            if action_result['changes']:
                for change in action_result['changes']:
                    verification_text += f"  • {change}\n"
        else:
            # Fallback: just verify without smart updates
            verification = await verifier.verify_parlay_odds(legs_detail)
            
            if verification['overall_status'] == 'all_good':
                verification_text += "✅ <b>Toutes les cotes valides!</b>\n"
            elif verification['overall_status'] == 'odds_better':
                verification_text += "📈 <b>Certaines cotes se sont AMÉLIORÉES!</b>\n"
            elif verification['overall_status'] == 'odds_worse':
                verification_text += "📉 <b>ATTENTION: Certaines cotes ont BAISSÉ!</b>\n"
            elif verification['overall_status'] == 'some_unavailable':
                verification_text += "⚠️ <b>Certains paris ne sont plus disponibles!</b>\n"
        
        verification_text += "\n"
    
    # Add summary with smart actions
    if smart_updates:
        verification_text += (
            f"<b>📊 ACTIONS INTELLIGENTES:</b>\n"
            f"✅ Gardés: {actions_taken['kept']}\n"
            f"🔄 Mis à jour: {actions_taken['updated']}\n"
            f"🔄 Remplacés: {actions_taken['replaced']}\n"
            f"❌ Supprimés: {actions_taken['deleted']}\n\n"
            f"<i>💡 Les parlays ont été automatiquement optimisés</i>\n"
            f"<i>Dernière vérification: {now.strftime('%H:%M:%S')}</i>\n"
            f"<i>Prochaine vérification possible dans 5 minutes</i>"
        )
        
        # Close updater
        updater.close()
    else:
        verification_text += (
            f"<b>📊 RÉSUMÉ:</b>\n"
            f"<i>Vérification basique effectuée</i>\n\n"
            f"<i>Dernière vérification: {now.strftime('%H:%M:%S')}</i>\n"
            f"<i>Prochaine vérification possible dans 5 minutes</i>"
        )
    
    # IMPORTANT: Keep original parlay message and ADD verification below
    # Get the original message text
    original_text = callback.message.text or callback.message.caption or ""
    
    # Find where the parlay info ends (before buttons/footer)
    # Usually ends with the last "━━━" or before navigation buttons info
    if "━━━━━━━━━━━━━━━━━━━━" in original_text:
        # Keep everything up to verification section
        parts = original_text.split("🔍 <b>VÉRIFICATION")
        base_message = parts[0].rstrip()
    else:
        base_message = original_text
    
    # Combine original + verification
    full_message = base_message + "\n\n" + verification_text
    
    # Add back button
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="« Retour aux Parlays", callback_data="back_to_parlays")]
    ])
    
    # Edit message to show BOTH original + verification results
    await callback.message.edit_text(
        full_message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("place_parlay_"))
async def handle_place_parlay(callback: types.CallbackQuery):
    """Explain how to place the parlay"""
    await callback.answer()
    casino = callback.data.replace("place_parlay_", "")
    
    instructions = (
        f"📝 <b>COMMENT PLACER CE PARLAY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Le bot ne place PAS les paris pour toi!\n"
        f"Voici ce que TU dois faire:\n\n"
        f"1️⃣ <b>Ouvre {casino}</b> sur ton téléphone/ordi\n"
        f"2️⃣ <b>Connecte-toi</b> à ton compte\n"
        f"3️⃣ <b>Va dans 'Parlay'</b> ou 'Pari Combiné'\n"
        f"4️⃣ <b>Ajoute les matchs</b> un par un\n"
        f"5️⃣ <b>Vérifie la cote totale</b>\n"
        f"6️⃣ <b>Place ta mise</b> (1-2% de ta bankroll)\n\n"
        f"⚠️ <b>IMPORTANT:</b>\n"
        f"• Les cotes peuvent avoir changé\n"
        f"• Vérifie toujours l'edge est positif\n"
        f"• Ne mise JAMAIS plus que conseillé\n"
        f"• Si une cote a trop bougé, skip!\n\n"
        f"💡 <b>Astuce:</b> Screenshot ce message pour référence!"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Compris!", callback_data=f"view_casino_{casino}")],
        [types.InlineKeyboardButton(text="« Retour", callback_data="back_to_parlays")]
    ])
    
    await callback.message.edit_text(
        instructions,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def _build_parlays_list(user_id: int):
    """Build parlays list content (shared by command and callback)"""
    # Check if user is ALPHA (PREMIUM)
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    db.close()
    
    if not user or user.tier != TierLevel.PREMIUM:
        # FREE user - show upgrade message
        return {
            'text': (
                "🔒 <b>RÉSERVÉ AUX ALPHA</b>\n\n"
                "Les parlays sont une fonctionnalité exclusive pour les membres ALPHA.\n\n"
                "Active ALPHA pour:\n"
                "• 📊 Voir les derniers appels par type\n"
                "• 🎲 Accéder aux parlays optimisés\n"
                "• 💎 Notifications illimitées\n"
                "• 🚀 Et bien plus!\n\n"
                "Rejoins ALPHA maintenant!"
            ),
            'keyboard': types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="👑 Devenir ALPHA", callback_data="show_tiers")],
                [types.InlineKeyboardButton(text="« Retour Menu", callback_data="main_menu")]
            ])
        }
    
    # Get user preferences
    manager = UserPreferencesManager()
    prefs = await manager.get_preferences(user_id)
    
    # Get today's parlays
    db = SessionLocal()
    result = db.execute(text("""
        SELECT * FROM parlays
        WHERE date(created_at) = date('now')
            AND status = 'pending'
        ORDER BY quality_score DESC, calculated_edge DESC
        LIMIT 50
    """))
    
    parlays = result.fetchall()
    
    if not parlays:
        db.close()
        manager.close()
        return {
            'text': (
                "📭 <b>AUCUN PARLAY DISPONIBLE</b>\n\n"
                "Aucun parlay ne correspond à vos préférences aujourd'hui.\n\n"
                "Essayez d'ajuster vos paramètres:\n"
                "/parlay_settings"
            ),
            'keyboard': types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="« Retour Menu", callback_data="menu")
            ]])
        }
    
    # Filter by user preferences
    filtered = []
    
    for parlay in parlays:
        # Parse JSON fields if they're strings
        if isinstance(parlay.bookmakers, str):
            try:
                parlay_casinos = json.loads(parlay.bookmakers)
            except:
                parlay_casinos = []
        else:
            parlay_casinos = parlay.bookmakers or []
        
        # Check risk profile
        if prefs['risk_profiles'] and parlay.risk_profile:
            if parlay.risk_profile not in prefs['risk_profiles']:
                continue
        
        # Check max legs
        if parlay.leg_count and parlay.leg_count > prefs['max_parlay_legs']:
            continue
        
        # Check casinos - ONLY if user has preferences set
        # If no preferences, show ALL casinos
        if prefs['preferred_casinos'] and len(prefs['preferred_casinos']) > 0:
            if parlay_casinos:  # Only filter if parlay has casino info
                match_found = False
                for pc in parlay_casinos:
                    for uc in prefs['preferred_casinos']:
                        if pc.lower() == uc.lower():
                            match_found = True
                            break
                    if match_found:
                        break
                if not match_found:
                    print(f"  → Filtered out: casino mismatch. Parlay casinos: {parlay_casinos}, User prefs: {prefs['preferred_casinos']}")
                    continue
        
        filtered.append((parlay, parlay_casinos))
    
    # Group by casino
    by_casino = {}
    for parlay_tuple in filtered[:20]:
        parlay, parlay_casinos = parlay_tuple
        casinos = parlay_casinos if parlay_casinos else ['Unknown']
        for casino in casinos:
            if casino not in by_casino:
                by_casino[casino] = []
            by_casino[casino].append(parlay)
    
    # Build keyboard
    keyboard_buttons = []
    for casino, casino_parlays in by_casino.items():
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"🏢 {casino} ({len(casino_parlays)} parlays)",
                callback_data=f"view_casino_{casino[:15]}"
            )
        ])
    
    # Add back button
    keyboard_buttons.append([
        types.InlineKeyboardButton(text="« Retour Menu", callback_data="menu")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    message_text = (
        f"🎯 <b>PARLAYS D'AUJOURD'HUI</b>\n\n"
        f"Trouvé {len(filtered)} parlays correspondant à vos préférences:\n\n"
        f"{chr(10).join(f'🏢 <b>{casino}</b>: {len(ps)} parlays' for casino, ps in by_casino.items())}\n\n"
        f"Sélectionnez un casino pour voir les parlays disponibles:"
    )
    
    db.close()
    manager.close()
    
    return {'text': message_text, 'keyboard': keyboard}


@router.callback_query(F.data == "back_to_parlays")
async def handle_back_to_parlays(callback: types.CallbackQuery):
    """Go back to parlays list - EDIT message"""
    await callback.answer()
    content = await _build_parlays_list(callback.from_user.id)
    await callback.message.edit_text(
        content['text'],
        parse_mode=ParseMode.HTML,
        reply_markup=content['keyboard']
    )


# View available parlays command
@router.message(Command("parlays"))
async def cmd_view_parlays(message: types.Message):
    """View available parlays (pull mode)"""
    user_id = message.from_user.id
    content = await _build_parlays_list(user_id)
    await message.answer(
        content['text'],
        parse_mode=ParseMode.HTML,
        reply_markup=content['keyboard']
    )


# Manual odds reporting command
@router.message(Command("report_odds"))
async def cmd_report_odds(message: types.Message):
    """Report odds change manually"""
    user_id = message.from_user.id
    
    # Get user's active bets
    db = SessionLocal()
    result = db.execute(text("""
        SELECT 
            id, match_name, bookmaker, bet_type,
            total_stake, expected_profit, bet_date
        FROM user_bets
        WHERE user_id = :user_id
            AND status = 'pending'
            AND match_date >= date('now')
        ORDER BY bet_date DESC
        LIMIT 10
    """), {'user_id': user_id})
    
    bets = result.fetchall()
    db.close()
    
    if not bets:
        await message.answer(
            "📭 <b>AUCUN PARI ACTIF</b>\n\n"
            "Vous n'avez aucun pari actif pour signaler des changements de cotes.\n\n"
            "Placez d'abord un pari avec /menu",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Show bets with buttons
    keyboard_buttons = []
    for bet in bets:
        button_text = f"{bet.bookmaker or 'Unknown'} - {bet.match_name or 'Match'} (${bet.total_stake:.0f})"
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=button_text[:50],  # Limit length
                callback_data=f"report_odds_{bet.id}"
            )
        ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        "📊 <b>SIGNALER CHANGEMENT DE COTES</b>\n\n"
        "Sélectionnez le pari dont les cotes ont changé:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
