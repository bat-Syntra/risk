"""
Request handlers for regular admins - Free Access and Ban/Unban with approval
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User
from bot.admin_approval_system import (
    is_any_admin, is_super_admin, request_action_approval
)

router = Router()


class FreeAccessStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_reason = State()


@router.callback_query(F.data.startswith("admin_request_free_"))
async def handle_request_free_access(callback: types.CallbackQuery, state: FSMContext):
    """Regular admin: Request free access approval (max 7 days)"""
    await callback.answer()
    
    if not is_any_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    
    if is_super_admin(callback.from_user.id):
        # Super admin doesn't need approval - redirect to normal free access
        target_user_id = int(callback.data.split("_")[-1])
        await callback.answer("Use direct 'Free Access' button!", show_alert=True)
        return
    
    target_user_id = int(callback.data.split("_")[-1])
    
    # Store user ID in state
    await state.update_data(target_user_id=target_user_id)
    
    text = (
        "🎁 <b>DEMANDER FREE ACCESS</b>\n\n"
        "Combien de jours de Free Access? (Max: 7 jours)\n\n"
        "Envoie un nombre entre 1 et 7:"
    )
    
    keyboard = [[InlineKeyboardButton(text="❌ Annuler", callback_data=f"admin_user_{target_user_id}")]]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(FreeAccessStates.waiting_for_days)


@router.message(FreeAccessStates.waiting_for_days)
async def handle_free_access_days_input(message: types.Message, state: FSMContext):
    """Process days input for free access request"""
    try:
        await message.delete()
    except:
        pass
    
    try:
        days = int(message.text.strip())
        if days < 1 or days > 7:
            raise ValueError()
    except:
        await message.answer(
            "❌ Nombre invalide. Envoie un nombre entre 1 et 7:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Annuler", callback_data="admin_refresh")]
            ])
        )
        return
    
    # Store days
    await state.update_data(days=days)
    
    await message.answer(
        f"🎁 <b>FREE ACCESS - {days} JOURS</b>\n\n"
        f"Maintenant, envoie la raison de cette demande:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Annuler", callback_data="admin_refresh")]
        ])
    )
    
    await state.set_state(FreeAccessStates.waiting_for_reason)


@router.message(FreeAccessStates.waiting_for_reason)
async def handle_free_access_reason_input(message: types.Message, state: FSMContext):
    """Process reason and create approval request"""
    reason = message.text.strip()
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    days = data.get('days')
    
    # Create approval request
    action_id = await request_action_approval(
        admin_id=message.from_user.id,
        action_type="free_access",
        details={
            'days': days,
            'reason': reason
        },
        target_user_id=target_user_id,
        bot=message.bot
    )
    
    if action_id:
        await message.answer(
            "✅ <b>DEMANDE ENVOYÉE!</b>\n\n"
            f"Ta demande de {days} jours de Free Access a été envoyée au super admin.\n\n"
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


@router.callback_query(F.data.startswith("admin_request_ban_"))
async def handle_request_ban(callback: types.CallbackQuery, state: FSMContext):
    """Regular admin: Request ban/unban approval"""
    await callback.answer()
    
    if not is_any_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    
    if is_super_admin(callback.from_user.id):
        # Super admin doesn't need approval - redirect to normal ban
        await callback.answer("Use direct 'Ban' button!", show_alert=True)
        return
    
    target_user_id = int(callback.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == target_user_id).first()
        if not user:
            await callback.answer("❌ User non trouvé", show_alert=True)
            return
        
        action_type = "unban" if user.is_banned else "ban"
        action_text = "Unban" if user.is_banned else "Ban"
        
        # Store in state
        await state.update_data(target_user_id=target_user_id, action_type=action_type)
        
        text = (
            f"🚫 <b>DEMANDER {action_text.upper()}</b>\n\n"
            f"User: @{user.username or 'N/A'}\n"
            f"ID: {target_user_id}\n\n"
            f"Envoie la raison pour {action_text}:"
        )
        
        keyboard = [[InlineKeyboardButton(text="❌ Annuler", callback_data=f"admin_user_{target_user_id}")]]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        await state.set_state(AdminStates.waiting_for_ban_reason)
        
    finally:
        db.close()


class AdminStates(StatesGroup):
    waiting_for_ban_reason = State()


@router.message(AdminStates.waiting_for_ban_reason)
async def handle_ban_reason_input(message: types.Message, state: FSMContext):
    """Process ban reason and create approval request"""
    reason = message.text.strip()
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    action_type = data.get('action_type')
    
    # Create approval request
    action_id = await request_action_approval(
        admin_id=message.from_user.id,
        action_type=action_type,
        details={'reason': reason},
        target_user_id=target_user_id,
        bot=message.bot
    )
    
    if action_id:
        await message.answer(
            "✅ <b>DEMANDE ENVOYÉE!</b>\n\n"
            f"Ta demande de {action_type} a été envoyée au super admin.\n\n"
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
