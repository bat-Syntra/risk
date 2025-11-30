"""Debug command to check user's alert settings"""
from aiogram import Router, types, F
from aiogram.filters import Command
from database import SessionLocal
from models.user import User
import os

router = Router()

# Admin IDs from environment
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DEFAULT_OWNER_ID = 8213628656
if DEFAULT_OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(DEFAULT_OWNER_ID)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("debug_me"))
async def cmd_debug_me(message: types.Message):
    """Show user's current alert settings and why they might not receive alerts"""
    user_id = message.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            await message.answer("❌ User not found in database. Use /start first.")
            return
        
        # Check all relevant flags
        text = (
            f"🔍 <b>DEBUG INFO FOR USER {user_id}</b>\n\n"
            f"<b>Tier & Subscription:</b>\n"
            f"• Tier: {user.tier.name}\n"
            f"• Subscription End: {user.subscription_end or 'LIFETIME'}\n"
            f"• Subscription Active: {user.subscription_active}\n\n"
            f"<b>Account Status:</b>\n"
            f"• is_active: {user.is_active}\n"
            f"• is_banned: {user.is_banned}\n"
            f"• notifications_enabled: {user.notifications_enabled}\n\n"
            f"<b>Alert Types Enabled:</b>\n"
            f"• enable_good_odds (Good EV): {user.enable_good_odds}\n"
            f"• enable_middle (Middle): {user.enable_middle}\n\n"
            f"<b>Filters:</b>\n"
            f"• min_arb_percent: {user.min_arb_percent or 'default'}\n"
            f"• max_arb_percent: {user.max_arb_percent or 'default'}\n"
            f"• min_good_ev_percent: {user.min_good_ev_percent or 'default'}\n"
            f"• max_good_ev_percent: {user.max_good_ev_percent or 'default'}\n"
            f"• min_middle_percent: {user.min_middle_percent or 'default'}\n"
            f"• max_middle_percent: {user.max_middle_percent or 'default'}\n\n"
            f"<b>Today's Stats:</b>\n"
            f"• Alerts received today: {user.alerts_today}\n"
            f"• Last alert: {user.last_alert_at or 'Never'}\n\n"
        )
        
        # Add warnings
        warnings = []
        if not user.is_active:
            warnings.append("⚠️ is_active=False → You won't receive ANY alerts!")
        if user.is_banned:
            warnings.append("⚠️ is_banned=True → You won't receive ANY alerts!")
        if user.notifications_enabled is False:
            warnings.append("⚠️ notifications_enabled=False → You won't receive ANY alerts!")
        if not user.enable_good_odds:
            warnings.append("⚠️ enable_good_odds=False → No Good EV alerts")
        if not user.enable_middle:
            warnings.append("⚠️ enable_middle=False → No Middle alerts")
        if not user.subscription_active and user.tier.name == 'premium':
            warnings.append("⚠️ Subscription expired → Downgraded to FREE tier")
        
        if warnings:
            text += "<b>⚠️ WARNINGS:</b>\n" + "\n".join(warnings) + "\n\n"
        else:
            text += "✅ <b>All settings look good!</b>\n\n"
        
        text += "To fix issues, use /settings or contact admin."
        
        await message.answer(text, parse_mode="HTML")
        
    finally:
        db.close()


@router.message(Command("fix_alerts"))
async def cmd_fix_alerts(message: types.Message):
    """Admin command to enable all alert flags for a user"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ Admin only")
        return
    
    # Parse target user ID from command
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "🔧 <b>Usage:</b> /fix_alerts [user_id]\n\n"
            "Example: <code>/fix_alerts 8213628656</code>\n\n"
            "This will enable all alert flags for the specified user.",
            parse_mode="HTML"
        )
        return
    
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == target_user_id).first()
        
        if not user:
            await message.answer(f"❌ User {target_user_id} not found in database")
            return
        
        # Enable all alert flags
        user.enable_good_odds = True
        user.enable_middle = True
        user.is_active = True
        user.is_banned = False
        if user.notifications_enabled is None or user.notifications_enabled is False:
            user.notifications_enabled = True
        
        db.commit()
        
        await message.answer(
            f"✅ <b>Fixed alert settings for user {target_user_id}</b>\n\n"
            f"✅ enable_good_odds = True\n"
            f"✅ enable_middle = True\n"
            f"✅ is_active = True\n"
            f"✅ is_banned = False\n"
            f"✅ notifications_enabled = True\n\n"
            f"User should now receive all alert types!",
            parse_mode="HTML"
        )
        
    finally:
        db.close()
