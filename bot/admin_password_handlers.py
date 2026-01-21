"""
Admin password management handlers for Telegram bot
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import SessionLocal
from models.user import User
from bot.admin_handlers import is_admin
from bot.admin_approval_system import is_super_admin
import bcrypt

router = Router()

class ChangePasswordState(StatesGroup):
    waiting_for_new_password = State()

@router.callback_query(F.data.startswith("admin_seepass_"))
async def callback_admin_see_password(callback: types.CallbackQuery):
    """Show user's password (super admin only)"""
    if not is_super_admin(callback.from_user.id):
        await callback.answer("❌ Super admin access required", show_alert=True)
        return
    
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        # Get password from website users table
        try:
            from models import WebsiteUser
            website_user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == user_id).first()
            
            if website_user and website_user.password_hash:
                # Show password info (we can't decrypt bcrypt, but show that it exists)
                text = (
                    f"🔐 <b>PASSWORD INFO</b>\n\n"
                    f"👤 User ID: <code>{user_id}</code>\n"
                    f"📧 Email: <code>{website_user.email}</code>\n"
                    f"🔑 Password Hash: <code>{website_user.password_hash[:50]}...</code>\n\n"
                    f"⚠️ <b>Note:</b> Passwords are hashed with bcrypt and cannot be decrypted.\n"
                    f"Use 'Change Pass' to set a new password."
                )
            else:
                text = (
                    f"❌ <b>NO PASSWORD FOUND</b>\n\n"
                    f"👤 User ID: <code>{user_id}</code>\n"
                    f"This user doesn't have a website account or password."
                )
        except Exception as e:
            text = f"❌ Error accessing password data: {str(e)}"
        
        kb = [[InlineKeyboardButton(text="◀️ Back to User", callback_data=f"admin_user_{user_id}")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        
    finally:
        db.close()

@router.callback_query(F.data.startswith("admin_changepass_"))
async def callback_admin_change_password(callback: types.CallbackQuery, state: FSMContext):
    """Start password change process (super admin only)"""
    if not is_super_admin(callback.from_user.id):
        await callback.answer("❌ Super admin access required", show_alert=True)
        return
    
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    
    # Store user_id in state
    await state.update_data(target_user_id=user_id)
    await state.set_state(ChangePasswordState.waiting_for_new_password)
    
    kb = [[InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_user_{user_id}")]]
    await callback.message.edit_text(
        f"🔑 <b>CHANGE PASSWORD</b>\n\n"
        f"👤 User ID: <code>{user_id}</code>\n\n"
        f"Please send the new password for this user:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

@router.message(ChangePasswordState.waiting_for_new_password)
async def process_new_password(message: types.Message, state: FSMContext):
    """Process the new password input"""
    if not is_super_admin(message.from_user.id):
        await message.answer("❌ Super admin access required")
        return
    
    data = await state.get_data()
    user_id = data.get('target_user_id')
    new_password = message.text.strip()
    
    if len(new_password) < 6:
        await message.answer("❌ Password must be at least 6 characters long. Try again:")
        return
    
    db = SessionLocal()
    try:
        # Update password in website users table
        try:
            from models import WebsiteUser
            website_user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == user_id).first()
            
            if website_user:
                # Hash the new password
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                website_user.password_hash = password_hash
                db.commit()
                
                text = (
                    f"✅ <b>PASSWORD CHANGED</b>\n\n"
                    f"👤 User ID: <code>{user_id}</code>\n"
                    f"📧 Email: <code>{website_user.email}</code>\n"
                    f"🔑 New password set successfully!\n\n"
                    f"The user can now login with the new password."
                )
            else:
                text = (
                    f"❌ <b>NO WEBSITE ACCOUNT</b>\n\n"
                    f"👤 User ID: <code>{user_id}</code>\n"
                    f"This user doesn't have a website account to update."
                )
        except Exception as e:
            text = f"❌ Error updating password: {str(e)}"
        
        kb = [[InlineKeyboardButton(text="◀️ Back to User", callback_data=f"admin_user_{user_id}")]]
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        
    finally:
        db.close()
        await state.clear()

@router.callback_query(F.data.startswith("admin_deleteacc_"))
async def callback_admin_delete_account(callback: types.CallbackQuery):
    """Show delete account confirmation (super admin only)"""
    if not is_super_admin(callback.from_user.id):
        await callback.answer("❌ Super admin access required", show_alert=True)
        return
    
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.message.edit_text("❌ User not found")
            return
        
        # Get email info
        email_info = "N/A"
        try:
            from models import WebsiteUser
            website_user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == user_id).first()
            if website_user and website_user.email:
                email_info = website_user.email
        except Exception:
            pass
        
        text = (
            f"⚠️ <b>DELETE ACCOUNT CONFIRMATION</b>\n\n"
            f"👤 User: @{u.username or 'N/A'}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📧 Email: <code>{email_info}</code>\n"
            f"🎖️ Tier: <b>{u.tier.value.upper()}</b>\n\n"
            f"❗️ <b>This will permanently delete:</b>\n"
            f"• Telegram bot account\n"
            f"• Website account (if exists)\n"
            f"• All user data and history\n"
            f"• Referral relationships\n\n"
            f"<b>Are you sure?</b>"
        )
        
        kb = [
            [InlineKeyboardButton(text="🗑️ YES, DELETE", callback_data=f"admin_deleteacc_confirm_{user_id}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_user_{user_id}")]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        
    finally:
        db.close()

@router.callback_query(F.data.startswith("admin_deleteacc_confirm_"))
async def callback_admin_delete_account_confirm(callback: types.CallbackQuery):
    """Actually delete the account (super admin only)"""
    if not is_super_admin(callback.from_user.id):
        await callback.answer("❌ Super admin access required", show_alert=True)
        return
    
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        # Get user info before deletion
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.message.edit_text("❌ User not found")
            return
        
        username = u.username or "N/A"
        
        # Delete from website users table
        try:
            from models import WebsiteUser
            website_user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == user_id).first()
            if website_user:
                db.delete(website_user)
        except Exception:
            pass
        
        # Delete referral relationships
        try:
            from models.referral import Referral, ReferralTier2
            # Delete as referee
            db.query(Referral).filter(Referral.referee_id == user_id).delete()
            db.query(ReferralTier2).filter(ReferralTier2.referee_id == user_id).delete()
            # Delete as referrer
            db.query(Referral).filter(Referral.referrer_id == user_id).delete()
            db.query(ReferralTier2).filter(ReferralTier2.original_referrer_id == user_id).delete()
        except Exception:
            pass
        
        # Delete bet history
        try:
            from models.bet import Bet
            db.query(Bet).filter(Bet.user_id == user_id).delete()
        except Exception:
            pass
        
        # Delete main user record
        db.delete(u)
        db.commit()
        
        text = (
            f"✅ <b>ACCOUNT DELETED</b>\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            f"All data has been permanently removed:\n"
            f"• Telegram bot account ✅\n"
            f"• Website account ✅\n"
            f"• Referral relationships ✅\n"
            f"• Bet history ✅\n\n"
            f"The user will need to /start again to create a new account."
        )
        
        kb = [[InlineKeyboardButton(text="◀️ Back to Users", callback_data="admin_users_1")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Error deleting account: {str(e)}")
    finally:
        db.close()
