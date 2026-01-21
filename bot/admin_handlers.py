"""
Admin handlers for Telegram bot
100% Telegram-based admin panel
"""
from aiogram import Bot, F, types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from datetime import datetime, timedelta, date
from sqlalchemy import func, text
import logging

from database import SessionLocal
from models.user import User, TierLevel
from models.bet import DailyStats, UserBet
from models.referral import Referral, ReferralTier2, ReferralSettings
from core.tiers import TIER_PRICING, TierManager, TierLevel as CoreTierLevel
from config import ADMIN_CHAT_ID
from utils.oddsjam_parser import parse_positive_ev_notification, parse_middle_notification, calculate_middle_stakes
from utils.oddsjam_formatters import format_good_odds_message, format_middle_message
from utils.odds_api_links import get_fallback_url
from core.casinos import get_casino_logo

logger = logging.getLogger(__name__)
router = Router()

# Admin IDs from environment (set in config.py)
import os
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
# Hardcoded owner fallback
DEFAULT_OWNER_ID = 8213628656
DEFAULT_OWNER_USERNAME = "ZEROR1SK"
if DEFAULT_OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(DEFAULT_OWNER_ID)
if ADMIN_CHAT_ID and int(ADMIN_CHAT_ID) not in ADMIN_IDS:
    try:
        if int(ADMIN_CHAT_ID) != 0:
            ADMIN_IDS.append(int(ADMIN_CHAT_ID))
    except Exception:
        pass


# FSM States for admin
class AdminStates(StatesGroup):
    awaiting_broadcast = State()
    awaiting_search = State()
    awaiting_aff_rate = State()


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
        # Allow by username if configured
        try:
            # We cannot access username here directly, so rely on DB entry
            uname = (u.username or "")
            if u and ADMIN_USERNAME and uname.lower() == ADMIN_USERNAME.lower():
                return True
            if u and uname.lower() == DEFAULT_OWNER_USERNAME.lower():
                return True
        except Exception:
            pass
        return False
    finally:
        db.close()


@router.message(Command("casinos"))
async def cmd_admin_casinos(message: types.Message):
    """Admin-only: open casino stats via /casinos command."""
    if not is_admin(message.from_user.id):
        return
    db = SessionLocal()
    try:
        from models.drop_event import DropEvent
        from collections import Counter
        drops = db.query(DropEvent).all()
        counts = Counter()
        for d in drops:
            if d.payload and isinstance(d.payload, dict):
                for o in d.payload.get('outcomes', []) or []:
                    c = o.get('casino')
                    if c:
                        counts[c] += 1
        sorted_casinos = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        text = "🎰 <b>STATISTIQUES CASINOS</b>\n\n"
        text += "<b>Classement par nombre d'apparitions:</b>\n<i>(Chaque call arbitrage = 2 casinos)</i>\n\n"
        if not sorted_casinos:
            text += "Aucun casino trouvé dans les calls.\n"
        else:
            for i, (casino, count) in enumerate(sorted_casinos, 1):
                logo = get_casino_logo(casino)
                text += f"{i}. {logo} <b>{casino}</b>: {count} calls\n"
        text += f"\n📊 <b>Total calls analysés: {len(drops)}</b>"
        kb = [[InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")]]
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()

@router.callback_query(F.data.startswith("admin_user_stats_"))
async def callback_admin_user_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    uid = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == uid).first()
        if not u:
            await callback.message.edit_text("❌ User introuvable")
            return
        today = date.today()
        week_ago = today - timedelta(days=7)
        # Today
        t = db.query(func.sum(DailyStats.total_bets), func.sum(DailyStats.total_staked), func.sum(DailyStats.total_profit)).filter(DailyStats.user_id == uid, DailyStats.date == today).first()
        # Week
        w = db.query(func.sum(DailyStats.total_bets), func.sum(DailyStats.total_staked), func.sum(DailyStats.total_profit)).filter(DailyStats.user_id == uid, DailyStats.date >= week_ago).first()
        # All
        a = db.query(func.sum(DailyStats.total_bets), func.sum(DailyStats.total_staked), func.sum(DailyStats.total_profit)).filter(DailyStats.user_id == uid).first()
        t_b, t_s, t_p = int(t[0] or 0), float(t[1] or 0), float(t[2] or 0)
        w_b, w_s, w_p = int(w[0] or 0), float(w[1] or 0), float(w[2] or 0)
        a_b, a_s, a_p = int(a[0] or 0), float(a[1] or 0), float(a[2] or 0)
        roi_t = (t_p / t_s * 100) if t_s > 0 else 0
        roi_w = (w_p / w_s * 100) if w_s > 0 else 0
        roi_a = (a_p / a_s * 100) if a_s > 0 else 0
        uname = u.username or str(uid)
        text = (
            f"👤 <b>@{uname}</b> — ID <code>{uid}</code>\n\n"
            f"📅 <b>Aujourd'hui</b>\n• Bets: {t_b}\n• Misé: ${t_s:.2f}\n• Profit: ${t_p:.2f}\n• ROI: {roi_t:.1f}%\n\n"
            f"📆 <b>7 jours</b>\n• Bets: {w_b}\n• Misé: ${w_s:.2f}\n• Profit: ${w_p:.2f}\n• ROI: {roi_w:.1f}%\n\n"
            f"🏆 <b>All-time</b>\n• Bets: {a_b}\n• Misé: ${a_s:.2f}\n• Profit: ${a_p:.2f}\n• ROI: {roi_a:.1f}%\n"
        )
        kb = [
            [InlineKeyboardButton(text="📜 My Bets", callback_data=f"admin_user_mybets_{uid}_1")],
            [InlineKeyboardButton(text="◀️ Retour", callback_data=f"admin_user_{uid}")],
        ]
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_user_mybets_"))
async def callback_admin_user_mybets(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    parts = callback.data.split("_")
    uid = int(parts[3])
    page = int(parts[4]) if len(parts) > 4 else 1
    per_page = 10
    offset = (page - 1) * per_page
    db = SessionLocal()
    try:
        uname = (db.query(User).filter(User.telegram_id == uid).first() or User(username=str(uid))).username or str(uid)
        q = db.query(UserBet).filter(UserBet.user_id == uid).order_by(UserBet.created_at.desc())
        total = q.count()
        bets = q.limit(per_page).offset(offset).all()
        if not bets:
            await callback.message.edit_text("📜 My Bets\n\nAucun bet.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Retour", callback_data=f"admin_user_{uid}")]]))
            return
        lines = [f"📜 <b>My Bets</b> — @{uname} (Page {page})\n"]
        for b in bets:
            profit = b.actual_profit if (b.actual_profit is not None) else b.expected_profit
            roi = (profit / b.total_stake * 100) if b.total_stake > 0 else 0
            when = b.bet_date.strftime('%d/%m/%y') if b.bet_date else (b.created_at.strftime('%d/%m/%y') if b.created_at else '-')
            lines.append(
                f"• {when} — Stake ${b.total_stake:.2f} — Profit ${profit:.2f} (ROI {roi:.1f}%)"
            )
        text = "\n".join(lines)
        nav = []
        total_pages = (total + per_page - 1) // per_page
        if page > 1:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_user_mybets_{uid}_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_user_mybets_{uid}_{page+1}"))
        kb = []
        if nav:
            kb.append(nav)
        kb.append([InlineKeyboardButton(text="◀️ Retour", callback_data=f"admin_user_{uid}")])
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()

