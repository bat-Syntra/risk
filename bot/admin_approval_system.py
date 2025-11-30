"""
Admin Approval System - Multi-level admin permissions with approval workflow
Supports super_admin and regular admin roles
"""
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
from sqlalchemy import text
import json
import logging

from database import SessionLocal
from models.user import User, TierLevel
from models.admin_role import AdminAction

logger = logging.getLogger(__name__)
router = Router()

# Role hierarchy
SUPER_ADMIN_ID = 8004919557  # Your telegram_id
SUPER_ADMIN_IDS = [8004919557, 8213628656, 6029059837]  # All super admins


def get_user_role(telegram_id: int) -> str:
    """Get user's admin role (super_admin, admin, user)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return "user"
        return user.role or "user"
    finally:
        db.close()


def is_super_admin(telegram_id: int) -> bool:
    """Check if user is super admin"""
    if telegram_id in SUPER_ADMIN_IDS:
        return True
    return get_user_role(telegram_id) == "super_admin"


def is_any_admin(telegram_id: int) -> bool:
    """Check if user is any type of admin"""
    role = get_user_role(telegram_id)
    return role in ["super_admin", "admin"]


async def request_action_approval(
    admin_id: int,
    action_type: str,
    details: dict,
    target_user_id: int = None,
    bot = None
) -> int:
    """
    Create a pending action that requires super admin approval
    Returns action_id
    """
    db = SessionLocal()
    try:
        # Create pending action
        db.execute(text("""
            INSERT INTO admin_actions 
            (admin_id, action_type, target_user_id, details, status, created_at)
            VALUES (:admin_id, :action_type, :target_user_id, :details, 'pending', :created_at)
        """), {
            'admin_id': admin_id,
            'action_type': action_type,
            'target_user_id': target_user_id,
            'details': json.dumps(details),
            'created_at': datetime.now()
        })
        db.commit()
        
        # Get the action_id
        result = db.execute(text("""
            SELECT id FROM admin_actions 
            WHERE admin_id = :admin_id 
            ORDER BY created_at DESC 
            LIMIT 1
        """), {'admin_id': admin_id}).first()
        
        action_id = result[0] if result else None
        
        # Notify super admin
        if bot and action_id:
            admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
            admin_username = f"@{admin_user.username}" if admin_user and admin_user.username else f"Admin {admin_id}"
            
            # Format notification based on action type
            if action_type == "free_access":
                target_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                target_username = f"@{target_user.username}" if target_user and target_user.username else f"User {target_user_id}"
                days = details.get('days', 7)
                
                notification_text = (
                    f"🔔 <b>NOUVELLE DEMANDE D'ACTION ADMIN</b>\n\n"
                    f"👤 Admin: {admin_username}\n"
                    f"🎯 Action: <b>Free Access</b>\n"
                    f"👥 User cible: {target_username}\n"
                    f"⏰ Durée: {days} jours\n"
                    f"📝 Raison: {details.get('reason', 'N/A')}\n\n"
                    f"Utilise /admin puis 'Manage Admins' pour approuver/rejeter."
                )
            elif action_type == "broadcast":
                audience_text = details.get('audience_text', '👥 TOUS les Users')
                notification_text = (
                    f"🔔 <b>NOUVELLE DEMANDE D'ACTION ADMIN</b>\n\n"
                    f"👤 Admin: {admin_username}\n"
                    f"🎯 Action: <b>Broadcast</b>\n"
                    f"🎯 Audience: {audience_text}\n"
                    f"📝 Message:\n{details.get('message', 'N/A')}\n\n"
                    f"Utilise /admin puis 'Manage Admins' pour approuver/rejeter."
                )
            elif action_type == "ban":
                target_user = db.query(User).filter(User.telegram_id == target_user_id).first()
                target_username = f"@{target_user.username}" if target_user and target_user.username else f"User {target_user_id}"
                
                notification_text = (
                    f"🔔 <b>NOUVELLE DEMANDE D'ACTION ADMIN</b>\n\n"
                    f"👤 Admin: {admin_username}\n"
                    f"🎯 Action: <b>Ban User</b>\n"
                    f"👥 User cible: {target_username}\n"
                    f"📝 Raison: {details.get('reason', 'N/A')}\n\n"
                    f"Utilise /admin puis 'Manage Admins' pour approuver/rejeter."
                )
            else:
                notification_text = (
                    f"🔔 <b>NOUVELLE DEMANDE D'ACTION ADMIN</b>\n\n"
                    f"👤 Admin: {admin_username}\n"
                    f"🎯 Action: {action_type}\n\n"
                    f"Utilise /admin puis 'Manage Admins' pour approuver/rejeter."
                )
            
            try:
                await bot.send_message(SUPER_ADMIN_ID, notification_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error sending approval notification: {e}")
        
        return action_id
        
    except Exception as e:
        logger.error(f"Error requesting action approval: {e}")
        db.rollback()
        return None
    finally:
        db.close()


async def approve_action(action_id: int, super_admin_id: int, bot = None) -> bool:
    """Approve a pending admin action and execute it"""
    db = SessionLocal()
    try:
        # Get action details
        result = db.execute(text("""
            SELECT admin_id, action_type, target_user_id, details 
            FROM admin_actions 
            WHERE id = :action_id AND status = 'pending'
        """), {'action_id': action_id}).first()
        
        if not result:
            return False
        
        admin_id, action_type, target_user_id, details_json = result
        details = json.loads(details_json) if details_json else {}
        
        # Execute the action
        success = False
        error_msg = None
        
        if action_type == "free_access":
            # Grant free access
            days = details.get('days', 7)
            expiry = datetime.now() + timedelta(days=days)
            
            db.execute(text("""
                UPDATE users 
                SET tier = 'premium',
                    subscription_start = :now,
                    subscription_end = :expiry,
                    free_access = 1
                WHERE telegram_id = :tid
            """), {
                'tid': target_user_id,
                'now': datetime.now(),
                'expiry': expiry
            })
            success = True
            
        elif action_type == "broadcast":
            # Broadcast will be handled by super admin manually after approval
            success = True
            
        elif action_type == "ban":
            # Ban user
            db.execute(text("""
                UPDATE users 
                SET is_active = 0
                WHERE telegram_id = :tid
            """), {'tid': target_user_id})
            success = True
        
        elif action_type == "unban":
            # Unban user
            db.execute(text("""
                UPDATE users 
                SET is_active = 1
                WHERE telegram_id = :tid
            """), {'tid': target_user_id})
            success = True
        
        if success:
            # Mark as approved
            db.execute(text("""
                UPDATE admin_actions 
                SET status = 'approved',
                    reviewed_at = :now,
                    reviewed_by = :super_admin_id
                WHERE id = :action_id
            """), {
                'action_id': action_id,
                'now': datetime.now(),
                'super_admin_id': super_admin_id
            })
            db.commit()
            
            # Notify admin who requested
            if bot:
                admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
                notification_text = (
                    f"✅ <b>ACTION APPROUVÉE!</b>\n\n"
                    f"Ton action de type <b>{action_type}</b> a été approuvée par le super admin.\n\n"
                    f"L'action a été exécutée avec succès!"
                )
                try:
                    await bot.send_message(admin_id, notification_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Error sending approval notification to admin: {e}")
            
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Error approving action: {e}")
        db.rollback()
        return False
    finally:
        db.close()


async def reject_action(action_id: int, super_admin_id: int, reason: str = None, bot = None) -> bool:
    """Reject a pending admin action"""
    db = SessionLocal()
    try:
        # Get admin_id before updating
        result = db.execute(text("""
            SELECT admin_id FROM admin_actions 
            WHERE id = :action_id
        """), {'action_id': action_id}).first()
        
        if not result:
            return False
        
        admin_id = result[0]
        
        # Mark as rejected
        db.execute(text("""
            UPDATE admin_actions 
            SET status = 'rejected',
                reviewed_at = :now,
                reviewed_by = :super_admin_id,
                notes = :reason
            WHERE id = :action_id
        """), {
            'action_id': action_id,
            'now': datetime.now(),
            'super_admin_id': super_admin_id,
            'reason': reason or "Rejeté par super admin"
        })
        db.commit()
        
        # Notify admin who requested
        if bot:
            notification_text = (
                f"❌ <b>ACTION REJETÉE</b>\n\n"
                f"Ton action a été rejetée par le super admin.\n\n"
                f"📝 Raison: {reason or 'Non spécifiée'}"
            )
            try:
                await bot.send_message(admin_id, notification_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error sending rejection notification to admin: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error rejecting action: {e}")
        db.rollback()
        return False
    finally:
        db.close()


@router.callback_query(F.data == "manage_admins")
async def handle_manage_admins(callback: types.CallbackQuery):
    """Super admin only: Manage admins and pending actions"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        # Count pending actions
        pending_count = db.execute(text("""
            SELECT COUNT(*) FROM admin_actions WHERE status = 'pending'
        """)).scalar()
        
        # Get all admins
        admins = db.execute(text("""
            SELECT telegram_id, username, role 
            FROM users 
            WHERE role IN ('admin', 'super_admin')
            ORDER BY role DESC, username
        """)).fetchall()
        
        text_msg = (
            f"👑 <b>GESTION DES ADMINS</b>\n\n"
            f"🔔 Actions en attente: <b>{pending_count}</b>\n\n"
            f"👥 <b>Liste des admins:</b>\n"
        )
        
        for admin in admins:
            tid, username, role = admin
            role_emoji = "👑" if role == "super_admin" else "🛠️"
            username_display = f"@{username}" if username else f"ID: {tid}"
            text_msg += f"{role_emoji} {username_display} ({role})\n"
        
        keyboard = [
            [InlineKeyboardButton(text=f"📋 Voir Actions en Attente ({pending_count})", callback_data="view_pending_actions")],
            [InlineKeyboardButton(text="➕ Ajouter Admin", callback_data="add_admin_prompt")],
            [InlineKeyboardButton(text="➖ Retirer Admin", callback_data="remove_admin_prompt")],
            [InlineKeyboardButton(text="📊 Historique Actions", callback_data="admin_actions_history")],
            [InlineKeyboardButton(text="◀️ Retour Admin", callback_data="admin_refresh")]
        ]
        
        await callback.message.edit_text(
            text_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data == "view_pending_actions")
