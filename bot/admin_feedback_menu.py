"""
Admin menu for viewing feedbacks and vouches
"""
import logging
from datetime import datetime, date
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from database import SessionLocal
from models.user import User
from models.feedback import UserFeedback, UserVouch
from sqlalchemy import desc, func
import os
from config import ADMIN_CHAT_ID

router = Router()
logger = logging.getLogger(__name__)

# Admin IDs from environment (same logic as admin_handlers.py)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DEFAULT_OWNER_ID = 8213628656
if DEFAULT_OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(DEFAULT_OWNER_ID)
if ADMIN_CHAT_ID and int(ADMIN_CHAT_ID) not in ADMIN_IDS:
    try:
        if int(ADMIN_CHAT_ID) != 0:
            ADMIN_IDS.append(int(ADMIN_CHAT_ID))
    except Exception:
        pass


def is_admin(user_id: int) -> bool:
    """Check if user is admin via env list, ADMIN_CHAT_ID, DB flag, or role."""
    if user_id in ADMIN_IDS:
        return True
    try:
        if int(ADMIN_CHAT_ID) and user_id == int(ADMIN_CHAT_ID):
            return True
    except Exception:
        pass
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if u and u.is_admin:
            return True
        # Check role (admin or super_admin)
        if u and hasattr(u, 'role') and u.role in ['admin', 'super_admin']:
            return True
    except Exception:
        pass
    finally:
        db.close()
    return False