async def _build_admin_dashboard(telegram_id: int):
    """Build admin dashboard with role-based permissions"""
    db = SessionLocal()
    try:
        # Get user role
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        role = user.role if user else "user"
        is_super = (role == "super_admin")
        
        total_users = db.query(User).count()
        free_users = db.query(User).filter(User.tier == TierLevel.FREE).count()
        premium_users = db.query(User).filter(User.tier == TierLevel.PREMIUM).count()
        paid_premium_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.free_access == False
        ).count()
        free_access_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.free_access == True
        ).count()
        
        # Only super admin sees revenue
        revenue_text = ""
        if is_super:
            monthly_revenue = paid_premium_users * TierManager.get_price(CoreTierLevel.PREMIUM)
            revenue_text = (
                f"\n💰 <b>REVENUE (est.)</b>\n"
                f"💵 Mensuel: <b>${monthly_revenue:,}</b>\n"
                f"💸 Annuel: <b>${monthly_revenue * 12:,}</b>\n"
                f"  <i>(Based on {paid_premium_users} paid users)</i>"
            )
        
        day_ago = datetime.now() - timedelta(days=1)
        new_users_today = db.query(User).filter(User.created_at >= day_ago).count()
        alerts_today_total = db.query(func.sum(User.alerts_today)).filter(User.last_alert_date == date.today()).scalar() or 0
        total_profit = db.query(func.sum(User.total_profit)).scalar() or 0
        
        # Check backup status for super admin
        backup_status = ""
        if is_super:
            try:
                from bot.auto_backup import AutoBackupManager
                from config import ADMIN_CHAT_ID
                backup_manager = AutoBackupManager(None, int(ADMIN_CHAT_ID))
                backup_ready = backup_manager.is_backup_ready()
                days_until = backup_manager.days_until_next_backup()
                if backup_ready:
                    backup_status = "\n\n🗄️ <b>BACKUP STATUS</b>\n🔴 <b>BACKUP READY</b> - Click below to receive!"
                else:
                    backup_status = f"\n\n🗄️ <b>BACKUP STATUS</b>\n✅ Backup up to date (next in {days_until}d)"
            except Exception as e:
                backup_status = "\n\n🗄️ <b>BACKUP STATUS</b>\n⚠️ Backup system unavailable"
        
        role_emoji = "👑" if is_super else "🛠️"
        role_text = "SUPER ADMIN" if is_super else "ADMIN"
        
        admin_text = (
            f"{role_emoji} <b>{role_text} PANEL</b>\n\n"
            "📊 <b>STATISTIQUES</b>\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"  ├ Free: {free_users}\n"
            f"  └ Premium: {premium_users} ({paid_premium_users} paid + {free_access_users} free)"
            f"{revenue_text}\n\n"
            f"📈 <b>CROISSANCE</b>\n"
            f"🆕 Nouveaux (24h): <b>{new_users_today}</b>\n"
            f"📨 Alerts today: <b>{alerts_today_total}</b>\n\n"
            f"💎 <b>PROFIT USERS</b>\n"
            f"📊 Total: <b>${total_profit:,.2f}</b>"
            f"{backup_status}"
        )
        
        # Build keyboard based on role
        keyboard = [
            [
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users_1"),
                InlineKeyboardButton(text="💎 Premium Users", callback_data="admin_premium_1"),
            ],
            [
                InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
                InlineKeyboardButton(text="📎 Feedbacks", callback_data="admin_fb_menu"),
            ],
            [
                InlineKeyboardButton(text="💰 Affiliates", callback_data="admin_affiliates"),
                InlineKeyboardButton(text="💳 Paiements", callback_data="admin_payments"),
            ],
        ]
        
        # Super admin only sections
        if is_super:
            # Count pending actions
            pending_count = db.execute(text("""
                SELECT COUNT(*) FROM admin_actions WHERE status = 'pending'
            """)).scalar() or 0
            
            pending_badge = f" ({pending_count})" if pending_count > 0 else ""
            
            keyboard.extend([
                [
                    InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
                    InlineKeyboardButton(text=f"👑 Manage Admins{pending_badge}", callback_data="manage_admins"),
                ],
                [
                    InlineKeyboardButton(text="🤝 Affiliates", callback_data="admin_affiliates"),
                    InlineKeyboardButton(text="🗃️ Backup DB", callback_data="admin_backup_now"),
                ],
                [
                    InlineKeyboardButton(text="🤖 ML System", callback_data="admin_ml_menu"),
                ],
            ])
        else:
            # Regular admin: broadcast requires approval
            keyboard.append([
                InlineKeyboardButton(text="📢 Request Broadcast", callback_data="admin_broadcast_request"),
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton(text="🔍 Rechercher", callback_data="admin_search"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_refresh"),
            ],
            [
                InlineKeyboardButton(text="◀️ Back to Menu", callback_data="main_menu"),
            ],
        ])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        return admin_text, reply_markup
    finally:
        db.close()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """
    /admin command - Main admin dashboard
    """
    # Delete the command message
    try:
        await message.delete()
    except Exception:
        pass
    if not is_admin(message.from_user.id):
        await message.answer("Admin ok")
        return
    text, markup = await _build_admin_dashboard(message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=markup)


@router.message(Command("test_arb"))
async def test_arbitrage(message: types.Message):
    """Admin-only: send a sample Arbitrage alert to admin chat"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    
    # Simulate an arbitrage drop via the /public/drop endpoint
    from main_new import app
    import httpx
    
    test_data = {
        "event_id": "test_arb_cmd",
        "arb_percentage": 3.45,
        "match": "Toronto Raptors vs Los Angeles Lakers",
        "league": "NBA",
        "market": "Total Points",
        "sport": "Basketball",
        "outcomes": [
            {
                "outcome": "Over 220.5",
                "odds": -200,
                "casino": "Betsson"
            },
            {
                "outcome": "Under 220.5",
                "odds": 255,
                "casino": "Coolbet"
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/public/drop",
                json=test_data,
                timeout=5.0
            )
            if response.status_code == 200:
                await message.answer("✅ Arbitrage test envoyé! Vérifie tes messages.")
            else:
                await message.answer(f"❌ Erreur: {response.status_code}")
    except Exception as e:
        await message.answer(f"❌ Erreur: {e}")


@router.message(Command("test_good_odds"))
async def test_good_odds(message: types.Message):
    """Admin-only: send a sample Good Odds alert to admin chat"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    sample = (
        "🚨 Positive EV Alert 3.92% 🚨\n"
        "Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +125 @ Betsson (Basketball, NBA)"
    )
    parsed = parse_positive_ev_notification(sample)
    if not parsed:
        await message.answer("Parse failed")
        return
    # Fake admin settings - show beginner profile with low EV warning
    user_cash = 500.0
    text = format_good_odds_message(parsed, user_cash, 'fr', user_profile='beginner', total_bets=0)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"{get_casino_logo(parsed['bookmaker'])} {parsed['bookmaker']}", url=get_fallback_url(parsed['bookmaker']))]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.message(Command("test_middle"))