async def handle_view_pending_actions(callback: types.CallbackQuery):
    """View all pending admin actions"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        # Get pending actions
        actions = db.execute(text("""
            SELECT id, admin_id, action_type, target_user_id, details, created_at
            FROM admin_actions 
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 10
        """)).fetchall()
        
        if not actions:
            text_msg = (
                "✅ <b>AUCUNE ACTION EN ATTENTE</b>\n\n"
                "Toutes les demandes ont été traitées!"
            )
            keyboard = [[InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")]]
        else:
            text_msg = f"📋 <b>ACTIONS EN ATTENTE</b>\n\n"
            
            keyboard = []
            for action in actions:
                action_id, admin_id, action_type, target_user_id, details_json, created_at = action
                details = json.loads(details_json) if details_json else {}
                
                # Get admin username
                admin = db.query(User).filter(User.telegram_id == admin_id).first()
                admin_username = f"@{admin.username}" if admin and admin.username else f"Admin {admin_id}"
                
                # Format action summary
                if action_type == "free_access":
                    target = db.query(User).filter(User.telegram_id == target_user_id).first()
                    target_username = f"@{target.username}" if target and target.username else f"User {target_user_id}"
                    days = details.get('days', 7)
                    summary = f"Free access {days}j pour {target_username}"
                elif action_type == "broadcast":
                    msg_preview = details.get('message', '')[:30]
                    summary = f"Broadcast: {msg_preview}..."
                elif action_type == "ban":
                    target = db.query(User).filter(User.telegram_id == target_user_id).first()
                    target_username = f"@{target.username}" if target and target.username else f"User {target_user_id}"
                    summary = f"Ban {target_username}"
                else:
                    summary = action_type
                
                text_msg += f"🔸 <b>#{action_id}</b> | {admin_username}\n   {summary}\n\n"
                
                # Add approve/reject buttons
                keyboard.append([
                    InlineKeyboardButton(text=f"✅ Approuver #{action_id}", callback_data=f"approve_action_{action_id}"),
                    InlineKeyboardButton(text=f"❌ Rejeter #{action_id}", callback_data=f"reject_action_{action_id}")
                ])
            
            keyboard.append([InlineKeyboardButton(text="◀️ Retour", callback_data="manage_admins")])
        
        await callback.message.edit_text(
            text_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    finally:
        db.close()


@router.callback_query(F.data.startswith("approve_action_"))
async def handle_approve_action(callback: types.CallbackQuery):
    """Approve a pending action"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    action_id = int(callback.data.split("_")[2])
    
    success = await approve_action(action_id, callback.from_user.id, callback.bot)
    
    if success:
        await callback.answer("✅ Action approuvée et exécutée!", show_alert=True)
    else:
        await callback.answer("❌ Erreur lors de l'approbation", show_alert=True)
    
    # Refresh the list
    await handle_view_pending_actions(callback)


@router.callback_query(F.data.startswith("reject_action_"))
async def handle_reject_action(callback: types.CallbackQuery):
    """Reject a pending action"""
    await callback.answer()
    
    if not is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Réservé au super admin!", show_alert=True)
        return
    
    action_id = int(callback.data.split("_")[2])
    
    success = await reject_action(action_id, callback.from_user.id, "Rejeté par super admin", callback.bot)
    
    if success:
        await callback.answer("❌ Action rejetée", show_alert=True)
    else:
        await callback.answer("❌ Erreur lors du rejet", show_alert=True)
    
    # Refresh the list
    await handle_view_pending_actions(callback)