@router.message(Command("feedbacks"))
async def cmd_feedbacks(message: types.Message):
    """Show feedbacks and vouches menu (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin only")
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Nouveaux Feedbacks", callback_data="admin_feedbacks_new")],
        [types.InlineKeyboardButton(text="📜 Tous les Feedbacks", callback_data="admin_feedbacks_all")],
        [types.InlineKeyboardButton(text="🎉 Nouveaux Vouches", callback_data="admin_vouches_new")],
        [types.InlineKeyboardButton(text="📜 Tous les Vouches", callback_data="admin_vouches_all")],
        [types.InlineKeyboardButton(text="📊 Statistiques", callback_data="admin_fb_stats")],
        [types.InlineKeyboardButton(text="◀️ Retour Menu Admin", callback_data="open_admin")]
    ])
    
    await message.answer(
        "🔧 <b>MENU ADMIN - FEEDBACKS & VOUCHES</b>\n\n"
        "Choisis une option:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin_feedbacks_new")
async def show_new_feedbacks(callback: types.CallbackQuery):
    """Show unseen feedbacks"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    db = SessionLocal()
    try:
        feedbacks = db.query(UserFeedback).filter(
            UserFeedback.seen_by_admin == False
        ).order_by(desc(UserFeedback.created_at)).limit(20).all()
        
        if not feedbacks:
            await callback.message.edit_text(
                "✅ <b>Aucun nouveau feedback</b>\n\n"
                "Tous les feedbacks ont été vus!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            return
        
        text = f"📝 <b>NOUVEAUX FEEDBACKS ({len(feedbacks)})</b>\n\n"
        
        for fb in feedbacks:
            # Get username
            user = db.query(User).filter(User.telegram_id == fb.user_id).first()
            username = user.username if user and user.username else f"User {fb.user_id}"
            
            emoji = "✅" if fb.feedback_type == 'good' else "⚠️"
            text += (
                f"{emoji} <b>@{username}</b> ({fb.feedback_type.upper()})\n"
                f"📊 {fb.bet_type or 'N/A'} | ${fb.bet_amount or 0:.0f} → ${fb.profit or 0:+.0f}\n"
                f"⚽ {fb.match_info or 'N/A'}\n"
            )
            if fb.message:
                text += f"💬 <i>\"{fb.message}\"</i>\n"
            text += f"📅 {fb.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # Mark as seen
        for fb in feedbacks:
            fb.seen_by_admin = True
        db.commit()
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Error showing feedbacks: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "admin_feedbacks_all")
async def show_all_feedbacks(callback: types.CallbackQuery):
    """Show all feedbacks (last 30 days)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    db = SessionLocal()
    try:
        # Group by date
        feedbacks = db.query(UserFeedback).order_by(desc(UserFeedback.created_at)).limit(50).all()
        
        if not feedbacks:
            await callback.message.edit_text(
                "📝 <b>Aucun feedback</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            return
        
        # Group by date
        by_date = {}
        for fb in feedbacks:
            date_key = fb.created_at.strftime('%Y-%m-%d')
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(fb)
        
        text = "📝 <b>TOUS LES FEEDBACKS</b>\n\n"
        
        for date_key in sorted(by_date.keys(), reverse=True):
            text += f"📅 <b>{date_key}</b>\n"
            for fb in by_date[date_key]:
                user = db.query(User).filter(User.telegram_id == fb.user_id).first()
                username = user.username if user and user.username else f"User {fb.user_id}"
                emoji = "✅" if fb.feedback_type == 'good' else "⚠️"
                text += f"{emoji} @{username} | {fb.bet_type or 'N/A'} | ${fb.profit or 0:+.0f}\n"
                # Show the feedback message if exists
                if fb.message:
                    text += f"💬 <i>\"{fb.message}\"</i>\n"
            text += "\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Error showing all feedbacks: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "admin_vouches_new")
async def show_new_vouches(callback: types.CallbackQuery):
    """Show unseen vouches"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    db = SessionLocal()
    try:
        vouches = db.query(UserVouch).filter(
            UserVouch.seen_by_admin == False
        ).order_by(desc(UserVouch.created_at)).limit(20).all()
        
        if not vouches:
            await callback.message.edit_text(
                "✅ <b>Aucun nouveau vouch</b>\n\n"
                "Tous les vouches ont été vus!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            return
        
        text = f"🎉 <b>NOUVEAUX VOUCHES ({len(vouches)})</b>\n\n"
        
        for v in vouches:
            # Get username
            user = db.query(User).filter(User.telegram_id == v.user_id).first()
            username = user.username if user and user.username else f"User {v.user_id}"
            
            # Emoji based on profit
            if v.profit >= 500:
                emoji = "🚀🔥💎"
            elif v.profit >= 200:
                emoji = "🔥💰"
            elif v.profit >= 100:
                emoji = "✨💰"
            else:
                emoji = "✅💚"
            
            text += (
                f"{emoji} <b>@{username}</b>\n"
                f"💰 <b>${v.profit:+.2f}</b> (mise ${v.bet_amount:.2f})\n"
                f"📈 ROI: {(v.profit/v.bet_amount*100):.1f}%\n"
                f"🎯 {v.bet_type.upper()}\n"
                f"⚽ {v.match_info}\n"
                f"🏆 {v.sport or 'N/A'}\n"
                f"📅 {v.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        # Mark as seen
        for v in vouches:
            v.seen_by_admin = True
        db.commit()
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Error showing vouches: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "admin_vouches_all")
async def show_all_vouches(callback: types.CallbackQuery):
    """Show all vouches grouped by date"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    db = SessionLocal()
    try:
        vouches = db.query(UserVouch).order_by(desc(UserVouch.created_at)).limit(50).all()
        
        if not vouches:
            await callback.message.edit_text(
                "🎉 <b>Aucun vouch</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            return
        
        # Group by date
        by_date = {}
        for v in vouches:
            date_key = v.created_at.strftime('%Y-%m-%d')
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(v)
        
        text = "🎉 <b>TOUS LES VOUCHES</b>\n\n"
        
        for date_key in sorted(by_date.keys(), reverse=True):
            total_profit = sum(v.profit for v in by_date[date_key])
            text += f"📅 <b>{date_key}</b> (Total: ${total_profit:+.2f})\n"
            for v in by_date[date_key]:
                user = db.query(User).filter(User.telegram_id == v.user_id).first()
                username = user.username if user and user.username else f"User {v.user_id}"
                emoji = "🔥" if v.profit >= 200 else "💰" if v.profit >= 100 else "✅"
                text += f"{emoji} @{username} | ${v.profit:+.2f} | {v.bet_type}\n"
            text += "\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Error showing all vouches: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "admin_fb_stats")
async def show_stats(callback: types.CallbackQuery):
    """Show feedback and vouch statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    db = SessionLocal()
    try:
        # Feedback stats
        total_feedbacks = db.query(UserFeedback).count()
        good_feedbacks = db.query(UserFeedback).filter(UserFeedback.feedback_type == 'good').count()
        bad_feedbacks = db.query(UserFeedback).filter(UserFeedback.feedback_type == 'bad').count()
        unseen_feedbacks = db.query(UserFeedback).filter(UserFeedback.seen_by_admin == False).count()
        
        # Vouch stats
        total_vouches = db.query(UserVouch).count()
        unseen_vouches = db.query(UserVouch).filter(UserVouch.seen_by_admin == False).count()
        total_vouch_profit = db.query(func.sum(UserVouch.profit)).scalar() or 0
        avg_vouch_profit = db.query(func.avg(UserVouch.profit)).scalar() or 0
        max_vouch = db.query(UserVouch).order_by(desc(UserVouch.profit)).first()
        
        # Vouch by bet type
        middle_vouches = db.query(UserVouch).filter(UserVouch.bet_type == 'middle').count()
        arb_vouches = db.query(UserVouch).filter(UserVouch.bet_type == 'arbitrage').count()
        ev_vouches = db.query(UserVouch).filter(UserVouch.bet_type == 'good_ev').count()
        
        text = (
            "📊 <b>STATISTIQUES</b>\n\n"
            "📝 <b>FEEDBACKS</b>\n"
            f"• Total: {total_feedbacks}\n"
            f"• Positifs: {good_feedbacks} (✅ {good_feedbacks/total_feedbacks*100:.0f}%)\n" if total_feedbacks > 0 else ""
            f"• Négatifs: {bad_feedbacks} (⚠️ {bad_feedbacks/total_feedbacks*100:.0f}%)\n" if total_feedbacks > 0 else ""
            f"• Non vus: {unseen_feedbacks}\n\n"
            "🎉 <b>VOUCHES</b>\n"
            f"• Total: {total_vouches}\n"
            f"• Non vus: {unseen_vouches}\n"
            f"• Profit total: ${total_vouch_profit:,.2f}\n"
            f"• Profit moyen: ${avg_vouch_profit:.2f}\n"
        )
        
        if max_vouch:
            max_user = db.query(User).filter(User.telegram_id == max_vouch.user_id).first()
            max_username = max_user.username if max_user and max_user.username else f"User {max_vouch.user_id}"
            text += f"• Plus gros: ${max_vouch.profit:.2f} (@{max_username})\n"
        
        text += (
            f"\n<b>Par type:</b>\n"
            f"• Middle: {middle_vouches}\n"
            f"• Arbitrage: {arb_vouches}\n"
            f"• Good EV: {ev_vouches}\n"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await callback.answer("❌ Erreur", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "admin_fb_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Return to main feedback menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    await callback.answer()
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Nouveaux Feedbacks", callback_data="admin_feedbacks_new")],
        [types.InlineKeyboardButton(text="📜 Tous les Feedbacks", callback_data="admin_feedbacks_all")],
        [types.InlineKeyboardButton(text="🎉 Nouveaux Vouches", callback_data="admin_vouches_new")],
        [types.InlineKeyboardButton(text="📜 Tous les Vouches", callback_data="admin_vouches_all")],
        [types.InlineKeyboardButton(text="📊 Statistiques", callback_data="admin_fb_stats")],
        [types.InlineKeyboardButton(text="◀️ Retour Menu Admin", callback_data="open_admin")]
    ])
    
    await callback.message.edit_text(
        "🔧 <b>MENU ADMIN - FEEDBACKS & VOUCHES</b>\n\n"
        "Choisis une option:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


def get_back_keyboard():
    """Get back button keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="◀️ Retour", callback_data="admin_fb_menu")]
    ])