async def test_middle(message: types.Message):
    """Admin-only: send a sample Middle alert to admin chat"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    sample = (
        "🚨 Middle Alert 3.1% 🚨\n"
        "Coastal Carolina vs North Dakota [Point Spread : Coastal Carolina +3.5/North Dakota -2] Coastal Carolina +3.5 -132 @ TonyBet, North Dakota -2 +150 @ LeoVegas (Basketball, NCAAB)"
    )
    parsed = parse_middle_notification(sample)
    if not parsed:
        await message.answer("Parse failed")
        return
    user_cash = 500.0
    calc = calculate_middle_stakes(parsed['side_a']['odds'], parsed['side_b']['odds'], user_cash)
    text = format_middle_message(parsed, calc, user_cash, 'fr')
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text=f"{get_casino_logo(parsed['side_a']['bookmaker'])} {parsed['side_a']['bookmaker']}", url=get_fallback_url(parsed['side_a']['bookmaker'])),
            types.InlineKeyboardButton(text=f"{get_casino_logo(parsed['side_b']['bookmaker'])} {parsed['side_b']['bookmaker']}", url=get_fallback_url(parsed['side_b']['bookmaker'])),
        ]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data == "admin_backup_now")
async def callback_admin_backup_now(callback: types.CallbackQuery):
    """Trigger database backup when admin clicks button"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.answer("🗄️ Starting backup...", show_alert=True)
    
    try:
        from bot.auto_backup import manual_backup_now
        from config import ADMIN_CHAT_ID
        
        # Send backup to admin
        await manual_backup_now(callback.bot, int(ADMIN_CHAT_ID))
        
        # Try to refresh admin panel, ignore "message not modified" error
        try:
            text, markup = await _build_admin_dashboard(callback.from_user.id)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception as edit_error:
            # Ignore "message is not modified" error - it's harmless
            if "message is not modified" not in str(edit_error).lower():
                raise edit_error
        
    except Exception as e:
        # Only show error if it's not the harmless "message not modified" error
        if "message is not modified" not in str(e).lower():
            await callback.bot.send_message(
                callback.from_user.id,
                f"❌ <b>Backup failed</b>\n\nError: {str(e)}",
                parse_mode=ParseMode.HTML
            )


