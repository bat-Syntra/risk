"""
Final Admin Actions - Add/Remove admins, Request Broadcast, History
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from datetime import datetime
from sqlalchemy import text
import json
import logging

from database import SessionLocal
from models.user import User
from bot.admin_approval_system import (
    get_user_role, is_super_admin, is_any_admin, 
    request_action_approval, SUPER_ADMIN_ID
)

logger = logging.getLogger(__name__)
router = Router()


# FSM States
class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_broadcast_message = State()


@router.callback_query(F.data == "add_admin_prompt")
async def handle_add_admin_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Prompt to add a new admin"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    text = (
        "➕ <b>AJOUTER UN ADMIN</b>\n\n"
        "Envoie le <b>Telegram ID</b> ou <b>@username</b> de la personne que tu veux promouvoir admin.\n\n"
        "Les admins réguliers auront accès à:\n"
        "✅ Users\n"
        "✅ Stats\n"
        "✅ Feedbacks\n\n"
        "Mais PAS à:\n"
        "❌ Database\n"
        "❌ Affiliates\n"
        "❌ Revenue\n\n"
        "Leurs actions (broadcast, free access, ban) nécessiteront ton approbation."
    )
    
    keyboard = [[InlineKeyboardButton(text="❌ Annuler", callback_data="manage_admins")]]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(AdminStates.waiting_for_admin_id)


@router.message(AdminStates.waiting_for_admin_id)
async def handle_add_admin_input(message: types.Message, state: FSMContext):
    """Process admin ID input"""
    try:
        # Delete user's message
        await message.delete()
    except:
        pass
    
    user_input = message.text.strip()
    
    db = SessionLocal()
    try:
        # Try to find user by telegram_id or username
        target_user = None
        
        if user_input.startswith("@"):
            # Username
            username = user_input[1:]
            target_user = db.query(User).filter(User.username == username).first()
        elif user_input.isdigit():
            # Telegram ID
            tid = int(user_input)
            target_user = db.query(User).filter(User.telegram_id == tid).first()
        
        if not target_user:
            await message.answer(
                "❌ Utilisateur non trouvé. Réessaie avec un ID valide ou @username.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")]
                ])
            )
            return
        
        # Update role to admin
        db.execute(text("""
            UPDATE users 
            SET role = 'admin'
            WHERE telegram_id = :tid
        """), {'tid': target_user.telegram_id})
        db.commit()
        
        # Notify
        username_display = f"@{target_user.username}" if target_user.username else f"ID: {target_user.telegram_id}"
        
        await message.answer(
            f"✅ <b>ADMIN AJOUTÉ!</b>\n\n"
            f"👤 {username_display} est maintenant <b>admin</b>!\n\n"
            f"Il peut maintenant accéder au panel admin avec /admin",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Retour Admin Panel", callback_data="manage_admins")]
            ])
        )
        
        # Notify the new admin
        try:
            await message.bot.send_message(
                target_user.telegram_id,
                "🎉 <b>FÉLICITATIONS!</b>\n\n"
                "Tu as été promu <b>ADMIN</b>!\n\n"
                "Tu peux maintenant utiliser /admin pour accéder au panel d'administration.\n\n"
                "Tes actions (broadcast, free access, ban) nécessiteront l'approbation du super admin.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data == "remove_admin_prompt")
async def handle_remove_admin_prompt(callback: types.CallbackQuery):
    """Show list of admins to remove"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        # Get all regular admins (not super_admin)
        admins = db.execute(text("""
            SELECT telegram_id, username
            FROM users 
            WHERE role = 'admin'
            ORDER BY username
        """)).fetchall()
        
        if not admins:
            text = (
                "❌ <b>AUCUN ADMIN À RETIRER</b>\n\n"
                "Il n'y a pas d'admins réguliers actuellement."
            )
            keyboard = [[InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")]]
        else:
            text = (
                "➖ <b>RETIRER UN ADMIN</b>\n\n"
                "Sélectionne l'admin à rétrograder en utilisateur régulier:\n"
            )
            
            keyboard = []
            for tid, username in admins:
                display_name = f"@{username}" if username else f"ID: {tid}"
                keyboard.append([
                    InlineKeyboardButton(text=f"❌ {display_name}", callback_data=f"remove_admin_{tid}")
                ])
            
            keyboard.append([InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("remove_admin_"))
async def handle_remove_admin_confirm(callback: types.CallbackQuery):
    """Remove admin role from user"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    tid = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    try:
        # Get user info
        user = db.query(User).filter(User.telegram_id == tid).first()
        
        if not user:
            await callback.answer("❌ Utilisateur non trouvé", show_alert=True)
            return
        
        # Update role back to user
        db.execute(text("""
            UPDATE users 
            SET role = 'user'
            WHERE telegram_id = :tid
        """), {'tid': tid})
        db.commit()
        
        username_display = f"@{user.username}" if user.username else f"ID: {tid}"
        
        await callback.message.edit_text(
            f"✅ <b>ADMIN RETIRÉ!</b>\n\n"
            f"👤 {username_display} n'est plus admin.\n\n"
            f"Il n'a plus accès au panel d'administration.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Retour Admin Panel", callback_data="manage_admins")]
            ])
        )
        
        # Notify the ex-admin
        try:
            await callback.bot.send_message(
                tid,
                "ℹ️ <b>NOTIFICATION</b>\n\n"
                "Tu n'es plus admin.\n\n"
                "Tu n'as plus accès au panel d'administration.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
    finally:
        db.close()


@router.callback_query(F.data == "admin_actions_history")
async def handle_admin_actions_history(callback: types.CallbackQuery):
    """Show history of all admin actions"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        # Get last 20 actions (all statuses)
        actions = db.execute(text("""
            SELECT id, admin_id, action_type, target_user_id, status, created_at, reviewed_at
            FROM admin_actions 
            ORDER BY created_at DESC
            LIMIT 20
        """)).fetchall()
        
        if not actions:
            text = (
                "📊 <b>HISTORIQUE DES ACTIONS</b>\n\n"
                "Aucune action enregistrée."
            )
        else:
            text = "📊 <b>HISTORIQUE DES ACTIONS</b>\n\n"
            
            for action in actions:
                action_id, admin_id, action_type, target_user_id, status, created_at, reviewed_at = action
                
                # Get admin username
                admin = db.query(User).filter(User.telegram_id == admin_id).first()
                admin_name = f"@{admin.username}" if admin and admin.username else f"Admin {admin_id}"
                
                # Status emoji
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'rejected': '❌'
                }.get(status, '❓')
                
                text += f"{status_emoji} <b>#{action_id}</b> | {action_type}\n"
                text += f"   {admin_name} | {status}\n\n"
        
        keyboard = [[InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data == "admin_broadcast_request")
async def handle_broadcast_request_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Regular admin: Request broadcast approval - Step 1: Choose audience"""
    await callback.answer()
    
    if not is_any_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    
    if is_super_admin(callback.from_user.id):
        # Super admin doesn't need approval
        await callback.answer("Use direct 'Broadcast' button!", show_alert=True)
        return
    
    text = (
        "📢 <b>DEMANDER UN BROADCAST</b>\n\n"
        "Choisis l'audience pour ton broadcast:"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="🆓 BETA Users (FREE)", callback_data="broadcast_aud_beta")],
        [InlineKeyboardButton(text="💎 ALPHA Users (PREMIUM)", callback_data="broadcast_aud_alpha")],
        [InlineKeyboardButton(text="👥 TOUS les Users", callback_data="broadcast_aud_all")],
        [InlineKeyboardButton(text="❌ Annuler", callback_data="admin_refresh")]
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("broadcast_aud_"))
async def handle_broadcast_audience_choice(callback: types.CallbackQuery, state: FSMContext):
    """Step 2: Audience chosen, now ask for message"""
    await callback.answer()
    
    audience = callback.data.split("_")[-1]  # beta, alpha, or all
    
    # Store audience in state
    await state.update_data(audience=audience)
    
    audience_text = {
        'beta': '🆓 BETA Users (FREE)',
        'alpha': '💎 ALPHA Users (PREMIUM)',
        'all': '👥 TOUS les Users'
    }.get(audience, 'TOUS les Users')
    
    text = (
        f"📢 <b>BROADCAST - {audience_text}</b>\n\n"
        f"Envoie maintenant le message que tu veux broadcaster à {audience_text}.\n\n"
        f"⚠️ Le super admin devra approuver avant l'envoi."
    )
    
    keyboard = [[InlineKeyboardButton(text="❌ Annuler", callback_data="admin_refresh")]]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(AdminStates.waiting_for_broadcast_message)


@router.message(AdminStates.waiting_for_broadcast_message)
async def handle_broadcast_request_input(message: types.Message, state: FSMContext):
    """Process broadcast message and create approval request"""
    broadcast_message = message.text
    
    # Get audience from state
    data = await state.get_data()
    audience = data.get('audience', 'all')
    
    audience_text = {
        'beta': '🆓 BETA Users',
        'alpha': '💎 ALPHA Users',
        'all': '👥 TOUS les Users'
    }.get(audience, 'TOUS les Users')
    
    # Create approval request
    action_id = await request_action_approval(
        admin_id=message.from_user.id,
        action_type="broadcast",
        details={
            'message': broadcast_message,
            'audience': audience,
            'audience_text': audience_text
        },
        bot=message.bot
    )
    
    if action_id:
        await message.answer(
            "✅ <b>DEMANDE ENVOYÉE!</b>\n\n"
            "Ta demande de broadcast a été envoyée au super admin pour approbation.\n\n"
            "Tu seras notifié de la décision.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Retour Admin", callback_data="admin_refresh")]
            ])
        )
    else:
        await message.answer(
            "❌ Erreur lors de la création de la demande.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Retour Admin", callback_data="admin_refresh")]
            ])
        )
    
    await state.clear()