@router.callback_query(F.data == "admin_refresh")
async def callback_admin_refresh(callback: types.CallbackQuery):
    """Refresh admin panel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("you are not admin motherfuckkk", show_alert=True)
        return
    await callback.answer()
    text, markup = await _build_admin_dashboard(callback.from_user.id)
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


@router.callback_query(F.data == "admin_ml_menu")
async def callback_admin_ml_menu(callback: types.CallbackQuery):
    """Show ML System menu with test commands"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.answer()
    
    text = (
        "🤖 <b>ML CALL LOGGER - SYSTEM MENU</b>\n\n"
        "Système de collecte de données pour l'IA\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>ML Stats:</b>\n"
        "Voir les statistiques complètes du logger\n"
        "• Success/Error count\n"
        "• Total calls en DB\n"
        "• Sports couverts\n"
        "• Santé du système\n\n"
        "🧪 <b>ML Test:</b>\n"
        "Tester le système de logging\n"
        "• Log un call test\n"
        "• Vérifie que la DB fonctionne\n"
        "• Retourne success/failure\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>Documentation:</b>\n"
        "Check ML_TROUBLESHOOTING.md si problème"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 ML Stats", callback_data="ml_stats_btn"),
            InlineKeyboardButton(text="🧪 ML Test", callback_data="ml_test_btn"),
        ],
        [
            InlineKeyboardButton(text="◀️ Retour Admin", callback_data="open_admin"),
        ]
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data == "ml_stats_btn")
async def callback_ml_stats_btn(callback: types.CallbackQuery):
    """Show ML Stats from button"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.answer("📊 Getting ML stats...")
    
    try:
        from utils.safe_call_logger import _safe_logger_instance
        from sqlalchemy import text as sql_text
        
        # Get logger stats
        if _safe_logger_instance is None:
            await callback.message.answer(
                "⚠️ <b>ML Logger not initialized</b>\n\n"
                "Logger will be initialized on next bot restart.\n"
                "Bot is running normally.",
                parse_mode=ParseMode.HTML
            )
            return
        
        safe_logger = _safe_logger_instance
        stats = safe_logger.get_stats()
        
        # Get DB stats
        db = SessionLocal()
        try:
            result = db.execute(sql_text("""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(DISTINCT sport) as sports_count,
                    COUNT(DISTINCT call_type) as types_count,
                    SUM(CASE WHEN users_clicked > 0 THEN 1 ELSE 0 END) as calls_with_clicks,
                    AVG(roi_percent) as avg_roi,
                    MIN(sent_at) as first_call,
                    MAX(sent_at) as last_call
                FROM arbitrage_calls
            """)).fetchone()
            
            if result and result[0] is not None:
                db_stats = {
                    'total_calls': result[0] or 0,
                    'sports_count': result[1] or 0,
                    'types_count': result[2] or 0,
                    'calls_with_clicks': result[3] or 0,
                    'avg_roi': round(result[4], 2) if result[4] else 0,
                    'first_call': result[5] if result[5] else 'N/A',
                    'last_call': result[6] if result[6] else 'N/A'
                }
            else:
                db_stats = {
                    'total_calls': 0,
                    'sports_count': 0,
                    'types_count': 0,
                    'calls_with_clicks': 0,
                    'avg_roi': 0,
                    'first_call': 'N/A',
                    'last_call': 'N/A'
                }
        finally:
            db.close()
        
        # Build message
        status_emoji = "✅" if stats['enabled'] else "❌"
        error_rate = stats['error_rate']
        health_emoji = "🟢" if error_rate < 5 else "🟡" if error_rate < 20 else "🔴"
        
        text = (
            f"📊 <b>ML CALL LOGGER - STATS</b>\n\n"
            f"{status_emoji} <b>Status:</b> {'Enabled' if stats['enabled'] else 'DISABLED'}\n"
            f"{health_emoji} <b>Health:</b> {100 - error_rate:.1f}%\n\n"
            f"📈 <b>LOGGER PERFORMANCE</b>\n"
            f"✅ Success: {stats['success_count']}\n"
            f"❌ Errors: {stats['error_count']}\n"
            f"📊 Error rate: {error_rate:.1f}%\n\n"
            f"💾 <b>DATABASE STATS</b>\n"
            f"📞 Total calls logged: {db_stats['total_calls']}\n"
            f"🏀 Sports covered: {db_stats['sports_count']}\n"
            f"📋 Call types: {db_stats['types_count']}\n"
            f"👆 Calls with clicks: {db_stats['calls_with_clicks']}\n"
            f"💰 Average ROI: {db_stats['avg_roi']}%\n\n"
        )
        
        if db_stats['first_call'] != 'N/A':
            text += (
                f"📅 <b>TIMELINE</b>\n"
                f"🥇 First call: {db_stats['first_call'][:19]}\n"
                f"🕐 Last call: {db_stats['last_call'][:19]}\n\n"
            )
        
        if error_rate > 20:
            text += "⚠️ <b>WARNING:</b> High error rate!\n"
        elif error_rate > 5:
            text += "💡 <b>TIP:</b> Monitor errors\n"
        else:
            text += "✅ <b>ALL SYSTEMS NOMINAL</b>\n"
        
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await callback.message.answer(
            f"❌ <b>Error getting ML stats</b>\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data == "ml_test_btn")
async def callback_ml_test_btn(callback: types.CallbackQuery):
    """Run ML Test from button"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.answer("🧪 Running ML test...")
    
    try:
        from utils.safe_call_logger import _safe_logger_instance
        from datetime import datetime
        
        if _safe_logger_instance is None:
            await callback.message.answer(
                "⚠️ <b>ML Logger not initialized</b>\n\n"
                "Logger will be initialized on next bot restart.\n"
                "Bot is running normally.",
                parse_mode=ParseMode.HTML
            )
            return
        
        safe_logger = _safe_logger_instance
        
        # Log test call
        success = await safe_logger.log_call_safe(
            call_type='arbitrage',
            sport='TEST',
            team_a='Test Team A',
            team_b='Test Team B',
            book_a='TestBook1',
            book_b='TestBook2',
            odds_a=-110,
            odds_b=+105,
            roi_percent=2.5,
            stake_a=100,
            stake_b=100,
            users_notified=1
        )
        
        if success:
            await callback.message.answer(
                "✅ <b>ML LOGGING TEST - SUCCESS</b>\n\n"
                "Test call logged successfully!\n\n"
                "Check database:\n"
                "<code>SELECT * FROM arbitrage_calls WHERE sport='TEST';</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.answer(
                "❌ <b>ML LOGGING TEST - FAILED</b>\n\n"
                "Could not log test call\n\n"
                "Check ML_TROUBLESHOOTING.md",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        await callback.message.answer(
            f"❌ <b>ML TEST ERROR</b>\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data.startswith("admin_users_"))
async def callback_admin_users(callback: types.CallbackQuery):
    """Show users list with pagination"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        per_page = 10
        offset = (page - 1) * per_page
        users = db.query(User).order_by(User.created_at.desc()).limit(per_page).offset(offset).all()
        total_users = db.query(User).count()
        total_pages = (total_users + per_page - 1) // per_page
        tier_emoji = {
            TierLevel.FREE: "🆓",
            TierLevel.PREMIUM: "💎",
        }
        users_text = f"👥 <b>USERS - Page {page}/{total_pages}</b>\n\n"
        keyboard = []
        for user in users:
            emoji = tier_emoji.get(user.tier, "🆓")
            username = user.username or "No username"
            today_alerts = user.alerts_today if user.last_alert_date == date.today() else 0
            
            # Check bonus status
            bonus_status = ""
            try:
                bonus_result = db.execute(text("""
                    SELECT bonus_activated_at, bonus_expires_at, bonus_redeemed, ever_had_bonus
                    FROM bonus_tracking
                    WHERE telegram_id = :tid
                """), {'tid': user.telegram_id}).first()
                
                if bonus_result:
                    if bonus_result.bonus_redeemed:
                        bonus_status = " | BONUS: APPLIED ✅"
                    elif bonus_result.bonus_activated_at:
                        # Check if expired
                        expires_at = bonus_result.bonus_expires_at
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at)
                        if datetime.now() > expires_at:
                            bonus_status = " | BONUS: EXPIRED ❌"
                        else:
                            # Active bonus
                            time_left = expires_at - datetime.now()
                            days_left = int(time_left.total_seconds() // 86400)
                            bonus_status = f" | BONUS: {days_left}d left 🎁"
            except Exception as e:
                logger.error(f"Error checking bonus for user {user.telegram_id}: {e}")
            
            users_text += (
                f"{emoji} <b>@{username}</b>\n"
                f"   ID: <code>{user.telegram_id}</code>\n"
                f"   Tier: {user.tier.value.upper()} | Today alerts: {today_alerts} | Profit: ${user.net_profit:.2f}{bonus_status}\n"
                f"\n"
            )
            keyboard.append([InlineKeyboardButton(text=f"👤 Gérer @{username}", callback_data=f"admin_user_{user.telegram_id}")])
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"admin_users_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"admin_users_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton(text="🔍 Rechercher", callback_data="admin_search")])
        keyboard.append([InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            users_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_casinos")
async def callback_admin_casinos(callback: types.CallbackQuery):
    """Show casino statistics - count appearances in arbitrage calls"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    db = SessionLocal()
    try:
        from models.drop_event import DropEvent
        from collections import Counter
        
        # Get all arbitrage drops
        drops = db.query(DropEvent).all()
        
        # Count casino occurrences (each call has 2 casinos, each +1)
        casino_counts = Counter()
        
        for drop in drops:
            if drop.payload and isinstance(drop.payload, dict):
                outcomes = drop.payload.get('outcomes', [])
                for outcome in outcomes:
                    casino = outcome.get('casino')
                    if casino:
                        casino_counts[casino] += 1
        
        # Sort by count descending
        sorted_casinos = sorted(casino_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Build message
        text = "🎰 <b>STATISTIQUES CASINOS</b>\n\n"
        text += "<b>Classement par nombre d'apparitions:</b>\n"
        text += "<i>(Chaque call arbitrage = 2 casinos)</i>\n\n"
        
        if not sorted_casinos:
            text += "Aucun casino trouvé dans les calls.\n"
        else:
            for i, (casino, count) in enumerate(sorted_casinos, 1):
                logo = get_casino_logo(casino)
                text += f"{i}. {logo} <b>{casino}</b>: {count} calls\n"
        
        total_calls = len(drops)
        text += f"\n📊 <b>Total calls analysés: {total_calls}</b>"
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: types.CallbackQuery):
    """Show detailed statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    db = SessionLocal()
    try:
        from models.bet import DailyStats, UserBet
        
        # Count only PAID premium users (exclude free_access)
        paid_premium_users = db.query(User).filter(
            User.tier == TierLevel.PREMIUM,
            User.free_access == False
        ).count()
        premium_revenue = paid_premium_users * TierManager.get_price(CoreTierLevel.PREMIUM)
        total_revenue = premium_revenue
        periods = [1, 7, 30]
        growth_stats = {}
        for days in periods:
            dt = datetime.now() - timedelta(days=days)
            count = db.query(User).filter(User.created_at >= dt).count()
            growth_stats[days] = count
        
        # NEW BET TRACKING STATS
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Today stats
        today_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(DailyStats.date == today).first()
        
        # Yesterday stats  
        yesterday_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(DailyStats.date == yesterday).first()
        
        # Week stats
        week_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(DailyStats.date >= week_ago).first()
        
        # All-time stats
        all_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).first()
        
        # Top bettors
        top_users = db.query(
            DailyStats.user_id,
            func.sum(DailyStats.total_bets).label('bets'),
            func.sum(DailyStats.total_staked).label('staked'),
            func.sum(DailyStats.total_profit).label('profit')
        ).group_by(DailyStats.user_id).order_by(func.sum(DailyStats.total_profit).desc()).limit(5).all()
        
        today_bets = int(today_stats[0] or 0)
        today_staked = float(today_stats[1] or 0)
        today_profit = float(today_stats[2] or 0)
        
        yesterday_bets = int(yesterday_stats[0] or 0)
        yesterday_profit = float(yesterday_stats[2] or 0)
        
        week_bets = int(week_stats[0] or 0)
        week_staked = float(week_stats[1] or 0)
        week_profit = float(week_stats[2] or 0)
        
        all_bets = int(all_stats[0] or 0)
        all_staked = float(all_stats[1] or 0)
        all_profit = float(all_stats[2] or 0)
        
        roi_today = (today_profit / today_staked * 100) if today_staked > 0 else 0
        roi_week = (week_profit / week_staked * 100) if week_staked > 0 else 0
        roi_all = (all_profit / all_staked * 100) if all_staked > 0 else 0
        
        stats_text = (
            "📊 <b>STATISTIQUES DÉTAILLÉES</b>\n\n"
            "<b>💰 REVENUE (PAID only)</b>\n"
            f"💎 Premium: ${premium_revenue:,} ({paid_premium_users} users)\n"
            f"📊 Total/mois: <b>${total_revenue:,}</b>\n"
            f"📈 Total/an: <b>${total_revenue * 12:,}</b>\n\n"
            "<b>📈 CROISSANCE</b>\n"
            f"├ Dernières 24h: {growth_stats[1]}\n"
            f"├ Derniers 7j: {growth_stats[7]}\n"
            f"└ Derniers 30j: {growth_stats[30]}\n\n"
            "<b>🎯 BET TRACKING</b>\n"
            f"<b>📅 Aujourd'hui:</b>\n"
            f"  • Bets: {today_bets}\n"
            f"  • Misé: ${today_staked:,.2f}\n"
            f"  • Profit: ${today_profit:,.2f}\n"
            f"  • ROI: {roi_today:.1f}%\n\n"
            f"<b>📆 7 derniers jours:</b>\n"
            f"  • Bets: {week_bets}\n"
            f"  • Misé: ${week_staked:,.2f}\n"
            f"  • Profit: ${week_profit:,.2f}\n"
            f"  • ROI: {roi_week:.1f}%\n\n"
            f"<b>🏆 All-time:</b>\n"
            f"  • Bets: {all_bets}\n"
            f"  • Misé: ${all_staked:,.2f}\n"
            f"  • Profit: ${all_profit:,.2f}\n"
            f"  • ROI: {roi_all:.1f}%\n\n"
            f"<b>🔥 TOP 5 BETTORS (profit):</b>\n"
        )
        
        for i, (user_id, bets, staked, profit) in enumerate(top_users, 1):
            user = db.query(User).filter(User.telegram_id == user_id).first()
            username = user.username if user else str(user_id)
            roi = (profit / staked * 100) if staked > 0 else 0
            stats_text += f"{i}. @{username}: ${profit:,.2f} ({int(bets)} bets, ROI {roi:.1f}%)\n"
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_affiliates")
async def callback_admin_affiliates(callback: types.CallbackQuery):
    """Affiliate dashboard: list referrers with counts and pending payouts + NEW commission tiers."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    db = SessionLocal()
    try:
        # Load NEW referrals from file storage
        import json
        import os
        referrals_file = "/tmp/referrals_storage.json"
        referrals_storage = {}
        
        if os.path.exists(referrals_file):
            with open(referrals_file, 'r') as f:
                referrals_storage = json.load(f)
        
        # Commission tiers calculation function
        def calculate_commission_rate(referral_count: int, is_alpha: bool = False) -> dict:
            if referral_count >= 30:
                return {"rate": 40.0, "tier": "🏆 Champion"}
            elif referral_count >= 20:
                return {"rate": 30.0, "tier": "🌟 Elite"}
            elif referral_count >= 10:
                return {"rate": 25.0, "tier": "💎 Diamond"}
            elif referral_count >= 5:
                return {"rate": 15.0, "tier": "⭐ Star + Alpha"}
            elif is_alpha:
                return {"rate": 12.5, "tier": "👑 Alpha"}
            else:
                return {"rate": 10.0, "tier": "🎯 Base"}
        
        # Aggregate OLD tier1 by referrer (database)
        from sqlalchemy import func
        tier1 = db.query(
            Referral.referrer_id,
            func.count(Referral.id),
            func.sum(Referral.pending_commission),
            func.sum(Referral.total_earned),
        ).group_by(Referral.referrer_id).all()
        
        # Aggregate OLD tier2 by original referrer (database)
        tier2 = db.query(
            ReferralTier2.original_referrer_id,
            func.count(ReferralTier2.id),
            func.sum(ReferralTier2.pending_commission),
            func.sum(ReferralTier2.total_earned),
        ).group_by(ReferralTier2.original_referrer_id).all()
        t2_map = {r[0]: r[1:] for r in tier2}
        
        lines = ["🤝 <b>AFFILIATES DASHBOARD</b>\n"]
        lines.append(f"📊 <b>NEW System:</b> {len(referrals_storage)} users, {sum(len(refs) for refs in referrals_storage.values())} referrals\n")
        
        # Show NEW referrals from file storage
        if referrals_storage:
            lines.append("<b>🆕 NEW REFERRALS (File Storage):</b>")
            for user_id, refs in referrals_storage.items():
                count = len(refs)
                commission = calculate_commission_rate(count)
                u = db.query(User).filter(User.id == int(user_id)).first()
                uname = f"@{u.username}" if u and u.username else f"User{user_id}"
                lines.append(f"{uname} — {count} refs | {commission['tier']} ({commission['rate']}%)")
            lines.append("")
        
        # Show OLD referrals from database
        rows = []
        if tier1:
            lines.append("<b>📜 OLD REFERRALS (Database):</b>")
            for ref_id, cnt1, pend1, earn1 in tier1:
                cnt2, pend2, earn2 = t2_map.get(ref_id, (0, 0.0, 0.0))
                cnt1 = cnt1 or 0
                cnt2 = cnt2 or 0
                total_cnt = cnt1 + cnt2
                total_pending = float(pend1 or 0.0) + float(pend2 or 0.0)
                total_earned = float(earn1 or 0.0) + float(earn2 or 0.0)
                
                u = db.query(User).filter(User.telegram_id == ref_id).first()
                uname = f"@{u.username}" if u and u.username else str(ref_id)
                lines.append(f"{uname} — T1:{cnt1} T2:{cnt2} | Pending: ${total_pending:.2f} | Earned: ${total_earned:.2f}")
                rows.append([InlineKeyboardButton(text=f"👤 {uname}", callback_data=f"admin_affiliate_{ref_id}")])
        
        # Commission tiers summary
        lines.append("\n<b>💰 COMMISSION TIERS:</b>")
        lines.append("🎯 Base: 10% | 👑 Alpha: 12.5%")
        lines.append("⭐ Star (5+): 15% + Alpha | 💎 Diamond (10+): 25%")
        lines.append("🌟 Elite (20+): 30% | 🏆 Champion (30+): 40%")
        
        if len(rows) == 0:
            rows.append([InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")])
        else:
            rows.append([InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")])
        
        if not referrals_storage and not tier1:
            await callback.message.edit_text("🤝 Aucun affilié trouvé", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        else:
            await callback.message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_affiliate_"))
async def callback_admin_affiliate_detail(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    ref_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        # Gather detail
        t1 = db.query(Referral).filter(Referral.referrer_id == ref_id).all()
        t2 = db.query(ReferralTier2).filter(ReferralTier2.original_referrer_id == ref_id).all()
        u = db.query(User).filter(User.telegram_id == ref_id).first()
        uname = f"@{u.username}" if u and u.username else str(ref_id)
        pend = sum(r.pending_commission for r in t1) + sum(r.pending_commission for r in t2)
        earned = sum(r.total_earned for r in t1) + sum(r.total_earned for r in t2)
        active_directs = db.query(Referral).filter(Referral.referrer_id == ref_id, Referral.is_active == True).count()
        # Detail text
        txt = (
            f"👤 <b>{uname}</b>\n"
            f"Directs actifs: {active_directs}\n"
            f"T1: {len(t1)}  •  T2: {len(t2)}\n"
            f"🕒 Pending: ${pend:.2f}  •  💵 Earned: ${earned:.2f}\n"
            f"➡️ Payer le pending au referrer?"
        )
        kb = [
            [InlineKeyboardButton(text="💸 Mark All Paid", callback_data=f"admin_affiliate_pay_{ref_id}")],
            [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_affiliates")],
        ]
        await callback.message.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_affiliate_pay_"))
async def callback_admin_affiliate_pay(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    ref_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        t1 = db.query(Referral).filter(Referral.referrer_id == ref_id).all()
        t2 = db.query(ReferralTier2).filter(ReferralTier2.original_referrer_id == ref_id).all()
        paid_amt = 0.0
        for r in t1:
            amt = float(r.pending_commission or 0.0)
            if amt > 0:
                r.mark_paid(amt)
                paid_amt += amt
        for r in t2:
            amt = float(r.pending_commission or 0.0)
            if amt > 0:
                r.mark_paid(amt)
                paid_amt += amt
        db.commit()
        await callback.message.answer(f"✅ Paid recorded: ${paid_amt:.2f}")
        # Return to detail
        await callback_admin_affiliate_detail(callback)
    finally:
        db.close()


@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: types.CallbackQuery):
    """Show broadcast menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    broadcast_text = (
        "📢 <b>BROADCAST MESSAGE</b>\n\n"
        "Sélectionne la cible:"
    )
    keyboard = [
        [InlineKeyboardButton(text="👥 Tous les Users", callback_data="broadcast_all")],
        [InlineKeyboardButton(text="🆓 FREE", callback_data="broadcast_free")],
        [InlineKeyboardButton(text="💎 PREMIUM", callback_data="broadcast_premium")],
        [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(
        broadcast_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


@router.callback_query(F.data.startswith("broadcast_"))
async def callback_broadcast_target(callback: types.CallbackQuery, state: FSMContext):
    """Start broadcast - await message"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    target = callback.data.split("_")[1]
    await state.update_data(broadcast_target=target)
    await state.set_state(AdminStates.awaiting_broadcast)
    await callback.message.edit_text(
        f"📝 <b>BROADCAST - {target.upper()}</b>\n\n"
        "Envoie maintenant ton message.\n"
        "Il sera envoyé à tous les users ciblés.\n\n"
        "Pour annuler, tape /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.awaiting_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    """Process and send broadcast"""
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    db = SessionLocal()
    try:
        if target == "all":
            users = db.query(User).filter(User.notifications_enabled == True).all()
        else:
            tier_level = TierLevel[target.upper()]
            users = db.query(User).filter(
                User.tier == tier_level,
                User.notifications_enabled == True
            ).all()
        success_count = 0
        fail_count = 0
        progress_msg = await message.answer(
            f"📤 Envoi en cours...\n0/{len(users)} envoyés"
        )
        for i, user in enumerate(users):
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message.text,
                    parse_mode=ParseMode.HTML
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"Failed to send to {user.telegram_id}: {e}")
            if (i + 1) % 10 == 0:
                try:
                    await progress_msg.edit_text(
                        f"📤 Envoi en cours...\n{i+1}/{len(users)} envoyés"
                    )
                except:
                    pass
        await progress_msg.edit_text(
            f"✅ <b>BROADCAST TERMINÉ</b>\n\n"
            f"✅ Envoyés: {success_count}\n"
            f"❌ Échecs: {fail_count}\n"
            f"📊 Total: {len(users)}",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
    finally:
        db.close()


@router.callback_query(F.data == "admin_search")
async def callback_admin_search(callback: types.CallbackQuery, state: FSMContext):
    """Start user search"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.awaiting_search)
    await callback.message.edit_text(
        "🔍 <b>RECHERCHER USER</b>\n\n"
        "Envoie le username (sans @) ou le Telegram ID\n\n"
        "Pour annuler, tape /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.awaiting_search)
async def process_search(message: types.Message, state: FSMContext):
    """Process search query"""
    if not is_admin(message.from_user.id):
        return
    # Allow '/cancel' to exit gracefully from within FSM before attempting DB search
    txt = (message.text or "").strip().lower()
    if txt in ("/cancel", "cancel"):
        await cancel_command(message, state)
        return
    search_term = message.text.strip()
    db = SessionLocal()
    try:
        user = None
        if search_term.isdigit():
            user = db.query(User).filter(User.telegram_id == int(search_term)).first()
        if not user:
            user = db.query(User).filter(User.username.ilike(f'%{search_term}%')).first()
        if not user:
            await message.answer(
                f"❌ User non trouvé: {search_term}",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        tier_emoji = {
            TierLevel.FREE: "🆓",
            TierLevel.PREMIUM: "💎",
        }
        emoji = tier_emoji.get(user.tier, "🆓")
        user_text = (
            f"👤 <b>USER DETAILS</b>\n\n"
            f"{emoji} <b>@{user.username or 'N/A'}</b>\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Tier: <b>{user.tier.value.upper()}</b>\n"
            f"Profit: <b>${user.net_profit:.2f}</b>\n"
            f"Bets: {user.total_bets}\n"
            f"Inscrit: {user.created_at.strftime('%Y-%m-%d')}"
        )
        keyboard = [
            [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(
            user_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        await state.clear()
    finally:
        db.close()


@router.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    """Cancel current operation"""
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    # Offer quick navigation after cancel
    kb = [[InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")]]
    try:
        if is_admin(message.from_user.id):
            kb.append([InlineKeyboardButton(text="🛠️ Admin", callback_data="admin_refresh")])
    except Exception:
        pass
    await message.answer("❌ Opération annulée", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "open_admin")
async def callback_open_admin(callback: types.CallbackQuery):
    """Open admin panel from menu button - Clean Apple style"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    text, markup = await _build_admin_dashboard(callback.from_user.id)
    
    # Delete the menu message for clean Apple-style navigation
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Send admin panel in a new clean message
    await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=markup)


# ===== Additional Admin: Premium list and user management =====

@router.callback_query(F.data.startswith("admin_premium_"))
async def callback_admin_premium(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        per_page = 10
        offset = (page - 1) * per_page
        users = db.query(User).filter(User.tier == TierLevel.PREMIUM).order_by(User.subscription_end.desc()).limit(per_page).offset(offset).all()
        total_users = db.query(User).filter(User.tier == TierLevel.PREMIUM).count()
        total_pages = (total_users + per_page - 1) // per_page
        text = f"💎 <b>PREMIUM USERS - Page {page}/{total_pages}</b>\n\n"
        for u in users:
            exp = u.subscription_end.strftime('%Y-%m-%d') if u.subscription_end else 'N/A'
            text += f"💎 @{u.username or 'N/A'} — ID <code>{u.telegram_id}</code> — Expires: {exp}\n"
        kb = []
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"admin_premium_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"admin_premium_{page+1}"))
        if nav:
            kb.append(nav)
        kb.append([InlineKeyboardButton(text="◀️ Retour", callback_data="admin_refresh")])
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_user_"))
async def callback_admin_user_detail(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    
    # Check if caller is super admin or regular admin
    from bot.admin_approval_system import is_super_admin
    is_super = is_super_admin(callback.from_user.id)
    
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.message.edit_text("❌ User introuvable")
            return
        today_alerts = u.alerts_today if u.last_alert_date == date.today() else 0
        if u.subscription_end:
            exp = u.subscription_end.strftime('%Y-%m-%d')
        elif u.tier == TierLevel.PREMIUM:
            exp = 'LIFETIME'
        else:
            exp = '—'
        # Get email from website users table if exists
        email_info = "N/A"
        try:
            from models import WebsiteUser
            website_user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == user_id).first()
            if website_user and website_user.email:
                email_info = website_user.email
        except Exception:
            pass
        
        text = (
            f"👤 <b>USER</b> @{'N/A' if not u.username else u.username}\n"
            f"ID: <code>{u.telegram_id}</code>\n"
            f"📧 Email: <code>{email_info}</code>\n"
            f"Tier: <b>{u.tier.value.upper()}</b> | Expires: {exp}\n"
            f"Notif: {'✅' if u.notifications_enabled else '❌'} | Banned: {'🚫' if u.is_banned else '✅'}\n"
            f"Alerts today: {today_alerts}\n"
        )
        
        # Build keyboard based on admin role
        if is_super:
            # Super admin: full access
            kb = [
                [InlineKeyboardButton(text="💎 Grant 30j", callback_data=f"admin_grant_{u.telegram_id}"), InlineKeyboardButton(text="♾️ Lifetime Premium", callback_data=f"admin_lifetime_{u.telegram_id}")],
                [InlineKeyboardButton(text="🎁 Free Access", callback_data=f"admin_freeaccess_{u.telegram_id}"), InlineKeyboardButton(text="⬇️ Revoke FREE", callback_data=f"admin_revoke_{u.telegram_id}")],
                [InlineKeyboardButton(text="👁️ See Pass", callback_data=f"admin_seepass_{u.telegram_id}"), InlineKeyboardButton(text="🔑 Change Pass", callback_data=f"admin_changepass_{u.telegram_id}")],
                [InlineKeyboardButton(text="🗑️ Delete Account", callback_data=f"admin_deleteacc_{u.telegram_id}")],
                [InlineKeyboardButton(text="✏️ Affiliate %", callback_data=f"admin_setaff_{u.id}")],
                [InlineKeyboardButton(text=("🚫 Ban" if not u.is_banned else "✅ Unban"), callback_data=f"admin_toggleban_{u.telegram_id}")],
                [InlineKeyboardButton(text=("🔕 Disable Notif" if u.notifications_enabled else "🔔 Enable Notif"), callback_data=f"admin_togglenotif_{u.telegram_id}")],
                [InlineKeyboardButton(text="📊 Stats", callback_data=f"admin_user_stats_{u.telegram_id}"), InlineKeyboardButton(text="📜 My Bets", callback_data=f"admin_user_mybets_{u.telegram_id}_1")],
                [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_users_1")],
            ]
        else:
            # Regular admin: restricted access (only Free Access with approval and Ban with approval)
            kb = [
                [InlineKeyboardButton(text="🎁 Request Free Access (max 7j)", callback_data=f"admin_request_free_{u.telegram_id}")],
                [InlineKeyboardButton(text=("🚫 Request Ban" if not u.is_banned else "✅ Request Unban"), callback_data=f"admin_request_ban_{u.telegram_id}")],
                [InlineKeyboardButton(text="📊 Stats", callback_data=f"admin_user_stats_{u.telegram_id}"), InlineKeyboardButton(text="📜 My Bets", callback_data=f"admin_user_mybets_{u.telegram_id}_1")],
                [InlineKeyboardButton(text="◀️ Retour", callback_data="admin_users_1")],
            ]
        
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_grant_"))
async def callback_admin_grant(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User introuvable", show_alert=True)
            return
        u.tier = TierLevel.PREMIUM
        u.subscription_start = datetime.now()
        u.subscription_end = datetime.now() + timedelta(days=30)
        # Enable Good Odds and Middle alerts for Premium users
        u.enable_good_odds = True
        u.enable_middle = True
        db.commit()
        # Try to DM the upgraded user a welcome/instructions message
        dm_sent = False
        try:
            exp = u.subscription_end.strftime('%Y-%m-%d') if u.subscription_end else ''
            lang = getattr(u, 'language', None) or 'en'
            if lang == 'fr':
                text = (
                    f"✅ <b>Bienvenue en PREMIUM!</b>\n\n"
                    f"Ton accès est actif pendant <b>30 jours</b> (jusqu'au <b>{exp}</b>).\n\n"
                    "<b>Important:</b> Lis le <b>/guide</b> complet <b>(10-15 minutes)</b> pour éviter $500+ d'erreurs.\n\n"
                    "Ensuite, enjoy:\n"
                    "• Ouvre le <b>Menu</b> pour voir les alertes et options\n"
                    "• Clique sur <b>Settings</b> dans le menu pour régler ton CASHH\n"
                    "• Consulte <b>/help</b> pour les commandes\n\n"
                    "💰 Let's make money!"
                )
            else:
                text = (
                    f"✅ <b>Welcome to PREMIUM!</b>\n\n"
                    f"Your access is active for <b>30 days</b> (until <b>{exp}</b>).\n\n"
                    "<b>Important:</b> Read the complete <b>/guide</b> <b>(10-15 minutes)</b> to avoid $500+ mistakes.\n\n"
                    "Then enjoy:\n"
                    "• Open the <b>Menu</b> to view alerts and options\n"
                    "• Click on <b>Settings</b> in the menu to set CASHH\n"
                    "• Click <b>I BET</b> after each arb to track profits\n"
                    "• Be quick: the faster you act, the better\n\n"
                    "Good luck and profits! 🚀"
                )
            await bot.send_message(u.telegram_id, text, parse_mode=ParseMode.HTML)
            dm_sent = True
        except Exception:
            dm_sent = False
    finally:
        db.close()
    if dm_sent:
        await callback.message.answer("✅ Premium 30j accordé • ✉️ Message envoyé")
    else:
        await callback.message.answer("✅ Premium 30j accordé • ⚠️ DM non envoyé")


@router.callback_query(F.data.startswith("admin_lifetime_"))
async def callback_admin_lifetime(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User introuvable", show_alert=True)
            return
        u.tier = TierLevel.PREMIUM
        u.subscription_start = datetime.now()
        u.subscription_end = None  # None = Lifetime
        # Enable Good Odds and Middle alerts for Lifetime Premium
        u.enable_good_odds = True
        u.enable_middle = True
        db.commit()
        # Try to DM the upgraded user
        dm_sent = False
        try:
            lang = getattr(u, 'language', None) or 'en'
            if lang == 'fr':
                dm_text = (
                    "🎉 <b>PREMIUM LIFETIME!</b>\n\n"
                    "Tu as maintenant un accès Premium à vie!\n\n"
                    "✅ Calls illimités\n"
                    "✅ Middle + Good Odds\n"
                    "✅ Tous les outils\n\n"
                    "Tape /menu pour commencer!"
                )
            else:
                dm_text = (
                    "🎉 <b>LIFETIME PREMIUM!</b>\n\n"
                    "You now have lifetime Premium access!\n\n"
                    "✅ Unlimited calls\n"
                    "✅ Middle + Good Odds\n"
                    "✅ All tools\n\n"
                    "Type /menu to start!"
                )
            await bot.send_message(u.telegram_id, dm_text, parse_mode=ParseMode.HTML)
            dm_sent = True
        except Exception:
            dm_sent = False
    finally:
        db.close()
    if dm_sent:
        await callback.message.answer("✅ Lifetime Premium accordé • ✉️ Message envoyé")
    else:
        await callback.message.answer("✅ Lifetime Premium accordé • ⚠️ DM non envoyé")


@router.callback_query(F.data.startswith("admin_revoke_"))
async def callback_admin_revoke(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User introuvable", show_alert=True)
            return
        u.tier = TierLevel.FREE
        u.subscription_end = None
        # Disable premium features when revoking to FREE
        u.enable_good_odds = False
        u.enable_middle = False
        db.commit()
    finally:
        db.close()
    await callback.message.answer("✅ Accès Premium révoqué (FREE)")


@router.callback_query(F.data.startswith("admin_toggleban_"))
async def callback_admin_toggleban(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User introuvable", show_alert=True)
            return
        u.is_banned = not u.is_banned
        db.commit()
        msg = "🚫 Banni" if u.is_banned else "✅ Unbanni"
    finally:
        db.close()
    await callback.message.answer(f"{msg}")


@router.callback_query(F.data.startswith("admin_setaff_"))
async def callback_admin_set_affiliate_rate(callback: types.CallbackQuery, state: FSMContext):
    """Prompt admin to set manual affiliate % override for a referrer (20..60)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    ref_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        current = db.query(ReferralSettings).filter(ReferralSettings.referrer_id == ref_id).first()
        cur_txt = f"Actuel: {int(current.override_rate*100)}%" if (current and current.override_rate is not None) else "Actuel: défaut (dynamique)"
    finally:
        db.close()
    await state.update_data(target_referrer_id=ref_id)
    await state.set_state(AdminStates.awaiting_aff_rate)
    await callback.message.answer(
        "✏️ <b>Affiliate % Override</b>\n\n"
        "Envoie une valeur entre <b>20</b> et <b>60</b> (ex: 25)\n"
        "Tape <code>reset</code> pour revenir au taux dynamique.\n\n"
        f"{cur_txt}",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.awaiting_aff_rate)
async def process_admin_set_affiliate_rate(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = (message.text or "").strip().lower()
    data = await state.get_data()
    ref_id = int(data.get("target_referrer_id", 0))
    if not ref_id:
        await state.clear()
        await message.answer("❌ Cible invalide")
        return
    db = SessionLocal()
    try:
        settings = db.query(ReferralSettings).filter(ReferralSettings.referrer_id == ref_id).first()
        if text in ("reset", "clear"):
            if settings and settings.override_rate is not None:
                settings.override_rate = None
                db.commit()
            await message.answer("✅ Override supprimé — retour au taux dynamique")
            await state.clear()
            return
        # parse percentage
        try:
            val = float(text.replace('%','').strip())
        except Exception:
            await message.answer("❌ Entrée invalide. Envoie un nombre entre 20 et 60, ou 'reset'.")
            return
        # clamp 20..60
        if val < 20 or val > 60:
            await message.answer("❌ Hors limites. Choisis une valeur entre 20 et 60.")
            return
        rate = round(val / 100.0, 4)
        if not settings:
            settings = ReferralSettings(referrer_id=ref_id, override_rate=rate)
            db.add(settings)
        else:
            settings.override_rate = rate
        db.commit()
        await message.answer(f"✅ Override défini à <b>{val:.0f}%</b>", parse_mode=ParseMode.HTML)
    finally:
        db.close()
    await state.clear()

@router.callback_query(F.data.startswith("admin_togglenotif_"))
async def callback_admin_togglenotif(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User introuvable", show_alert=True)
            return
        u.notifications_enabled = not u.notifications_enabled
        db.commit()
        msg = "🔕 Notifications désactivées" if not u.notifications_enabled else "🔔 Notifications activées"
    finally:
        db.close()
    await callback.message.answer(msg)


@router.callback_query(F.data.startswith("admin_freeaccess_"))
async def callback_admin_freeaccess_menu(callback: types.CallbackQuery):
    """Show Free Access menu with duration options"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    await callback.answer()
    
    user_id = int(callback.data.split("_")[-1])
    
    text = (
        "🎁 <b>FREE ACCESS MENU</b>\n\n"
        "Choose duration for FREE premium access:\n"
        "(Not counted in revenue)"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="📅 1 Week", callback_data=f"admin_free_7_{user_id}")],
        [InlineKeyboardButton(text="📅 1 Month", callback_data=f"admin_free_30_{user_id}")],
        [InlineKeyboardButton(text="♾️ Lifetime", callback_data=f"admin_free_lifetime_{user_id}")],
        [InlineKeyboardButton(text="✏️ Custom Days", callback_data=f"admin_free_custom_{user_id}")],
        [InlineKeyboardButton(text="◀️ Back", callback_data=f"admin_user_{user_id}")],
    ]
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("admin_free_"))
async def callback_admin_grant_free(callback: types.CallbackQuery, state: FSMContext):
    """Grant free access with specified duration"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Accès refusé", show_alert=True)
        return
    
    parts = callback.data.split("_")
    duration_type = parts[2]  # 7, 30, lifetime, or custom
    user_id = int(parts[3])
    
    if duration_type == "custom":
        # Ask for custom days
        await callback.answer()
        await state.set_state("admin_free_custom_days")
        await state.update_data(target_user_id=user_id)
        await callback.message.answer(
            "✏️ Enter number of days for free access:\n"
            "(Send a number, e.g., 60)"
        )
        return
    
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == user_id).first()
        if not u:
            await callback.answer("User not found", show_alert=True)
            return
        
        # Set free access flag
        u.free_access = True
        u.tier = TierLevel.PREMIUM
        u.subscription_start = datetime.now()
        
        if duration_type == "lifetime":
            u.subscription_end = None
            duration_text = "LIFETIME"
        else:
            days = int(duration_type)
            u.subscription_end = datetime.now() + timedelta(days=days)
            duration_text = f"{days} days"
        
        # Enable premium features
        u.enable_good_odds = True
        u.enable_middle = True
        
        db.commit()
        
        await callback.answer(f"✅ Free access granted: {duration_text}", show_alert=True)
        await callback.message.answer(
            f"🎁 <b>FREE ACCESS GRANTED</b>\n\n"
            f"User: {user_id}\n"
            f"Duration: {duration_text}\n"
            f"Status: Premium (FREE)\n\n"
            f"✅ Not counted in revenue",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Error granting free access: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.message(F.text.regexp(r'^\d+$'), StateFilter("admin_free_custom_days"))
async def process_free_custom_days(message: types.Message, state: FSMContext):
    """Process custom days input for free access"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Access denied")
        return
    
    try:
        days = int(message.text)
        if days <= 0 or days > 3650:  # Max 10 years
            await message.answer("❌ Invalid number. Use 1-3650 days")
            return
        
        data = await state.get_data()
        user_id = data.get('target_user_id')
        
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.telegram_id == user_id).first()
            if not u:
                await message.answer("❌ User not found")
                return
            
            # Grant free access
            u.free_access = True
            u.tier = TierLevel.PREMIUM
            u.subscription_start = datetime.now()
            u.subscription_end = datetime.now() + timedelta(days=days)
            u.enable_good_odds = True
            u.enable_middle = True
            
            db.commit()
            
            await message.answer(
                f"🎁 <b>FREE ACCESS GRANTED</b>\n\n"
                f"User: {user_id}\n"
                f"Duration: {days} days\n"
                f"Expires: {u.subscription_end.strftime('%Y-%m-%d')}\n\n"
                f"✅ Not counted in revenue",
                parse_mode=ParseMode.HTML
            )
            
        finally:
            db.close()
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Invalid number")
