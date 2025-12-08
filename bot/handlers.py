"""
User command handlers for Telegram bot
Handles: /start, /help, /subscribe, /mystats, /referral, /settings
"""
import logging
from aiogram import Bot, F, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
import os
from datetime import datetime, date, timedelta
from sqlalchemy import func, case, text, and_

logger = logging.getLogger(__name__)

from database import SessionLocal
from models.user import User, TierLevel
from models.bet import UserBet, DailyStats
from core.tiers import TierManager, TierLevel as CoreTierLevel
from core.referrals import ReferralManager
from core.calculator import ArbitrageCalculator
from core.casinos import CASINOS, get_casino_referral_link, get_casino_logo
from core.languages import Translations
from config import ADMIN_CHAT_ID
from utils.drops_stats import get_today_stats_for_tier
from bot.commands_setup import set_user_commands
from bot.message_manager import BotMessageManager
from bot.nowpayments_handler import NOWPaymentsManager
from models.referral import ReferralSettings

router = Router()


# FSM States
class UserStates(StatesGroup):
    awaiting_bankroll = State()
    awaiting_risk_percentage = State()


class OnboardingStates(StatesGroup):
    awaiting_referral = State()
    awaiting_terms_acceptance = State()

class LastArbCashh(StatesGroup):
    awaiting_amount = State()


async def _show_subscribe_tiers(message: types.Message):
    """Helper to show subscribe/tiers menu from deep link"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.answer("Please send /start first!")
            return
        lang = user.language or "en"
        
        if lang == "fr":
            text = (
                "💎 <b>PLANS DISPONIBLES</b>\n\n"
                "🆓 <b>GRATUIT</b>\n"
                "• 5 alertes par jour\n"
                "• Arbitrages < 2.5%\n\n"
                "🔥 <b>ALPHA - 200 CAD/mois</b>\n"
                "• Alertes illimitées\n"
                "• Tous les arbitrages\n"
                "• Middle Bets + Good Odds\n"
                "• Dashboard Web\n"
                "• Support VIP\n\n"
                "💰 Paiement crypto uniquement"
            )
            btn_text = "🔥 Acheter ALPHA"
        else:
            text = (
                "💎 <b>AVAILABLE PLANS</b>\n\n"
                "🆓 <b>FREE</b>\n"
                "• 5 alerts per day\n"
                "• Arbitrages < 2.5%\n\n"
                "🔥 <b>ALPHA - 200 CAD/month</b>\n"
                "• Unlimited alerts\n"
                "• All arbitrages\n"
                "• Middle Bets + Good Odds\n"
                "• Web Dashboard\n"
                "• VIP Support\n\n"
                "💰 Crypto payment only"
            )
            btn_text = "🔥 Buy ALPHA"
        
        keyboard = [
            [InlineKeyboardButton(text=btn_text, callback_data="buy_alpha")],
            [InlineKeyboardButton(text=("◀️ Menu" if lang == 'fr' else "◀️ Menu"), callback_data="main_menu")],
        ]
        await BotMessageManager.send_or_edit(
            event=message,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """
    /start command - Registration + Referral handling
    """
    # Delete the command message
    try:
        await message.delete()
    except Exception:
        pass
    
    # Handle deep link payloads (e.g., /start subscribe)
    logger.info(f"[START] message.text = '{message.text}'")
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1].strip().lower()
        logger.info(f"[START] payload detected = '{payload}'")
        if payload == 'subscribe':
            # Forward to subscribe_command (defined later in this file)
            # We need to create user first if they don't exist, then call subscribe
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
                if not user:
                    # Create user first
                    user = User(
                        telegram_id=message.from_user.id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        last_name=message.from_user.last_name,
                        language="en",
                        tier=TierLevel.FREE,
                        is_active=True
                    )
                    db.add(user)
                    db.commit()
            finally:
                db.close()
            # Now call subscribe_command (will be handled after function definition)
            # Use message.answer to show tiers directly
            await _show_subscribe_tiers(message)
            return
        elif payload == 'getstarted':
            # Just show normal menu (fall through)
            pass
    
    # Confirmation system disabled on Telegram (web only)
    pending_count = 0
    has_pending = False
    
    user_tg = message.from_user
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        is_new = False
        if not user:
            # New user - create account (default EN, FREE)
            user = User(
                telegram_id=user_tg.id,
                username=user_tg.username,
                first_name=user_tg.first_name,
                last_name=user_tg.last_name,
                language="en",
                tier=TierLevel.FREE,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new = True
            
            # Create bonus tracking ONLY for FREE users (eligible for 2 days)
            # PREMIUM/LIFETIME users should NOT get bonus
            if user.tier == TierLevel.FREE:
                try:
                    db.execute(text("""
                        INSERT INTO bonus_tracking 
                        (telegram_id, started_at, bonus_eligible, ever_had_bonus)
                        VALUES (:tid, :now, 1, 0)
                    """), {
                        'tid': user_tg.id,
                        'now': datetime.now()
                    })
                    db.commit()
                except Exception as e:
                    logger.error(f"Error creating bonus_tracking for {user_tg.id}: {e}")
            
            # If started with referral payload, apply it now (after user exists)
            if message.text and len(message.text.split()) > 1:
                referral_code = (message.text.split()[1] or "").strip()
                if referral_code:
                    try:
                        applied = ReferralManager.apply_referral(db, user_tg.id, referral_code)
                    except Exception:
                        applied = False
                    if applied:
                        # Notify referrer that their link was used
                        try:
                            referrer = db.query(User).filter(User.referral_code == referral_code).first()
                            if referrer:
                                ref_lang = (getattr(referrer, 'language', None) or 'en')
                                uname = message.from_user.username
                                mention = (f"@{uname}" if uname else f"<code>{message.from_user.id}</code>")
                                if ref_lang == 'fr':
                                    ref_text = (
                                        "🎁 <b>NOUVEAU REFERRAL</b>\n\n"
                                        f"{mention} vient d'utiliser votre lien de parrainage et a rejoint le bot.\n\n"
                                        "Vous gagnerez 20% quand il/elle passe PREMIUM.\n\n"
                                        "📊 /mystats"
                                    )
                                else:
                                    ref_text = (
                                        "🎁 <b>NEW REFERRAL</b>\n\n"
                                        f"{mention} just used your referral link and joined the bot.\n\n"
                                        "You’ll earn 20% when they go PREMIUM.\n\n"
                                        "📊 /mystats"
                                    )
                                await message.bot.send_message(referrer.telegram_id, ref_text, parse_mode=ParseMode.HTML)
                        except Exception:
                            pass
            # Ensure user has a referral code of their own
            try:
                ReferralManager.create_user_referral_code(db, user_tg.id)
            except Exception:
                pass
        else:
            # Existing user - update last seen
            user.last_seen = datetime.now()
            db.commit()
        
        # Onboarding flow for brand new users
        if is_new:
            # If no referral payload was used, ask if they have a code
            had_payload = bool(message.text and len(message.text.split()) > 1)
            if not had_payload and not user.referred_by:
                kb = [
                    [InlineKeyboardButton(text=("🎁 J'ai un code" if True else "🎁 I have a code"), callback_data="onboard_have_ref")],
                    [InlineKeyboardButton(text=("⏭️ Passer" if True else "⏭️ Skip"), callback_data="onboard_skip_ref")],
                ]
                prompt = "As-tu un code de parrainage? / Do you have a referral code?"
                await BotMessageManager.send_or_edit(
                    event=message,
                    text=prompt,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                    parse_mode=ParseMode.HTML,
                )
                return
            else:
                # Go straight to language choice
                lang_prompt = "Choose your language / Choisis ta langue"
                lang_kb = [
                    [InlineKeyboardButton(text="🇬🇧 English", callback_data="onboard_lang_en")],
                    [InlineKeyboardButton(text="🇫🇷 Français", callback_data="onboard_lang_fr")],
                ]
                await BotMessageManager.send_or_edit(
                    event=message,
                    text=lang_prompt,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=lang_kb),
                    parse_mode=ParseMode.HTML,
                )
                return

        # Unified main menu with stats
        lang = user.language or "en"
        title = "Bienvenue" if lang == "fr" else "Welcome"
        desc = (
            "Risk0 Casino - Profite de bets garantis!"
            if lang == "fr" else
            "Risk0 Casino - Enjoy guaranteed bets!"
        )
        profit_label = "Profit total" if lang == "fr" else "Total Profit"
        bets_label = "Bets placés" if lang == "fr" else "Bets placed"
        help_line = "Tape /help pour voir toutes les commandes!" if lang == "fr" else "Type /help to see all commands!"
        # Tier label (ALPHA for admin, LIFETIME for premium with no expiry)
        if user.is_admin:
            tier_label = "ALPHA"
        elif user.tier == TierLevel.PREMIUM and not user.subscription_end:
            tier_label = "KING"  # Lifetime = KING
        else:
            # FREE users = BETA, PREMIUM = ALPHA
            tier_label = "BETA" if user.tier == TierLevel.FREE else "ALPHA"
        # Access line for PREMIUM users
        days_left_line = ""
        if user.tier == TierLevel.PREMIUM and not user.subscription_end:
            # Admin créateur = KING OF ALPHA (pas "KING ALPHA")
            if user.telegram_id == 8213628656:
                days_left_line = (f"👑 Accès: <b>KING OF ALPHA</b>\n" if lang == 'fr' else f"👑 Access: <b>KING OF ALPHA</b>\n")
            # Lifetime = KING
            else:
                days_left_line = (f"👑 Accès: <b>KING</b>\n" if lang == 'fr' else f"👑 Access: <b>KING</b>\n")
        elif user.tier == TierLevel.PREMIUM and user.subscription_end:
            # Temporary premium with expiry date
            days_left = user.days_until_expiry
            days_left_line = (f"⏰ Expire dans: {days_left} jours\n" if lang == 'fr' else f"⏰ Expires in: {days_left} days\n")
        # Calls today + Potential %
        def _core_tier_from_model(t):
            try:
                name = t.name.lower()
            except Exception:
                return CoreTierLevel.FREE
            return CoreTierLevel.PREMIUM if name == 'premium' else CoreTierLevel.FREE
        calls_count, potential_pct = get_today_stats_for_tier(_core_tier_from_model(user.tier))
        calls_label = ("Appels aujourd'hui" if lang == 'fr' else "Calls today")
        potential_label = ("Potentiel" if lang == 'fr' else "Potential")

        # Hide Tier line in main menu for PREMIUM users
        tier_line = "" if user.tier == TierLevel.PREMIUM else f"🏆 <b>Tier: {tier_label}</b>\n"
        # FREE daily quota line (shown only to FREE users)
        quota_line = ""
        if user.tier == TierLevel.FREE:
            today_used = user.alerts_today if user.last_alert_date == date.today() else 0
            max_alerts = TierManager.get_features(_core_tier_from_model(user.tier)).get("max_alerts_per_day", 2)
            quota_line = (f"📣 {today_used}/{max_alerts} today\n" if lang != 'fr' else f"📣 {today_used}/{max_alerts} aujourd'hui\n")
        
        # Calculate real-time stats from UserBet
        total_bets_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0
        
        total_profit_calc = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0.0
        
        # Calculate total stake for ROI
        total_stake_calc = db.query(
            func.sum(UserBet.total_stake)
        ).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0.0
        
        # Calculate ROI
        roi = (total_profit_calc / total_stake_calc * 100) if total_stake_calc > 0 else 0.0
        
        # Calculate current win streak
        recent_bets = db.query(UserBet).filter(
            UserBet.user_id == user_tg.id
        ).order_by(UserBet.created_at.desc()).limit(10).all()
        
        win_streak = 0
        for bet in recent_bets:
            # Check if bet is a win (actual_profit if confirmed, else expected_profit for pending)
            profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
            if profit > 0:
                win_streak += 1
            else:
                break  # Stop at first loss
        
        # Determine performance badge
        badge = ""
        if roi > 30 or win_streak >= 5:
            badge = " 🔥 HOT STREAK"
        elif total_bets_count >= 10 and roi > 20:
            badge = " 💎 DIAMOND HANDS"
        elif total_profit_calc > 5000:
            badge = " 🚀 ROCKET"
        elif user.tier == TierLevel.PREMIUM and total_bets_count >= 50:
            badge = " 👑 KING"
        
        # For FREE users, show how many calls ALPHA gets (to drive upgrade)
        if user.tier == TierLevel.FREE:
            # Get ALPHA stats to show what they're missing (returns tuple: count, total_pct)
            alpha_calls, alpha_potential = get_today_stats_for_tier(CoreTierLevel.PREMIUM)
            # Get user's actual usage today
            today_used = user.alerts_today if user.last_alert_date == date.today() else 0
            
            # Check if user has active bonus
            bonus_result = db.execute(text("""
                SELECT bonus_activated_at, bonus_expires_at, bonus_redeemed
                FROM bonus_tracking
                WHERE telegram_id = :tid
                    AND bonus_activated_at IS NOT NULL
                    AND bonus_redeemed = 0
                    AND bonus_expires_at > :now
            """), {'tid': user_tg.id, 'now': datetime.now()}).first()
            
            bonus_line = ""
            if bonus_result:
                # Parse datetime from SQLite if string
                expires_at = bonus_result.bonus_expires_at
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                
                time_left = expires_at - datetime.now()
                total_hours = int(time_left.total_seconds() // 3600)
                days_left = total_hours // 24
                hours_left = total_hours % 24
                
                # Format time display
                if days_left > 0:
                    time_display = f"{days_left} jour{'s' if days_left > 1 else ''} {hours_left}h" if lang == 'fr' else f"{days_left} day{'s' if days_left > 1 else ''} {hours_left}h"
                else:
                    time_display = f"{hours_left}h"
                
                if lang == 'fr':
                    bonus_line = f"🎁 <b>Rabais $50 expire dans {time_display}!</b>\n"
                else:
                    bonus_line = f"🎁 <b>$50 discount expires in {time_display}!</b>\n"
            
            # Generate daily motivational example (changes every 24h based on date)
            import hashlib
            today_str = date.today().isoformat()
            seed = int(hashlib.md5(today_str.encode()).hexdigest()[:8], 16)
            
            # Randomize but keep realistic
            num_bets = (seed % 4) + 3  # 3-6 bets
            ev_pct = ((seed >> 8) % 6) + 5  # 5-10%
            bankroll = ((seed >> 16) % 40 + 10) * 100  # $1000-$5000
            profit = round(bankroll * (num_bets * ev_pct / 100), 2)
            
            if lang == 'fr':
                stats_line = f"💎 Alpha aujourd'hui: <b>{alpha_calls} calls</b>  •  📈 <b>{alpha_potential:.1f}% potential</b>\n"
                stats_line += f"🆓 Toi (BETA): <b>{today_used}/5 calls aujourd'hui</b>\n"
                stats_line += bonus_line
                stats_line += f"\n💡 <i>Exemple: {num_bets} bets à {ev_pct}% EV avec ${bankroll} = <b>+${profit}</b> profit! ASSURÉ</i>\n\n"
            else:
                stats_line = f"💎 Alpha today: <b>{alpha_calls} calls</b>  •  📈 <b>{alpha_potential:.1f}% potential</b>\n"
                stats_line += f"🆓 You (BETA): <b>{today_used}/5 calls today</b>\n"
                stats_line += bonus_line
                stats_line += f"\n💡 <i>Example: {num_bets} bets at {ev_pct}% EV with ${bankroll} = <b>+${profit}</b> profit! GUARANTEED</i>\n\n"
        else:
            # PREMIUM: show their stats
            if lang == 'fr':
                stats_line = f"📣 {calls_label}: <b>{calls_count}</b>\n📈 {potential_label}: <b>{potential_pct}%</b>\n\n"
            else:
                stats_line = f"📣 {calls_label}: <b>{calls_count}</b>\n📈 {potential_label}: <b>{potential_pct}%</b>\n\n"
        
        # If user has pending confirmations, show special confirmation menu
        if has_pending:
            # Get ALL pending bets (no date filtering)
            pending_bets = db.query(UserBet).filter(
                and_(
                    UserBet.user_id == user_tg.id,
                    UserBet.status == 'pending'
                )
            ).all()
            
            # Filter to only ready bets
            today = date.today()
            ready_bets = []
            for bet in pending_bets:
                if bet.match_date and bet.match_date < today:
                    ready_bets.append(bet)
                elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                    ready_bets.append(bet)
            
            # Build confirmation message
            if lang == 'fr':
                menu_text = f"📋 <b>CONFIRMATIONS EN ATTENTE</b>\n\n⚠️ <b>{len(ready_bets)} confirmation(s) nécessaire(s):</b>\n"
            else:
                menu_text = f"📋 <b>PENDING CONFIRMATIONS</b>\n\n⚠️ <b>{len(ready_bets)} confirmation(s) needed:</b>\n"
            
            # Show first 5 bets
            for bet in ready_bets[:5]:
                bet_emoji = "🎲" if bet.bet_type == 'middle' else "✅" if bet.bet_type == 'arbitrage' else "📈"
                match = bet.match_name or "Match"
                menu_text += f"• {bet_emoji} {match} (${bet.total_stake:.0f})\n"
            
            if len(ready_bets) > 5:
                menu_text += f"  ... {'et' if lang == 'fr' else 'and'} {len(ready_bets) - 5} {'autre(s)' if lang == 'fr' else 'more'}\n"
            
            menu_text += f"\n💡 {'Clique sur le bouton pour recevoir tous les questionnaires!' if lang == 'fr' else 'Click the button to receive all questionnaires!'}"
            
            # Only ONE button: send questionnaires
            btn_text = f"📨 {'Envoyer tous les questionnaires' if lang == 'fr' else 'Send all questionnaires'}"
            keyboard = [
                [InlineKeyboardButton(text=btn_text, callback_data="resend_all_questionnaires")]
            ]
        else:
            # Normal menu
            menu_text = (
                f"🎰 <b>{title} {user_tg.first_name}!{badge}</b>\n\n"
                f"💰 {desc}\n\n"
                f"{tier_line}"
                f"{quota_line}{days_left_line}"
                f"💵 <b>{profit_label}: ${total_profit_calc:.2f}</b>\n"
                f"📊 <b>{bets_label}: {total_bets_count}</b>\n"
                f"{stats_line}"
                f"{help_line}"
            )
            # Check bet_focus_mode
            bet_focus = getattr(user, 'bet_focus_mode', False)
            
            # Generate auth token for dashboard
            import base64, json, time as time_module
            dash_token = base64.b64encode(json.dumps({"telegramId": user.telegram_id, "username": user_tg.username or user_tg.first_name or str(user.telegram_id), "tier": user.tier.value if hasattr(user.tier, 'value') else str(user.tier), "ts": int(time_module.time())}, separators=(',', ':')).encode()).decode()
            dash_url = f"https://smartrisk0.xyz/dash?token={dash_token}"
            
            # Build menu keyboard
            keyboard = await build_menu_keyboard(user, lang, dash_url, bet_focus)
            # Admin panel button (env or DB admin)
            try:
                env_admins = [int(x.strip()) for x in (os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []) if x.strip()]
            except Exception:
                env_admins = []
            is_env_admin = False
            try:
                is_env_admin = (user_tg.id in env_admins) or (ADMIN_CHAT_ID and user_tg.id == int(ADMIN_CHAT_ID))
            except Exception:
                is_env_admin = False
            if user.is_admin or is_env_admin:
                admin_label = "🛠️ Admin" if lang == "fr" else "🛠️ Admin"
                keyboard.append([InlineKeyboardButton(text=admin_label, callback_data="open_admin")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Ensure per-chat commands reflect language (default EN)
        try:
            await set_user_commands(message.bot, message.chat.id, lang)
        except Exception:
            pass
        # Use message manager to delete user command and previous menu, and send new
        await BotMessageManager.send_or_edit(
            event=message,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    
    finally:
        db.close()


@router.message(Command("support"))
async def support_command(message: types.Message):
    """/support - Contact support info"""
    try:
        await message.delete()
    except Exception:
        pass
    text = (
        "🆘 <b>SUPPORT</b>\n\n"
        "📖 New? Read the guide: /guide (10-15 min)\n\n"
        "👤 Contact: @Z3RORISK\n"
        "🕒 Response: <b>Fast (Same day)</b>\n\n"
        "Include: your issue and screenshots if possible."
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def help_command(message: types.Message):
    """/help - Show main commands and how it works"""
    try:
        await message.delete()
    except Exception:
        pass
    text = (
        "🆕 New? Read the complete guide: /guide — ⏱️ 10-15 minutes = avoid $500+ mistakes\n\n"
        "🎯 <b>Main commands</b>\n"
        "/start — Start the bot\n"
        "/menu — Open the menu\n"
        "/guide — Complete guide (recommended)\n"
        "/mystats — Your stats & performance\n"
        "/subscribe — Upgrade plans\n"
        "/referral — Your referral link & earnings\n"
        "/settings — Settings (CASHH, filters, notifications)\n"
        "/support — Contact support\n"
        "/help — This help\n\n"
        "💰 <b>How it works</b>\n"
        "1️⃣ You receive arbitrage/+EV alerts in real-time\n"
        "2️⃣ Bot calculates optimal stakes automatically\n"
        "3️⃣ You place bets on the bookmakers\n"
        "4️⃣ Click I BET to track profit & ROI\n"
        "5️⃣ Profit guaranteed (arbitrage) or +EV long term\n\n"
        "🎖️ <b>Plans</b>\n"
        "🆓 FREE — 5 calls/day, max 2.5% arbs only\n"
        "💎 ALPHA — $200 CAD/month\n"
        "   • Unlimited arbitrage calls\n"
        "   • Good Odds (+EV) & Middle Bets\n"
        "   • Advanced calculator & filters\n"
        "   • Pro stats dashboard\n"
        "   • Last Call feature (24h)\n"
        "   • VIP support\n\n"
        "🎁 <b>Referral</b> — Alpha members earn 20% recurring (up to 40% with bonuses) • /referral\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "onboard_have_ref")
async def callback_onboard_have_ref(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(OnboardingStates.awaiting_referral)
    await callback.message.edit_text(
        "Envoie ton code ici / Send your referral code here\n\nOu clique 'Skip' si tu n'en as pas.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭️ Skip", callback_data="onboard_skip_ref")]])
    )


@router.callback_query(F.data == "onboard_skip_ref")
async def callback_onboard_skip_ref(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    lang_prompt = "Choose your language / Choisis ta langue"
    lang_kb = [
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="onboard_lang_en")],
        [InlineKeyboardButton(text="🇫🇷 Français", callback_data="onboard_lang_fr")],
    ]
    await callback.message.edit_text(
        lang_prompt,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=lang_kb)
    )


@router.message(OnboardingStates.awaiting_referral)
async def process_onboarding_referral(message: types.Message, state: FSMContext):
    code = (message.text or "").strip()
    db = SessionLocal()
    try:
        ok = False
        try:
            ok = ReferralManager.apply_referral(db, message.from_user.id, code)
        except Exception:
            ok = False
        if ok:
            await message.answer("✅ Code appliqué / Code applied")
            # Notify referrer that their code was used
            try:
                referrer = db.query(User).filter(User.referral_code == code).first()
                if referrer:
                    ref_lang = (getattr(referrer, 'language', None) or 'en')
                    uname = message.from_user.username
                    mention = (f"@{uname}" if uname else f"<code>{message.from_user.id}</code>")
                    if ref_lang == 'fr':
                        ref_text = (
                            "🎁 <b>NOUVEAU REFERRAL</b>\n\n"
                            f"{mention} vient d'utiliser votre lien de parrainage et a rejoint le bot.\n\n"
                            "Vous gagnerez 10-40% quand il/elle passe PREMIUM.\n\n"
                            "10% base → 12.5% Alpha → 15% (5 clients) → 25% (10) → 30% (20) → 40% (30+)\n\n"
                            "📊 /mystats"
                        )
                    else:
                        ref_text = (
                            "🎁 <b>NEW REFERRAL</b>\n\n"
                            f"{mention} just used your referral link and joined the bot.\n\n"
                            "You'll earn 10-40% when they go PREMIUM.\n\n"
                            "10% base → 12.5% Alpha → 15% (5 clients) → 25% (10) → 30% (20) → 40% (30+)\n\n"
                            "📊 /mystats"
                        )
                    await message.bot.send_message(referrer.telegram_id, ref_text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await message.answer("❌ Code invalide / Invalid code")
    finally:
        db.close()
    await state.clear()
    # Ask language next
    lang_prompt = "Choose your language / Choisis ta langue"
    lang_kb = [
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="onboard_lang_en")],
        [InlineKeyboardButton(text="🇫🇷 Français", callback_data="onboard_lang_fr")],
    ]
    await message.answer(
        lang_prompt,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=lang_kb)
    )


@router.callback_query(F.data.in_({"onboard_lang_en", "onboard_lang_fr"}))
async def callback_onboard_lang(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    db = SessionLocal()
    lang = "en" if callback.data.endswith("_en") else "fr"
    
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            return
        user.language = lang
        db.commit()
    finally:
        db.close()
    
    try:
        await set_user_commands(callback.bot, callback.message.chat.id, lang)
    except Exception:
        pass
    
    # Show dashboard announcement first
    dash_text = (
        "🚀 <b>RISK0 DASHBOARD IS ALIVE!</b> 🎉\n\n"
        "All your tools in one place:\n"
        "• Live Arbitrage Alerts\n"
        "• Bet Tracking & Stats\n"
        "• Portfolio Analytics\n"
        "• Pro Calculator\n"
        "• Bankroll Management\n\n"
        "🌐 Access now: https://smartrisk0.xyz\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
    )
    await callback.message.answer(dash_text, parse_mode=ParseMode.HTML)

    # Show legal terms and conditions
    await state.set_state(OnboardingStates.awaiting_terms_acceptance)
    
    if lang == "fr":
        terms_text = (
            "⚠️ <b>AVANT DE COMMENCER - LIS CECI</b> ⚠️\n\n"
            "🔥 <b>BIENVENUE À RISK0</b> 🔥\n\n"
            "Le groupe #1 de paris sportifs profitables.\n\n"
            "💰 <b>CE QUE TU OBTIENS:</b>\n"
            "• Arbitrages (profit garanti 0 risque)\n"
            "• Middle bets (risque faible, reward élevé)\n"
            "• Opportunités +EV\n"
            "• Éducation complète & stratégies\n"
            "• Support 24/7\n\n"
            "💵 <b>Prix:</b> $200/mois (crypto seulement)\n\n"
            "⚠️ <b>REQUIS:</b>\n"
            "• Minimum $200 bankroll\n"
            "• 18+ ans seulement\n"
            "• Comptes multiples de bookmakers\n\n"
            "📜 <b>LIS CES DOCUMENTS D'ABORD:</b>\n\n"
            "📋 Terms of Service\n"
            "https://telegra.ph/RISK0---TERMS--CONDITIONS-11-27\n\n"
            "🔒 Privacy Policy\n"
            "https://telegra.ph/RISK0---PRIVACY-POLICY-11-27\n\n"
            "⚠️ Risk Disclosure\n"
            "https://telegra.ph/RISK0---RISK-DISCLOSURE-11-27\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ $200/mois en CRYPTO SEULEMENT\n\n"
            "3️⃣ Tu as besoin d'un MINIMUM de $200 de bankroll pour profiter\n\n"
            "4️⃣ Tu PEUX faire de l'argent si tu suis nos méthodes\n\n"
            "5️⃣ Tu POURRAIS être limité par les bookmakers (on t'enseigne comment éviter)\n\n"
            "6️⃣ On fournit l'info - TOI tu exécutes\n\n"
            "7️⃣ Tous les paris ont un risque (mais notre méthode 0-risque le minimise)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📖 <b>IMPORTANT:</b> Lis le guide complet après avoir accepté pour comprendre comment tout fonctionne.\n\n"
            "✅ <b>En continuant, tu acceptes tous les termes ci-dessus.</b>\n\n"
            "Let's make money. 🚀"
        )
        accept_button = "✅ J'ACCEPTE"
    else:
        terms_text = (
            "⚠️ <b>BEFORE YOU START - READ THIS</b> ⚠️\n\n"
            "🔥 <b>WELCOME TO RISK0</b> 🔥\n\n"
            "The #1 sports betting profit group.\n\n"
            "💰 <b>WHAT YOU GET:</b>\n"
            "• Arbitrage plays (0-risk guaranteed profit)\n"
            "• Middle bets (low risk, high reward)\n"
            "• +EV opportunities\n"
            "• Full education & strategies\n"
            "• 24/7 support\n\n"
            "💵 <b>Price:</b> $200/month (crypto only)\n\n"
            "⚠️ <b>REQUIREMENTS:</b>\n"
            "• Minimum $200 bankroll\n"
            "• 18+ only\n"
            "• Multiple bookmaker accounts\n\n"
            "📜 <b>READ THESE FIRST:</b>\n\n"
            "📋 Terms of Service\n"
            "https://telegra.ph/RISK0---TERMS--CONDITIONS-11-27\n\n"
            "🔒 Privacy Policy\n"
            "https://telegra.ph/RISK0---PRIVACY-POLICY-11-27\n\n"
            "⚠️ Risk Disclosure\n"
            "https://telegra.ph/RISK0---RISK-DISCLOSURE-11-27\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ This is $200/month in CRYPTO ONLY\n\n"
            "3️⃣ You need MINIMUM $200 bankroll to profit\n\n"
            "4️⃣ You can make money if you follow our methods\n\n"
            "5️⃣ You might get limited by bookmakers (we teach you how to avoid)\n\n"
            "6️⃣ We provide info - YOU execute\n\n"
            "7️⃣ All betting has risk (but our 0-risk method minimizes it)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📖 IMPORTANT: Read the full guide after accepting to understand how everything works.\n\n"
            "✅ By continuing, you agree to all terms above.\n\n"
            "Let's make money. 🚀"
        )
        accept_button = "✅ I ACCEPT"
    
    kb = [[InlineKeyboardButton(text=accept_button, callback_data="accept_terms")]]
    
    await callback.message.edit_text(
        terms_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "accept_terms")
async def callback_accept_terms(callback: types.CallbackQuery, state: FSMContext):
    """User accepted terms - go to main menu"""
    await callback.answer()
    await state.clear()

    # Show dashboard announcement
    dash_text = (
        "🚀 <b>RISK0 DASHBOARD IS ALIVE!</b> 🎉\n\n"
        "All your tools in one place:\n"
        "• Live Arbitrage Alerts\n"
        "• Bet Tracking & Stats\n"
        "• Portfolio Analytics\n"
        "• Pro Calculator\n"
        "• Bankroll Management\n\n"
        "🌐 Access now: https://smartrisk0.xyz\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
    )
    await callback.message.answer(dash_text, parse_mode=ParseMode.HTML)

    # Get user language
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = user.language if user else "en"
    finally:
        db.close()

    # Show welcome message
    if lang == "fr":
        welcome_text = (
            "👋 <b>BIENVENUE SUR RISK0!</b>\n\n"
            "💰 Prêt à commencer à faire des profits garantis?\n\n"
            "📊 Voici quoi faire:\n"
            "1. Lis le /guide d'abord\n"
            "2. Configure ta bankroll dans /settings\n"
            "3. Attends les alertes d'arbitrage\n"
            "4. Suis tes profits\n\n"
            "🔔 <b>Active les notifications pour ne rater aucun call!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        welcome_text = (
            "👋 <b>WELCOME TO RISK0!</b>\n\n"
            "💰 Ready to start making guaranteed profits?\n\n"
            "📊 Here's what to do:\n"
            "1. Read the /guide first\n"
            "2. Set up your bankroll in /settings\n"
            "3. Wait for arbitrage alerts\n"
            "4. Track your profits\n\n"
            "🔔 <b>Turn on notifications to never miss a call!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
        )
    await callback.message.answer(welcome_text, parse_mode=ParseMode.HTML)

    # Mark user as having accepted terms (optional: track in DB)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            # Optional: add terms_accepted timestamp to User model later
            pass
    finally:
        db.close()
    
    # Go to main menu
    await callback_main_menu(callback)


@router.message(Command("menu"))
async def menu_command(message: types.Message, state: FSMContext):
    """/menu - alias of /start showing the unified main menu"""
    await start_command(message, state)


@router.message(Command("help"))
async def help_command(message: types.Message):
    """
    /help command - Show all available commands (localized)
    """
    try:
        await message.delete()
    except Exception:
        pass
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        help_text = (
            "🆕 <b>Nouveau?</b> Lis le guide complet: <b>/guide</b> — ⏱️ 5-10 minutes = éviter $500+ d'erreurs\n\n"
            "<b>🎯 Commandes principales</b>\n"
            "/start — Démarrer le bot\n"
            "/menu — Ouvrir le menu\n"
            "/guide — Guide complet (recommandé)\n"
            "/mystats — Tes statistiques\n"
            "/subscribe — Voir les plans\n"
            "/referral — Ton lien de parrainage\n"
            "/settings — Paramètres (CASHH, risk)\n"
            "/support — Contacte le support\n"
            "/help — Cette aide\n\n"
            "<b>💰 Comment ça marche?</b>\n"
            "1️⃣ Tu reçois des alertes d'arbitrage\n"
            "2️⃣ Le bot calcule les stakes (mode SAFE par défaut)\n"
            "3️⃣ Tu places les 2 paris\n"
            "4️⃣ Tu cliques <b>I BET</b> pour tracker tes profits\n\n"
            "<b>🎖️ Plans</b>\n"
            "🆓 FREE — 5 alertes/jour, arbitrages &lt; 2.5%\n"
            "🔥 ALPHA — 200 CAD/mois: illimité, ≥0.5%, Middle, Good Odds, filtres, calculateur, stats, support VIP\n\n"
            "<b>🎁 Parrainage</b> — Gagne 20% récurrent • /referral\n\n"
            "❓ Besoin d'aide? /support ou contacte @ZEROR1SK"
        )
    else:
        help_text = (
            "🆕 <b>New?</b> Read the complete guide: <b>/guide</b> — ⏱️ 5-10 minutes = avoid $500+ mistakes\n\n"
            "<b>🎯 Main commands</b>\n"
            "/start — Start the bot\n"
            "/menu — Open the menu\n"
            "/guide — Complete guide (recommended)\n"
            "/mystats — Your stats\n"
            "/subscribe — Plans\n"
            "/referral — Your referral link\n"
            "/settings — Settings (CASHH, risk)\n"
            "/support — Contact support\n"
            "/help — This help\n\n"
            "<b>💰 How it works</b>\n"
            "1️⃣ You receive arbitrage alerts\n"
            "2️⃣ Bot computes stakes (SAFE by default)\n"
            "3️⃣ You place both bets\n"
            "4️⃣ Click <b>I BET</b> to track profits\n\n"
            "<b>🎖️ Plans</b>\n"
            "🆓 FREE — 5 alerts/day, arbitrages &lt; 2.5%\n"
            "🔥 ALPHA — 200 CAD/month: unlimited, ≥0.5%, Middle, Good Odds, filters, calculator, stats, VIP support\n\n"
            "<b>🎁 Referral</b> — Earn 20% recurring • /referral\n\n"
            "❓ Need help? /support or @ZEROR1SK"
        )

    # Send as a normal reply to avoid disappearing due to edit/delete flow
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@router.message(Command("support"))
async def support_command(message: types.Message):
    """/support - Contact/help info (bilingual)"""
    try:
        await message.delete()
    except Exception:
        pass
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        lang = (user.language if user else "en")
    finally:
        db.close()

    if lang == 'fr':
        text = (
            "🆘 <b>SUPPORT</b>\n\n"
            "📖 Nouveau? Lis le guide: <b>/guide</b> (10-15 min)\n\n"
            "👤 Contact: @ZEROR1SK\n"
            "🕒 Réponse: Rapide (Même jour)\n\n"
            "Indique: ton problème, screenshots si possible."
        )
    else:
        text = (
            "🆘 <b>SUPPORT</b>\n\n"
            "📖 New? Read the guide: <b>/guide</b> (10-15 min)\n\n"
            "👤 Contact: @ZEROR1SK\n"
            "🕒 Response: Fast (Same day)\n\n"
            "Include: your issue and screenshots if possible."
        )

    await BotMessageManager.send_or_edit(
        event=message,
        text=text,
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(F.data == "show_support")
async def callback_show_support(callback: types.CallbackQuery):
    """Show support page"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        if lang == 'fr':
            text = (
                "🆘 <b>SUPPORT</b>\n\n"
                "📖 Nouveau? Lis le guide: <b>/guide</b> (10-15 min)\n\n"
                "👤 Contact: @ZEROR1SK\n"
                "🕒 Réponse: Rapide (Même jour)\n\n"
                "Indique: ton problème, screenshots si possible."
            )
        else:
            text = (
                "🆘 <b>SUPPORT</b>\n\n"
                "📖 New? Read the guide: <b>/guide</b> (10-15 min)\n\n"
                "👤 Contact: @ZEROR1SK\n"
                "🕒 Response: Fast (Same day)\n\n"
                "Include: your issue and screenshots if possible."
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="◀️ Back to More" if lang == 'en' else "◀️ Retour à Plus",
                callback_data="settings_more"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.message(Command("subscribe"))
async def subscribe_command(message: types.Message):
    """
    /subscribe command - Show tier options (redirects to show_tiers)
    """
    try:
        await message.delete()
    except Exception:
        pass
    # Create a fake callback to reuse show_tiers logic
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.answer("Please send /start first!")
            return
        lang = user.language or "en"
        
        if lang == "fr":
            message_text = (
                "💎 <b>PLANS DISPONIBLES</b>\n\n"
                "🆓 <b>GRATUIT</b>\n"
                "• 5 alertes par jour\n"
                "• Arbitrages &lt; 2.5%\n"
                "• Alertes en temps réel\n\n"
                "🔥 <b>ALPHA - 200 CAD/mois</b>\n"
                "• Alertes illimitées\n"
                "• Tous les arbitrages (≥0.5%)\n"
                "• Middle Bets + Good Odds\n"
                "• Filtres avancés\n"
                "• Vérificateur de cotes auto\n"
                "• Mode RISKED\n"
                "• Calculateur personnalisé\n"
                "• Stats avancées\n"
                "• Support VIP\n"
                "• 20% referral à vie\n"
                "\n"
                "💰 <b>Paiement crypto uniquement</b>\n"
                "🎁 <b>Programme Referral:</b> Gagne 20% de commission récurrente!"
            )
        else:
            message_text = (
                "💎 <b>BETA vs ALPHA</b>\n\n"
                "🧪 <b>BETA (FREE)</b>\n"
                "• 5 alerts per day\n"
                "• Arbitrages &lt; 2.5%\n"
                "• Real-time alerts\n\n"
                "🔥 <b>ALPHA - 200 CAD/month</b>\n"
                "• Unlimited alerts\n"
                "• All arbitrages (≥0.5%)\n"
                "• Middle Bets + Good Odds\n"
                "• Advanced filters\n"
                "• Auto odds checker\n"
                "• RISKED mode\n"
                "• Custom calculator\n"
                "• Advanced stats\n"
                "• VIP support\n"
                "• 20% referral for life\n"
                "\n"
                "💰 <b>Crypto payment only</b>\n"
                "🎁 <b>Referral Program:</b> Earn 20% recurring commission!"
            )
        
        keyboard = [
            [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == "fr" else "🔥 Buy ALPHA"), callback_data="buy_premium")],
            [InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=message,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.message(Command("mystats"))
async def stats_command(message: types.Message):
    """
    /mystats command - Show user statistics
    """
    try:
        await message.delete()
    except Exception:
        pass
    user_tg = message.from_user
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        
        if not user:
            await message.answer("❌ User non trouvé. Tape /start d'abord!")
            return
        
        # User stats (détaillées)
        lang = user.language or "en"
        # Header
        stats_text = (
            f"📊 <b>{'TES STATISTIQUES' if lang == 'fr' else 'YOUR STATISTICS'}</b>\n"
            f"👤 {'User' if lang == 'en' else 'User'}: @{user.username or 'N/A'}\n"
            f"🎖️ Tier: <b>{user.tier.value.upper()}</b>\n"
        )
        if user.subscription_end and user.tier != TierLevel.FREE:
            days_left = user.days_until_expiry
            stats_text += (f"⏰ Expires in: {days_left} days\n" if lang == 'en' else f"⏰ Expire dans: {days_left} jours\n")
        stats_text += "\n"

        # Today / 7 days / All-time blocks
        today = date.today()
        week_ago = today - timedelta(days=7)
        # Today
        t = db.query(DailyStats.total_bets, DailyStats.total_staked, DailyStats.total_profit).filter(
            DailyStats.user_id == user.telegram_id,
            DailyStats.date == today
        ).first()
        t_bets = int((t.total_bets if t and t.total_bets is not None else 0)) if hasattr(t, 'total_bets') else int((t[0] or 0) if t else 0)
        t_staked = float((t.total_staked if t and t.total_staked is not None else 0.0)) if hasattr(t, 'total_staked') else float((t[1] or 0.0) if t else 0.0)
        t_profit = float((t.total_profit if t and t.total_profit is not None else 0.0)) if hasattr(t, 'total_profit') else float((t[2] or 0.0) if t else 0.0)
        t_roi = (t_profit / t_staked * 100.0) if t_staked > 0 else 0.0
        # 7 days
        w = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user.telegram_id,
            DailyStats.date >= week_ago
        ).first()
        w_bets = int(w[0] or 0)
        w_staked = float(w[1] or 0.0)
        w_profit = float(w[2] or 0.0)
        w_roi = (w_profit / w_staked * 100.0) if w_staked > 0 else 0.0
        # All-time (via DailyStats sums)
        a = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user.telegram_id
        ).first()
        a_bets = int(a[0] or 0)
        a_staked = float(a[1] or 0.0)
        a_profit = float(a[2] or 0.0)
        a_roi = (a_profit / a_staked * 100.0) if a_staked > 0 else 0.0
        # Compose blocks (localized)
        if lang == 'fr':
            stats_text += (
                "📅 Aujourd'hui\n"
                f"• Bets: {t_bets}\n"
                f"• Misé: ${t_staked:.2f}\n"
                f"• Profit: ${t_profit:.2f}\n"
                f"• ROI: {t_roi:.1f}%\n\n"
                "📆 7 jours\n"
                f"• Bets: {w_bets}\n"
                f"• Misé: ${w_staked:.2f}\n"
                f"• Profit: ${w_profit:.2f}\n"
                f"• ROI: {w_roi:.1f}%\n\n"
                "🏆 All-time\n\n"
                f"• Misé: ${a_staked:.2f}\n"
                f"•💰 Profit Net: ${(a_profit):.2f}\n"
                f"📈 Profit Total: ${user.total_profit:.2f}\n"
                f"📉 Perte Totale: ${user.total_loss:.2f}\n"
                f"📊 Bets: {max(a_bets, user.total_bets or 0)}\n"
                f"• ROI: {a_roi:.1f}%\n"
            )
        else:
            stats_text += (
                "📅 Today\n"
                f"• Bets: {t_bets}\n"
                f"• Staked: ${t_staked:.2f}\n"
                f"• Profit: ${t_profit:.2f}\n"
                f"• ROI: {t_roi:.1f}%\n\n"
                "📆 7 days\n"
                f"• Bets: {w_bets}\n"
                f"• Staked: ${w_staked:.2f}\n"
                f"• Profit: ${w_profit:.2f}\n"
                f"• ROI: {w_roi:.1f}%\n\n"
                "🏆 All-time\n\n"
                f"• Staked: ${a_staked:.2f}\n"
                f"•💰 Net Profit: ${(a_profit):.2f}\n"
                f"📈 Total Profit: ${user.total_profit:.2f}\n"
                f"📉 Total Loss: ${user.total_loss:.2f}\n"
                f"📊 Bets placed: {max(a_bets, user.total_bets or 0)}\n"
                f"• ROI: {a_roi:.1f}%\n"
            )
        
        # Referral stats (append if exists)
        referral_stats = ReferralManager.get_referral_stats(db, user.telegram_id)
        if referral_stats["total"]["count"] > 0:
            stats_text += ("\n" + ("🎁 <b>REFERRALS</b>\n" if lang != 'fr' else "🎁 <b>PARRAINAGE</b>\n"))
            stats_text += (
                (f"👥 Referrals: {referral_stats['total']['count']}\n"
                 f"💵 Earnings: ${referral_stats['total']['total_earned']:.2f}\n"
                 f"💰 Monthly recurring: ${referral_stats['total']['monthly_recurring']:.2f}\n") if lang != 'fr' else
                (f"👥 Personnes référées: {referral_stats['total']['count']}\n"
                 f"💵 Commissions gagnées: ${referral_stats['total']['total_earned']:.2f}\n"
                 f"💰 Mensuel récurrent: ${referral_stats['total']['monthly_recurring']:.2f}\n")
            )
        
        my_bets_text = ("📜 Mes Bets" if lang == 'fr' else "📜 My Bets")
        keyboard = [
            [InlineKeyboardButton(text=my_bets_text, callback_data="my_bets")],
            [InlineKeyboardButton(text=("🎁 Mon Lien Referral" if lang == 'fr' else "🎁 My Referral Link"), callback_data="show_referral")],
            [InlineKeyboardButton(text=("💎 Upgrade Tier" if lang != 'fr' else "💎 Upgrade Tier"), callback_data="show_tiers")],
            [InlineKeyboardButton(text=("◀️ Menu" if lang == 'fr' else "◀️ Menu"), callback_data="main_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=message,
            text=stats_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    
    finally:
        db.close()


@router.message(Command("referral"))
async def referral_command(message: types.Message):
    """
    /referral command - Show referral link and stats
    """
    try:
        await message.delete()
    except Exception:
        pass
    user_tg = message.from_user
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        
        if not user:
            await message.answer("❌ User non trouvé!")
            return
        
        # Get or create referral code
        referral_code = ReferralManager.create_user_referral_code(db, user_tg.id)
        
        # Resolve bot username dynamically
        bot_username = os.getenv("BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME")
        if not bot_username:
            try:
                me = await message.bot.get_me()
                bot_username = me.username
            except Exception:
                bot_username = "Risk0_bot"
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        # Get referral stats
        stats = ReferralManager.get_referral_stats(db, user_tg.id)
        # Dynamic commission info (respects admin override)
        active_directs = 0
        try:
            active_directs = ReferralManager.count_active_tier1(db, user_tg.id)
        except Exception:
            active_directs = 0
        try:
            current_rate = ReferralManager.get_dynamic_tier1_rate(db, user_tg.id)
        except Exception:
            current_rate = 0.20
        # Detect if admin override exists to display proper label
        try:
            _rs = db.query(ReferralSettings).filter(ReferralSettings.referrer_id == user_tg.id).first()
            is_override = bool(_rs and _rs.override_rate is not None)
        except Exception:
            is_override = False
        tiers_info = [
            (5, 0.15), (10, 0.25), (20, 0.30), (30, 0.40)
        ]
        next_tier_text = ""
        for thr, rate in tiers_info:
            if active_directs < thr:
                next_tier_text = f"➡️ Next: {thr} directs → {int(rate*100)}%"
                break
        if not next_tier_text:
            next_tier_text = "✅ Max rate reached"
        
        # Localized share text for Telegram share URL
        lang = user.language or "en"
        share_text = ("Rejoins Risk0 Casino!" if lang == "fr" else "Join Risk0 Casino!")
        if lang == 'fr':
            referral_text = (
                f"🎁 <b>TON PROGRAMME REFERRAL</b>\n\n"
                f"💰 <b>Taux actuel: {int(current_rate*100)}%</b> {'(override admin)' if is_override else '(dynamique)'}\n"
                f"👥 Directs actifs: {active_directs}\n"
                f"{next_tier_text}\n"
                f"🎟️ Alpha GRATUIT à 10 directs actifs\n\n"
                f"Ton lien:\n<code>{referral_link}</code>\n\n"
                f"📊 <b>Tes Stats:</b>\n"
                f"👥 Personnes référées: {stats['total']['count']}\n"
                f"💵 Commissions gagnées: ${stats['total']['total_earned']:.2f}\n"
                f"💰 Mensuel récurrent: ${stats['total']['monthly_recurring']:.2f}\n\n"
                f"🔥 Commission <b>RÉCURRENTE</b> chaque mois!"
            )
        else:
            referral_text = (
                f"🎁 <b>YOUR REFERRAL PROGRAM</b>\n\n"
                f"💰 <b>Current rate: {int(current_rate*100)}%</b> {'(override)' if is_override else '(dynamic)'}\n"
                f"👥 Active directs: {active_directs}\n"
                f"{next_tier_text}\n"
                f"🎟️ FREE Alpha at 10 active directs\n\n"
                f"Your link:\n<code>{referral_link}</code>\n\n"
                f"📊 <b>Your Stats:</b>\n"
                f"👥 Referrals: {stats['total']['count']}\n"
                f"💵 Earnings: ${stats['total']['total_earned']:.2f}\n"
                f"💰 Monthly recurring: ${stats['total']['monthly_recurring']:.2f}\n\n"
                f"🔥 <b>RECURRING</b> commission every month!"
            )

        share_btn = "📱 Share" if lang == "en" else "📱 Partager"
        copy_btn = "📋 Copy Link" if lang == "en" else "📋 Copier le Lien"
        back_btn = "◀️ Menu"
        keyboard = [
            [InlineKeyboardButton(text=share_btn, url=f"https://t.me/share/url?url={referral_link}&text={share_text}")],
            [InlineKeyboardButton(text=copy_btn, callback_data="copy_referral")],
            [InlineKeyboardButton(text=back_btn, callback_data="main_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=message,
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    
    finally:
        db.close()


@router.message(Command("settings"))
async def settings_command(message: types.Message):
    """
    /settings command - User settings
    """
    try:
        await message.delete()
    except Exception:
        pass
    user_tg = message.from_user
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        
        if not user:
            await message.answer("❌ User non trouvé!")
            return
        
        lang = user.language or "en"
        # Tier + expiry and language line in Settings
        # Admin créateur = KING OF ALPHA
        if user.telegram_id == 8213628656:
            tier_display = "KING OF ALPHA"
        elif user.tier == TierLevel.PREMIUM:
            tier_display = "ALPHA"
        else:
            tier_display = "FREE"
        tier_line = (f"🎖️ Tier: <b>{tier_display}</b>\n")
        if user.tier != TierLevel.FREE and user.subscription_end:
            days_left = user.days_until_expiry
            exp_line_en = f"⏰ Expires in: {days_left} days\n"
            exp_line_fr = f"⏰ Expire dans: {days_left} jours\n"
        else:
            exp_line_en = ""
            exp_line_fr = ""
        lang_line_en = f"🌐 Language: <b>{'English' if (user.language or 'en') == 'en' else 'Français'}</b>\n"
        lang_line_fr = f"🌐 Langue: <b>{'Anglais' if (user.language or 'en') == 'en' else 'Français'}</b>\n"
        # Percentage filters display
        filter_arb = f"⚖️ Arbitrage: <b>{user.min_arb_percent or 0.5}% - {user.max_arb_percent or 100}%</b>\n"
        filter_middle = f"🎯 Middle: <b>{user.min_middle_percent or 0.5}% - {user.max_middle_percent or 100}%</b>\n"
        filter_goodev = f"💎 Good +EV: <b>{user.min_good_ev_percent or 0.5}% - {user.max_good_ev_percent or 100}%</b>\n"
        
        # Stake rounding display
        from utils.stake_rounder import get_rounding_display
        rounding_level = user.stake_rounding or 0
        rounding_display = get_rounding_display(rounding_level, lang)
        
        # Casino filter display
        import json
        try:
            selected_casinos = json.loads(user.selected_casinos) if user.selected_casinos else []
        except:
            selected_casinos = []
        total_casinos = 18  # Total number of available casinos
        casino_count = len(selected_casinos) if selected_casinos else total_casinos
        casino_filter_line = f"🎰 Casinos: <b>{casino_count}/{total_casinos}</b>\n"
        
        match_today_status = getattr(user, 'match_today_only', False)
        
        settings_text = (
            (f"⚙️ <b>SETTINGS</b>\n\n"
             + tier_line
             + exp_line_en
             + lang_line_en
             + f"💰 Default CASHH: <b>${user.default_bankroll:.2f}</b>\n"
             + f"🔔 Notifications: <b>{'✅ Enabled' if user.notifications_enabled else '❌ Disabled'}</b>\n"
             + f"🎲 Stake Rounding: <b>{rounding_display}</b>\n"
             + f"✨ Good Odds Alerts: <b>{'✅ ON' if user.enable_good_odds else '❌ OFF'}</b>\n"
             + f"🎯 Middle Opportunities: <b>{'✅ ON' if user.enable_middle else '❌ OFF'}</b>\n"
             + f"🎮 Match Today Only: <b>{'✅ ON' if match_today_status else '❌ OFF'}</b>\n\n"
             + f"📊 <b>Filters:</b>\n"
             + filter_arb
             + filter_middle
             + filter_goodev
             + casino_filter_line)
            if lang == 'en' else
            (f"⚙️ <b>PARAMÈTRES</b>\n\n"
             + tier_line
             + exp_line_fr
             + lang_line_fr
             + f"💰 CASHH par défaut: <b>${user.default_bankroll:.2f}</b>\n"
             + f"🔔 Notifications: <b>{'✅ Activées' if user.notifications_enabled else '❌ Désactivées'}</b>\n"
             + f"🎲 Arrondi Stakes: <b>{rounding_display}</b>\n"
             + f"✨ Good Odds Alertes: <b>{'✅ ON' if user.enable_good_odds else '❌ OFF'}</b>\n"
             + f"🎯 Middle Opportunités: <b>{'✅ ON' if user.enable_middle else '❌ OFF'}</b>\n"
             + f"🎮 Match Aujourd'hui: <b>{'✅ ON' if match_today_status else '❌ OFF'}</b>\n\n"
             + f"📊 <b>Filtres:</b>\n"
             + filter_arb
             + filter_middle
             + filter_goodev
             + casino_filter_line)
        )
        
        change_cashh_text = "💰 Change CASHH" if lang == 'en' else "💰 Changer CASHH"
        lang_btn = "🌐 Language / Langue" if lang == 'en' else "🌐 Langue / Language"
        tiers_text = "💎 Alpha Tiers" if lang == 'en' else "💎 Tiers Alpha"
        notif_text = (("🔔 Disable" if user.notifications_enabled else "🔔 Enable") if lang == 'en'
                      else ("🔔 Désactiver" if user.notifications_enabled else "🔔 Activer"))
        filter_text = "📊 Filter by %" if lang == 'en' else "📊 Filtrer par %"
        rounding_text = "🎲 Stake Rounding" if lang == 'en' else "🎲 Arrondi Stakes"
        casino_filter_text = "🎰 Filter by Casino" if lang == 'en' else "🎰 Filtrer par Casino"
        
        # Build keyboard based on order: CASHH, Filters, Rounding, Notif, Good Odds, Middle, Bet Focus, Lang, Tiers
        keyboard = [
            [InlineKeyboardButton(text=change_cashh_text, callback_data="change_bankroll")],
            [InlineKeyboardButton(text=filter_text, callback_data="percent_filters")],
            [InlineKeyboardButton(text=casino_filter_text, callback_data="casino_filter_menu")],
            [InlineKeyboardButton(text=rounding_text, callback_data="stake_rounding_menu")],
            [InlineKeyboardButton(text=notif_text, callback_data="toggle_notifications")],
            [InlineKeyboardButton(text=("✨ Good Odds: ON" if user.enable_good_odds else "✨ Good Odds: OFF"), callback_data="toggle_good_odds")],
            [InlineKeyboardButton(text=("🎯 Middle: ON" if user.enable_middle else "🎯 Middle: OFF"), callback_data="toggle_middle")],
            [InlineKeyboardButton(text=("📈 Bet Focus: ON" if user.bet_focus_mode else "📈 Bet Focus: OFF"), callback_data="toggle_bet_focus")],
            [InlineKeyboardButton(text=("🎮 Match Today: ON" if getattr(user, 'match_today_only', False) else "🎮 Match Today: OFF"), callback_data="toggle_match_today")],
            [InlineKeyboardButton(text=lang_btn, callback_data="change_language")],
            [InlineKeyboardButton(text=tiers_text, callback_data="show_tiers")],
        ]
        
        # Add Casinos, Guide, Referral at bottom if IN bet focus mode (on one line)
        # When OFF, they're in the main menu instead
        if user.bet_focus_mode:
            keyboard.append([
                InlineKeyboardButton(text=("🎰 Casinos" if lang == 'en' else "🎰 Casinos"), callback_data="show_casinos"),
                InlineKeyboardButton(text=("📖 Guide" if lang == 'en' else "📖 Guide"), callback_data="show_guide"),
                InlineKeyboardButton(text=("🎁 Referral" if lang == 'en' else "🎁 Parrainage"), callback_data="show_referral")
            ])
        
        # Menu button at the end
        keyboard.append([InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=message,
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    
    finally:
        db.close()


# Callback query handlers
@router.callback_query(F.data == "show_tiers")
async def callback_show_tiers(callback: types.CallbackQuery):
    """Show tier options"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("Please send /menu", show_alert=True)
            return
        lang = user.language or "en"
        
        # Check for active bonus
        bonus_result = db.execute(text("""
            SELECT bonus_activated_at, bonus_expires_at, bonus_redeemed, bonus_amount
            FROM bonus_tracking
            WHERE telegram_id = :tid
                AND bonus_activated_at IS NOT NULL
                AND bonus_redeemed = 0
                AND bonus_expires_at > :now
        """), {'tid': callback.from_user.id, 'now': datetime.now()}).first()
        
        has_active_bonus = bonus_result is not None
        price_display = "200 CAD/mois" if lang == "fr" else "200 CAD/month"
        
        if has_active_bonus:
            bonus_amount = bonus_result.bonus_amount or 50
            discounted_price = 200 - bonus_amount
            price_display = f"<s>200</s> {discounted_price} CAD/mois 🎁" if lang == "fr" else f"<s>200</s> {discounted_price} CAD/month 🎁"
        
        if lang == "fr":
            tier_message = (
                "💎 <b>BETA vs ALPHA</b>\n\n"
                "🧪 <b>BETA (GRATUIT)</b>\n"
                "• 5 alertes par jour\n"
                "• Arbitrages < 2.5%\n"
                "• Alertes en temps réel\n\n"
                f"🔥 <b>ALPHA - {price_display}</b>\n"
                "• Alertes illimitées\n"
                "• Tous les arbitrages (≥0.5%)\n"
                "• Middle Bets + Good Odds\n"
                "• Filtres avancés\n"
                "• Vérificateur de cotes auto\n"
                "• Mode RISKED\n"
                "• Calculateur personnalisé\n"
                "• Stats avancées\n"
                "• Support VIP\n"
                "• 20% de parrainage à vie\n\n"
                "💰 Paiement en crypto uniquement\n"
                "🎁 Programme de parrainage: Gagnez 20% de commission récurrente!\n"
            )
        else:
            tier_message = (
                "💎 <b>BETA vs ALPHA</b>\n\n"
                "🧪 <b>BETA (FREE)</b>\n"
                "• 5 alerts per day\n"
                "• Arbitrages &lt; 2.5%\n"
                "• Real-time alerts\n\n"
                f"🔥 <b>ALPHA - {price_display}</b>\n"
                "• Unlimited alerts\n"
                "• All arbitrages (≥0.5%)\n"
                "• Middle Bets + Good Odds\n"
                "• Optimized Parlays (Beta)\n"
                "• Book Health Monitor\n"
                "• Advanced filters\n"
                "• Auto odds checker\n"
                "• RISKED mode\n"
                "• Custom calculator\n"
                "• Advanced stats\n"
                "• VIP support\n"
                "• 20% referral for life\n"
                "\n"
                "💰 <b>Crypto payment only</b>\n"
                "🎁 <b>Referral Program:</b> Earn 20% recurring commission!"
            )
        
        keyboard = [
            [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == "fr" else "🔥 Buy ALPHA"), callback_data="buy_premium")],
            [InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=callback,
            text=tier_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "show_referral")
async def callback_show_referral(callback: types.CallbackQuery):
    """Show referral info"""
    await callback.answer()
    db = SessionLocal()
    try:
        user_tg = callback.from_user
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        referral_code = ReferralManager.create_user_referral_code(db, user_tg.id)
        # Resolve bot username dynamically
        bot_username = os.getenv("BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME")
        if not bot_username:
            try:
                me = await callback.bot.get_me()
                bot_username = me.username
            except Exception:
                bot_username = "Risk0_bot"
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        stats = ReferralManager.get_referral_stats(db, user_tg.id)
        # Dynamic commission info
        active_directs = 0
        try:
            active_directs = ReferralManager.count_active_tier1(db, user_tg.id)
        except Exception:
            active_directs = 0
        try:
            current_rate = ReferralManager.get_dynamic_tier1_rate(db, user_tg.id)
        except Exception:
            current_rate = 0.20
        
        # Different tiers for FREE vs PREMIUM
        is_free_user = user.tier == TierLevel.FREE
        lang = user.language or "en"
        if is_free_user:
            # FREE: 10% base
            if lang == 'fr':
                next_tier_text = "➡️ Upgrade ALPHA: 12.5% à vie + bonus jusqu'à 40%!"
            else:
                next_tier_text = "➡️ Upgrade ALPHA: 12.5% forever + bonus up to 40%!"
        else:
            # ALPHA: 12.5% permanent + bonuses with directs
            if lang == 'fr':
                next_tier_text = "🎉 Alpha = 12.5% à VIE!"
            else:
                next_tier_text = "🎉 Alpha = 12.5% FOREVER!"
            # Show next tier bonus
            tiers_info = [
                (5, 0.15), (10, 0.25), (20, 0.30), (30, 0.40)
            ]
            for thr, rate in tiers_info:
                if active_directs < thr:
                    next_tier_text += f"\n➡️ {thr} directs → {int(rate*100)}% bonus"
                    break
            if active_directs >= 30:
                next_tier_text += "\n✅ Max rate (40%) reached!"
        
        if lang == "fr":
            referral_text = (
                f"🎁 <b>TON PROGRAMME REFERRAL</b>\n\n"
                f"💰 <b>Taux actuel: {int(current_rate*100)}%</b> (récurrent)\n"
                f"👥 Directs actifs: {active_directs}\n"
                f"{next_tier_text}\n"
                f"🎟️ Alpha GRATUIT à 10 directs actifs\n\n"
                f"Ton lien:\n<code>{referral_link}</code>\n\n"
                f"📊 <b>Tes Stats:</b>\n"
                f"👥 Personnes référées: {stats['total']['count']}\n"
                f"💵 Commissions gagnées: ${stats['total']['total_earned']:.2f}\n"
                f"💰 Mensuel récurrent: ${stats['total']['monthly_recurring']:.2f}\n\n"
                f"🔥 Commission <b>RÉCURRENTE</b> chaque mois!\n\n"
                f"❓ Besoin d'aide ? Contacte @Z3RORISK"
            )
            share_text = "Rejoins Risk0 Casino!"
        else:
            referral_text = (
                f"🎁 <b>YOUR REFERRAL PROGRAM</b>\n\n"
                f"💰 <b>Current rate: {int(current_rate*100)}%</b> (recurring)\n"
                f"👥 Active directs: {active_directs}\n"
                f"{next_tier_text}\n"
                f"🎟️ FREE Alpha at 10 active directs\n\n"
                f"Your link:\n<code>{referral_link}</code>\n\n"
                f"📊 <b>Your Stats:</b>\n"
                f"👥 Referrals: {stats['total']['count']}\n"
                f"💵 Earnings: ${stats['total']['total_earned']:.2f}\n"
                f"💰 Monthly recurring: ${stats['total']['monthly_recurring']:.2f}\n\n"
                f"🔥 <b>RECURRING</b> commission every month!\n\n"
                f"❓ Need help? Contact @Z3RORISK"
            )
            share_text = "Join Risk0 Casino!"
        share_btn = "📱 Share" if lang == "en" else "📱 Partager"
        copy_btn = "📋 Copy Link" if lang == "en" else "📋 Copier le Lien"
        back_btn = "◀️ Menu"
        keyboard = [
            [InlineKeyboardButton(text=share_btn, url=f"https://t.me/share/url?url={referral_link}&text={share_text}")],
            [InlineKeyboardButton(text=copy_btn, callback_data="copy_referral")],
            [InlineKeyboardButton(text=back_btn, callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=callback,
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "copy_referral")
async def callback_copy_referral(callback: types.CallbackQuery):
    """Send a message with the user's referral link for easy copy."""
    await callback.answer()
    db = SessionLocal()
    try:
        user_tg = callback.from_user
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        if not user:
            await callback.answer("❌ User non trouvé!", show_alert=True)
            return
        code = ReferralManager.create_user_referral_code(db, user_tg.id)
        bot_username = os.getenv("BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME")
        if not bot_username:
            try:
                me = await callback.bot.get_me()
                bot_username = me.username
            except Exception:
                bot_username = "Risk0_bot"
        link = f"https://t.me/{bot_username}?start={code}"
        lang = user.language or "en"
        if lang == 'fr':
            text = f"📋 Ton lien referral:\n<code>{link}</code>"
        else:
            text = f"📋 Your referral link:\n<code>{link}</code>"
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    finally:
        db.close()


# DISABLED: Duplicate handler - using the one in bet_handlers.py instead (has I BET menu + stats by type)
# @router.callback_query(F.data == "my_stats")
# async def callback_my_stats(callback: types.CallbackQuery):
#     """Show stats"""
#     pass


@router.callback_query(F.data == "settings")
async def callback_settings(callback: types.CallbackQuery):
    """Show settings"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        lang = user.language or "en"
        # Admin créateur = KING OF ALPHA
        if user.telegram_id == 8213628656:
            tier_display = "KING OF ALPHA"
        elif user.tier == TierLevel.PREMIUM:
            tier_display = "ALPHA"
        else:
            tier_display = "FREE"
        tier_line = (f"🎖️ Tier: <b>{tier_display}</b>\n")
        if user.tier != TierLevel.FREE and user.subscription_end:
            days_left = user.days_until_expiry
            exp_line_en = f"⏰ Expires in: {days_left} days\n"
            exp_line_fr = f"⏰ Expire dans: {days_left} jours\n"
        else:
            exp_line_en = ""
            exp_line_fr = ""
        lang_line_en = f"🌐 Language: <b>{'English' if (user.language or 'en') == 'en' else 'Français'}</b>\n"
        lang_line_fr = f"🌐 Langue: <b>{'Anglais' if (user.language or 'en') == 'en' else 'Français'}</b>\n"
        
        # Premium-only notification types
        premium_notifs_en = ""
        premium_notifs_fr = ""
        if user.tier == TierLevel.PREMIUM:
            match_today_status = getattr(user, 'match_today_only', False)
            premium_notifs_en = (
                f"✨ Good Odds Alerts: <b>{'✅ ON' if user.enable_good_odds else '❌ OFF'}</b>\n"
                f"🎯 Middle Opportunities: <b>{'✅ ON' if user.enable_middle else '❌ OFF'}</b>\n"
                f"🎮 Match Today Only: <b>{'✅ ON' if match_today_status else '❌ OFF'}</b>\n"
            )
            premium_notifs_fr = (
                f"✨ Good Odds Alerts: <b>{'✅ ON' if user.enable_good_odds else '❌ OFF'}</b>\n"
                f"🎯 Middle Opportunities: <b>{'✅ ON' if user.enable_middle else '❌ OFF'}</b>\n"
                f"🎮 Match Aujourd'hui: <b>{'✅ ON' if match_today_status else '❌ OFF'}</b>\n"
            )
        
        # Percentage filters display (FREE users have restricted filters)
        if user.tier == TierLevel.FREE:
            filter_arb = f"⚖️ Arbitrage: <b>{user.min_arb_percent or 0.5}% - {min(user.max_arb_percent or 2.5, 2.5)}%</b>\n"
            filter_middle = f"🎯 Middle: <b>0% - 0%</b> 🔒 Premium\n"
            filter_goodev = f"💎 Good +EV: <b>0% - 0%</b> 🔒 Premium\n"
        else:
            filter_arb = f"⚖️ Arbitrage: <b>{user.min_arb_percent or 0.5}% - {user.max_arb_percent or 100}%</b>\n"
            filter_middle = f"🎯 Middle: <b>{user.min_middle_percent or 0.5}% - {user.max_middle_percent or 100}%</b>\n"
            filter_goodev = f"💎 Good +EV: <b>{user.min_good_ev_percent or 0.5}% - {user.max_good_ev_percent or 100}%</b>\n"
        
        # Stake rounding display
        from utils.stake_rounder import get_rounding_display
        rounding_level = user.stake_rounding or 0
        rounding_display = get_rounding_display(rounding_level, lang)
        
        # Casino filter display
        import json
        try:
            selected_casinos = json.loads(user.selected_casinos) if user.selected_casinos else []
        except:
            selected_casinos = []
        total_casinos = 18
        casino_count = len(selected_casinos) if selected_casinos else total_casinos
        casino_filter_line = f"🎰 Casinos: <b>{casino_count}/{total_casinos}</b>\n"
        
        # Sport filter display
        try:
            selected_sports = json.loads(user.selected_sports) if user.selected_sports else []
        except:
            selected_sports = []
        total_sports = 8  # all, basketball, soccer, tennis, hockey, football, baseball, mma
        sport_count = len(selected_sports) if selected_sports else total_sports
        sport_filter_line = f"🏅 Sports: <b>{sport_count}/{total_sports}</b>\n"
        
        # Hide rounding for FREE users (risk removed entirely)
        if user.tier == TierLevel.FREE:
            rounding_line_en = ""
            rounding_line_fr = ""
        else:
            rounding_line_en = f"🎲 Stake Rounding: <b>{rounding_display}</b>\n"
            rounding_line_fr = f"🎲 Arrondi Stakes: <b>{rounding_display}</b>\n"
        
        settings_text = (
            (f"⚙️ <b>SETTINGS</b>\n\n"
             + tier_line
             + exp_line_en
             + lang_line_en
             + f"💰 Default CASHH: <b>${user.default_bankroll:.2f}</b>\n"
             + f"🔔 Notifications: <b>{'✅ Enabled' if user.notifications_enabled else '❌ Disabled'}</b>\n"
             + rounding_line_en
             + premium_notifs_en
             + f"\n📊 <b>Filters:</b>\n"
             + filter_arb
             + filter_middle
             + filter_goodev
             + casino_filter_line
             + sport_filter_line)
            if lang == 'en' else
            (f"⚙️ <b>PARAMÈTRES</b>\n\n"
             + tier_line
             + exp_line_fr
             + lang_line_fr
             + f"💰 CASHH par défaut: <b>${user.default_bankroll:.2f}</b>\n"
             + f"🔔 Notifications: <b>{'✅ Activées' if user.notifications_enabled else '❌ Désactivées'}</b>\n"
             + rounding_line_fr
             + premium_notifs_fr
             + f"\n📊 <b>Filtres:</b>\n"
             + filter_arb
             + filter_middle
             + filter_goodev
             + casino_filter_line
             + sport_filter_line)
        )
        change_cashh_text = "💰 Change CASHH" if lang == 'en' else "💰 Changer CASHH"
        lang_btn = "🌐 Langue / Language" if lang == 'en' else "🌐 Langue / Language"
        tiers_text = "💎 Alpha Tiers" if lang == 'en' else "💎 Tiers Alpha"
        notif_text = (("🔔 Disable" if user.notifications_enabled else "🔔 Enable") if lang == 'en' 
                      else ("🔔 Désactiver" if user.notifications_enabled else "🔔 Activer"))
        
        # Build keyboard in correct order
        keyboard = [
            [InlineKeyboardButton(text=change_cashh_text, callback_data="change_bankroll")],
        ]
        
        # Premium-only features for FREE users show "Buy Premium"
        if user.tier == TierLevel.FREE:
            keyboard.append([InlineKeyboardButton(text=lang_btn, callback_data="change_language")])
            keyboard.append([InlineKeyboardButton(text=tiers_text, callback_data="show_tiers")])
            keyboard.append([InlineKeyboardButton(text=notif_text, callback_data="toggle_notifications")])
            buy_premium_text = "🔒 Buy Alpha for Advanced Features" if lang == 'en' else "🔒 Acheter Alpha pour Fonctions Avancées"
            keyboard.append([InlineKeyboardButton(text=buy_premium_text, callback_data="show_tiers")])
        else:
            # ALPHA users get actual controls in this order:
            # Filter %, Filter Casino, Filter Sport, Rounding, Notif, Good Odds, Middle, Bet Focus, Lang, Tiers
            filter_text = "📊 Filter by %" if lang == 'en' else "📊 Filtrer par %"
            casino_filter_text = "🎰 Filter by Casino" if lang == 'en' else "🎰 Filtrer par Casino"
            sport_filter_text = "🏅 Filter by Sport" if lang == 'en' else "🏅 Filtrer par Sport"
            rounding_text = "🎲 Stake Rounding" if lang == 'en' else "🎲 Arrondi Stakes"
            
            keyboard.append([InlineKeyboardButton(text=filter_text, callback_data="percent_filters")])
            keyboard.append([InlineKeyboardButton(text=casino_filter_text, callback_data="casino_filter_menu")])
            keyboard.append([InlineKeyboardButton(text=sport_filter_text, callback_data="sport_filter_menu")])
            keyboard.append([InlineKeyboardButton(text=rounding_text, callback_data="stake_rounding_menu")])
            keyboard.append([InlineKeyboardButton(text=notif_text, callback_data="toggle_notifications")])
            
            # Good Odds and Middle toggle buttons
            good_odds_text = (f"✨ Good Odds: {'ON' if user.enable_good_odds else 'OFF'}" if lang == 'en' 
                             else f"✨ Good Odds: {'ON' if user.enable_good_odds else 'OFF'}")
            middle_text = (f"🎯 Middle: {'ON' if user.enable_middle else 'OFF'}" if lang == 'en' 
                          else f"🎯 Middle: {'ON' if user.enable_middle else 'OFF'}")
            keyboard.append([InlineKeyboardButton(text=good_odds_text, callback_data="toggle_good_odds")])
            keyboard.append([InlineKeyboardButton(text=middle_text, callback_data="toggle_middle")])
            
            # Bet Focus Mode toggle
            bet_focus_enabled = getattr(user, 'bet_focus_mode', False)
            bet_focus_text = (f"📈 Bet Focus: {'ON' if bet_focus_enabled else 'OFF'}" if lang == 'en' 
                             else f"📈 Bet Focus: {'ON' if bet_focus_enabled else 'OFF'}")
            keyboard.append([InlineKeyboardButton(text=bet_focus_text, callback_data="toggle_bet_focus")])
            
            # Match Today toggle
            match_today_enabled = getattr(user, 'match_today_only', False)
            match_today_text = (f"🎮 Match Today: {'ON' if match_today_enabled else 'OFF'}" if lang == 'en' 
                               else f"🎮 Match Auj.: {'ON' if match_today_enabled else 'OFF'}")
            keyboard.append([InlineKeyboardButton(text=match_today_text, callback_data="toggle_match_today")])
            
            # Lang and Tiers
            keyboard.append([InlineKeyboardButton(text=lang_btn, callback_data="change_language")])
            keyboard.append([InlineKeyboardButton(text=tiers_text, callback_data="show_tiers")])
            
            # If Bet Focus Mode is ON, show Casino/Guide/Referral here (on one line, side by side)
            # When OFF, they're in the main menu instead
            if bet_focus_enabled:
                casino_btn_text = "🎰 Casinos" if lang == 'en' else "🎰 Casinos"
                guide_btn_text = "📖 Guide" if lang == 'en' else "📖 Guide"
                referral_btn_text = "🎁 Referral" if lang == 'en' else "🎁 Referral"
                keyboard.append([
                    InlineKeyboardButton(text=casino_btn_text, callback_data="show_casinos"),
                    InlineKeyboardButton(text=guide_btn_text, callback_data="learn_guide_pro"),
                    InlineKeyboardButton(text=referral_btn_text, callback_data="show_referral")
                ])
            
            # More button for ALPHA users (News, Proxy TOS, etc.)
            more_btn_text = "➕ More" if lang == 'en' else "➕ Plus"
            keyboard.append([InlineKeyboardButton(text=more_btn_text, callback_data="settings_more")])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=callback,
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "settings_more")
async def callback_settings_more(callback: types.CallbackQuery):
    """Show MORE settings page (ALPHA only - News, Proxy TOS)"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        
        lang = user.language or "en"
        
        # Only ALPHA users can access
        if user.tier == TierLevel.FREE:
            await callback.answer("🔒 ALPHA Only!", show_alert=True)
            return
        
        if lang == 'fr':
            text = (
                "⚙️ <b>PARAMÈTRES - Plus</b>\n\n"
                "Options additionnelles:\n"
            )
        else:
            text = (
                "⚙️ <b>SETTINGS - More</b>\n\n"
                "Additional options:\n"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="📰 News" if lang == 'en' else "📰 Nouvelles",
                callback_data="show_news"
            )],
            [InlineKeyboardButton(
                text="📜 TOS & Legal" if lang == 'en' else "📜 TOS & Légal",
                callback_data="show_proxy_tos"
            )],
            [InlineKeyboardButton(
                text="🗑️ Erase All History" if lang == 'en' else "🗑️ Effacer Historique",
                callback_data="confirm_erase_history"
            )],
            [InlineKeyboardButton(
                text="◀️ Back to Settings" if lang == 'en' else "◀️ Retour aux Paramètres",
                callback_data="settings"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "confirm_erase_history")
async def callback_confirm_erase_history(callback: types.CallbackQuery):
    """Ask confirmation before erasing all history"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        
        lang = user.language or "en"
        
        # Count user's bets
        bet_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == callback.from_user.id
        ).scalar() or 0
        
        if lang == 'fr':
            title = "⚠️ ATTENTION"
            text = (
                f"<b>⚠️ CONFIRMATION REQUISE</b>\n\n"
                f"Tu es sur le point d'effacer <b>TOUTES</b> tes données:\n\n"
                f"📊 <b>{bet_count} bets</b> enregistrés\n"
                f"📈 Toutes les statistiques\n"
                f"🗓️ Tout l'historique\n\n"
                f"<b>⚠️ Cette action est IRRÉVERSIBLE!</b>\n\n"
                f"Es-tu vraiment sûr?"
            )
            yes_btn = "✅ OUI, EFFACER TOUT"
            no_btn = "❌ NON, ANNULER"
        else:
            title = "⚠️ WARNING"
            text = (
                f"<b>⚠️ CONFIRMATION REQUIRED</b>\n\n"
                f"You are about to erase <b>ALL</b> your data:\n\n"
                f"📊 <b>{bet_count} bets</b> recorded\n"
                f"📈 All statistics\n"
                f"🗓️ All history\n\n"
                f"<b>⚠️ This action is IRREVERSIBLE!</b>\n\n"
                f"Are you really sure?"
            )
            yes_btn = "✅ YES, ERASE ALL"
            no_btn = "❌ NO, CANCEL"
        
        keyboard = [
            [InlineKeyboardButton(text=yes_btn, callback_data="erase_all_history_confirmed")],
            [InlineKeyboardButton(text=no_btn, callback_data="settings_more")],
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "erase_all_history_confirmed")
async def callback_erase_all_history_confirmed(callback: types.CallbackQuery):
    """Actually erase all user history and stats"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        
        lang = user.language or "en"
        user_id = callback.from_user.id
        
        # Count before deletion
        bet_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id
        ).scalar() or 0
        
        # DELETE ALL user bets
        db.query(UserBet).filter(UserBet.user_id == user_id).delete()
        db.commit()
        
        if lang == 'fr':
            text = (
                f"✅ <b>HISTORIQUE EFFACÉ</b>\n\n"
                f"🗑️ <b>{bet_count} bets</b> supprimés\n"
                f"📊 Toutes les stats réinitialisées à 0\n"
                f"🔄 Tu peux recommencer à zéro!\n\n"
                f"Tes prochains I BET seront enregistrés normalement."
            )
            back_btn = "◀️ Retour aux Paramètres"
        else:
            text = (
                f"✅ <b>HISTORY ERASED</b>\n\n"
                f"🗑️ <b>{bet_count} bets</b> deleted\n"
                f"📊 All stats reset to 0\n"
                f"🔄 You can start fresh!\n\n"
                f"Your next I BET clicks will be recorded normally."
            )
            back_btn = "◀️ Back to Settings"
        
        keyboard = [
            [InlineKeyboardButton(text=back_btn, callback_data="settings")]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "show_news")
async def callback_show_news(callback: types.CallbackQuery):
    """Show News page"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        
        lang = user.language or "en"
        
        if lang == 'fr':
            text = (
                "📰 <b>NOUVELLES RISK0</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>📅 29 Novembre 2025</b>\n\n"
                "🎲 <b>NOUVEAU: Système Parlays Intelligent!</b>\n"
                "• Parlays avec corrélations détectées\n"
                "• 4 profils de risque (Conservative → Lottery)\n"
                "• Suivi des cotes en temps réel\n"
                "• Analyses avancées et historique\n\n"
                "🎯 <b>Bet Focus Mode</b>\n"
                "• Menu simplifié avec boutons essentiels\n"
                "• Accès rapide I BET, Stats, Calls\n"
                "• Interface épurée pour focus optimal\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>📅 27 Novembre 2025</b>\n\n"
                "🎉 <b>Nouveau: Guide Complet ALPHA!</b>\n"
                "• Tous les guides débloqués pour membres ALPHA\n"
                "• Navigation séquentielle améliorée\n"
                "• Contenu exclusif Pro Tips (3 sections)\n\n"
                "🔧 <b>Améliorations Settings:</b>\n"
                "• Page 'More' pour membres ALPHA\n"
                "• Accès rapide aux News\n"
                "• Liens Privacy & Legal disponibles\n\n"
                "📊 <b>Nouvelles Fonctionnalités:</b>\n"
                "• Filtres dans Last Calls ajoutés\n"
                "• Fonction I BET intégrée pour tracking\n"
                "• Statistiques améliorées\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Plus de mises à jour à venir! 🚀"
            )
        else:
            text = (
                "📰 <b>RISK0 NEWS</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>📅 November 29, 2025</b>\n\n"
                "🎲 <b>NEW: Intelligent Parlay System!</b>\n"
                "• Parlays with detected correlations\n"
                "• 4 risk profiles (Conservative → Lottery)\n"
                "• Real-time odds tracking\n"
                "• Advanced analytics and history\n\n"
                "🎯 <b>Bet Focus Mode</b>\n"
                "• Simplified menu with essential buttons\n"
                "• Quick access to I BET, Stats, Calls\n"
                "• Clean interface for optimal focus\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<b>📅 November 27, 2025</b>\n\n"
                "🎉 <b>New: Complete ALPHA Guide!</b>\n"
                "• All guides unlocked for ALPHA members\n"
                "• Improved sequential navigation\n"
                "• Exclusive Pro Tips content (3 sections)\n\n"
                "🔧 <b>Settings Improvements:</b>\n"
                "• 'More' page for ALPHA members\n"
                "• Quick access to News\n"
                "• Privacy & Legal links available\n\n"
                "📊 <b>New Features:</b>\n"
                "• Last Calls filters added\n"
                "• I BET tracking function integrated\n"
                "• Enhanced statistics\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "More updates coming soon! 🚀"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="◀️ Back" if lang == 'en' else "◀️ Retour",
                callback_data="settings_more" if user.tier != TierLevel.FREE else "learn_guide_pro"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "show_proxy_tos")
async def callback_show_proxy_tos(callback: types.CallbackQuery):
    """Show Proxy TOS links"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ User non trouvé! Tape /start", show_alert=True)
            return
        
        lang = user.language or "en"
        
        # Only ALPHA users
        if user.tier == TierLevel.FREE:
            await callback.answer("🔒 ALPHA Only!", show_alert=True)
            return
        
        if lang == 'fr':
            text = (
                "📜 <b>TOS & LÉGAL</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔗 <b>Liens Importants:</b>\n\n"
                "Clique sur les boutons ci-dessous pour accéder aux documents:\n"
            )
        else:
            text = (
                "📜 <b>TOS & LEGAL</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔗 <b>Important Links:</b>\n\n"
                "Click the buttons below to access the documents:\n"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="📄 Terms of Service" if lang == 'en' else "📄 Conditions d'Utilisation",
                url="https://telegra.ph/RISK0---TERMS--CONDITIONS-11-27"
            )],
            [InlineKeyboardButton(
                text="🔒 Privacy Policy" if lang == 'en' else "🔒 Politique de Confidentialité",
                url="https://telegra.ph/RISK0---PRIVACY-POLICY-11-27"
            )],
            [InlineKeyboardButton(
                text="⚠️ Risk Disclosure" if lang == 'en' else "⚠️ Divulgation des Risques",
                url="https://telegra.ph/RISK0---RISK-DISCLOSURE-11-27"
            )],
            [InlineKeyboardButton(
                text="🆘 Support" if lang == 'en' else "🆘 Support",
                callback_data="show_support"
            )],
            [InlineKeyboardButton(
                text="◀️ Back to More" if lang == 'en' else "◀️ Retour à Plus",
                callback_data="settings_more"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data == "buy_premium")
async def callback_buy_premium(callback: types.CallbackQuery):
    """Handle PREMIUM tier purchase via crypto"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("Please send /start", show_alert=True)
            return
        
        lang = user.language or "en"
        base_price = TierManager.get_price(CoreTierLevel.PREMIUM)
        
        # 🧪 TEST MODE: Set price to $3 for testing account
        # 2nd account for payment testing
        TEST_ACCOUNT_ID = 8004919557  # Test account - $3 price
        
        if callback.from_user.id == TEST_ACCOUNT_ID and TEST_ACCOUNT_ID != 0:
            # TEST MODE: $10 for testing payment system (min amount for most cryptos)
            price = 10.0
            bonus_amount = 190  # Show as discount from $200 to $10
            has_active_bonus = True
            base_price = 200
        else:
            # Normal flow
            # Check if user has active bonus
            bonus_result = db.execute(text("""
                SELECT bonus_activated_at, bonus_expires_at, bonus_redeemed, bonus_amount
                FROM bonus_tracking
                WHERE telegram_id = :tid
                    AND bonus_activated_at IS NOT NULL
                    AND bonus_redeemed = 0
                    AND bonus_expires_at > :now
            """), {'tid': callback.from_user.id, 'now': datetime.now()}).first()
            
            has_active_bonus = bonus_result is not None
            price = base_price
            bonus_amount = 0
            
            if has_active_bonus:
                bonus_amount = bonus_result.bonus_amount or 50
                price = base_price - bonus_amount
        
        if lang == "fr":
            if has_active_bonus:
                payment_text = (
                    f"💎 <b>ALPHA - <s>{base_price}</s> {price} CAD/mois</b> 🎁\n"
                    f"(Rabais nouveau membre: ${bonus_amount})\n\n"
                    f"💰 <b>Paiement crypto via NOWPayments</b>\n\n"
                    f"Clique sur 'Payer avec Crypto' pour générer ta facture de paiement.\n\n"
                    f"📱 Ton ID Telegram: <code>{callback.from_user.id}</code>\n\n"
                    f"✅ Cryptos acceptées: BTC, ETH, USDT, LTC, TRX, BCH, BNB, SOL, TON, DOGE, et 150+ autres\n\n"
                    f"⚡ Activation automatique après confirmation du paiement\n"
                    f"🔐 Paiement sécurisé et anonyme"
                )
            else:
                payment_text = (
                    f"💎 <b>ALPHA - {price} CAD/mois</b>\n\n"
                    f"💰 <b>Paiement crypto via NOWPayments</b>\n\n"
                    f"Clique sur 'Payer avec Crypto' pour générer ta facture de paiement.\n\n"
                    f"📱 Ton ID Telegram: <code>{callback.from_user.id}</code>\n\n"
                    f"✅ Cryptos acceptées: BTC, ETH, USDT, LTC, TRX, BCH, BNB, SOL, TON, DOGE, et 150+ autres\n\n"
                    f"⚡ Activation automatique après confirmation du paiement\n"
                    f"🔐 Paiement sécurisé et anonyme"
                )
            pay_text = "💳 Payer avec Crypto"
            admin_text = "💬 Support"
            back_text = "◀️ Retour"
        else:
            if has_active_bonus:
                payment_text = (
                    f"💎 <b>ALPHA - <s>{base_price}</s> {price} CAD/month</b> 🎁\n"
                    f"(New member discount: ${bonus_amount})\n\n"
                    f"💰 <b>Crypto payment via NOWPayments</b>\n\n"
                    f"Click 'Pay with Crypto' to generate your payment invoice.\n\n"
                    f"📱 Your Telegram ID: <code>{callback.from_user.id}</code>\n\n"
                    f"✅ Accepted cryptos: BTC, ETH, USDT, LTC, TRX, BCH, BNB, SOL, TON, DOGE, and 150+ more\n\n"
                    f"⚡ Auto-activation after payment confirmation\n"
                    f"🔐 Secure and anonymous payment"
                )
            else:
                payment_text = (
                    f"💎 <b>ALPHA - {price} CAD/month</b>\n\n"
                    f"💰 <b>Crypto payment via NOWPayments</b>\n\n"
                    f"Click 'Pay with Crypto' to generate your payment invoice.\n\n"
                    f"📱 Your Telegram ID: <code>{callback.from_user.id}</code>\n\n"
                    f"✅ Accepted cryptos: BTC, ETH, USDT, LTC, TRX, BCH, BNB, SOL, TON, DOGE, and 150+ more\n\n"
                    f"⚡ Auto-activation after payment confirmation\n"
                    f"🔐 Secure and anonymous payment"
                )
            pay_text = "💳 Pay with Crypto"
            admin_text = "💬 Support"
            back_text = "◀️ Back"
        
        # NOWPayments payment link (configure via env), fallback to admin chat link
        admin_username = os.getenv("ADMIN_USERNAME", "ZEROR1SK")
        # Prefer username-based link for reliability across clients
        admin_url = f"https://t.me/{admin_username}"
        # Try to create a NOWPayments invoice dynamically for this user
        pay_url = None
        try:
            invoice = await NOWPaymentsManager.create_invoice(
                telegram_id=callback.from_user.id,
                amount_cad=float(price),
            )
            if invoice and invoice.get("invoice_url"):
                pay_url = invoice["invoice_url"]
        except Exception:
            pay_url = None
        if not pay_url:
            # Fallback to static payment link from env or admin DM link
            pay_url = os.getenv("NOWPAYMENTS_PAYMENT_LINK")
            if not pay_url or not pay_url.strip():
                pay_url = admin_url

        keyboard = [
            [InlineKeyboardButton(text=pay_text, url=pay_url)],
            [InlineKeyboardButton(text=admin_text, url=admin_url)],
            [InlineKeyboardButton(text=back_text, callback_data="show_tiers")]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=payment_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


async def build_menu_keyboard(user, lang, dash_url=None, bet_focus=False):
    """Build unified menu keyboard based on user tier"""
    keyboard = [
        [InlineKeyboardButton(text="🚀 RISK0 Dashboard", url=dash_url)] if dash_url else None,
        [InlineKeyboardButton(text=("📊 Mes Stats" if lang == "fr" else "📊 My Stats"), callback_data="my_stats")],
    ]
    keyboard = [k for k in keyboard if k is not None]  # Remove None entries

    # Add Last Calls and Parlays only for PREMIUM users
    if user.tier != TierLevel.FREE:
        keyboard.extend([
            [InlineKeyboardButton(text=("🕒 Derniers Calls" if lang == "fr" else "🕒 Last Calls"), callback_data="last_calls")],
            [InlineKeyboardButton(text=("🎲 Parlays" if lang == "fr" else "🎲 Parlays"), callback_data="parlays_info")],
        ])

    # Settings for all users
    keyboard.append([InlineKeyboardButton(text=("⚙️ Paramètres" if lang == "fr" else "⚙️ Settings"), callback_data="settings")])

    # Add Casino/Guide/Referral if bet_focus_mode is OFF
    if not bet_focus:
        keyboard.extend([
            [InlineKeyboardButton(text=("🎰 Casinos" if lang == "fr" else "🎰 Casinos"), callback_data="show_casinos")],
            [InlineKeyboardButton(text=("📖 Guide" if lang == "fr" else "📖 Guide"), callback_data="learn_guide_pro")],
            [InlineKeyboardButton(text=("🎁 Parrainage" if lang == "fr" else "🎁 Referral"), callback_data="show_referral")],
        ])
        # Add upgrade button for FREE users after referral
        if user.tier == TierLevel.FREE:
            keyboard.append([InlineKeyboardButton(text="🔥 ALPHA", callback_data="show_tiers")])

    return keyboard


@router.callback_query(F.data == "pay_usdt")
async def callback_pay_usdt(callback: types.CallbackQuery):
    """Show USDT payment info"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.message.answer("Please send /start first!")
            return
        lang = user.language or "en"
        
        if lang == "fr":
            text = (
                "💳 <b>PAIEMENT USDT (TRC20)</b>\n\n"
                "💵 Montant: 200 CAD\n"
                "💸 Adresse USDT (TRC20):\n"
                "<code>WALLET-USDT-ICI</code>\n\n"
                "❗️ IMPORTANT:\n"
                "1. Envoyez le montant exact\n"
                "2. Utilisez uniquement le réseau TRC20\n"
                "3. Envoyez une capture d'écran à @Z3RORISK\n"
            )
            btn_text = "📲 Copier l'adresse"
        else:
            text = (
                "💳 <b>USDT (TRC20) PAYMENT</b>\n\n"
                "💵 Amount: 200 CAD\n"
                "💸 USDT (TRC20) Address:\n"
                "<code>WALLET-USDT-ICI</code>\n\n"
                "❗️ IMPORTANT:\n"
                "1. Send exact amount\n"
                "2. Use TRC20 network only\n"
                "3. Send screenshot to @Z3RORISK\n"
            )
            btn_text = "📲 Copy Address"
        
        keyboard = [
            [InlineKeyboardButton(text=btn_text, callback_data="copy_usdt_address")],
            [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="buy_alpha")],
        ]
        await BotMessageManager.send_or_edit(
            event=callback,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()

@router.callback_query(F.data == "pay_btc")
async def callback_pay_btc(callback: types.CallbackQuery):
    """Show BTC payment info"""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.message.answer("Please send /start first!")
            return
        lang = user.language or "en"
        
        if lang == "fr":
            text = (
                "💳 <b>PAIEMENT BTC</b>\n\n"
                "💵 Montant: 200 CAD\n"
                "💸 Adresse BTC:\n"
                "<code>WALLET-BTC-ICI</code>\n\n"
                "❗️ IMPORTANT:\n"
                "1. Envoyez le montant exact\n"
                "2. Attendez 1 confirmation\n"
                "3. Envoyez une capture d'écran à @Z3RORISK\n"
            )
            btn_text = "📲 Copier l'adresse"
        else:
            text = (
                "💳 <b>BTC PAYMENT</b>\n\n"
                "💵 Amount: 200 CAD\n"
                "💸 BTC Address:\n"
                "<code>WALLET-BTC-ICI</code>\n\n"
                "❗️ IMPORTANT:\n"
                "1. Send exact amount\n"
                "2. Wait for 1 confirmation\n"
                "3. Send screenshot to @Z3RORISK\n"
            )
            btn_text = "📲 Copy Address"
        
        keyboard = [
            [InlineKeyboardButton(text=btn_text, callback_data="copy_btc_address")],
            [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="buy_alpha")],
        ]
        await BotMessageManager.send_or_edit(
            event=callback,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()

@router.callback_query(F.data == "copy_usdt_address")
async def callback_copy_usdt_address(callback: types.CallbackQuery):
    """Copy USDT address to clipboard"""
    await callback.answer("USDT address copied!", show_alert=True)

@router.callback_query(F.data == "copy_btc_address")
async def callback_copy_btc_address(callback: types.CallbackQuery):
    """Copy BTC address to clipboard"""
    await callback.answer("BTC address copied!", show_alert=True)

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    """Return to unified main menu"""
    # Confirmation system disabled on Telegram (web only)
    pending_count = 0
    has_pending = False
    
    # Don't call answer() here - BotMessageManager.send_or_edit() does it
    db = SessionLocal()
    try:
        user_tg = callback.from_user
        user = db.query(User).filter(User.telegram_id == user_tg.id).first()
        if not user:
            await callback.answer("Please send /menu", show_alert=True)
            return
        lang = user.language or "en"
        title = "Bienvenue" if lang == "fr" else "Welcome"
        desc = (
            "Risk0 Casino - Profite de bets garantis!"
            if lang == "fr" else
            "Risk0 Casino - Enjoy guaranteed bets!"
        )
        # Tier label - BETA for FREE users, ALPHA for PREMIUM, KING for lifetime
        if user.tier == TierLevel.FREE:
            tier_label = "BETA"
        elif user.is_admin:
            tier_label = "ALPHA"
        elif user.tier == TierLevel.PREMIUM and not user.subscription_end:
            tier_label = "KING"  # Lifetime = KING
        else:
            tier_label = "ALPHA" if user.tier == TierLevel.PREMIUM else "BETA"
        # Days left / Access line
        days_left_line = ""
        if user.tier == TierLevel.PREMIUM and not user.subscription_end:
            # Lifetime = KING
            if user.telegram_id == 8213628656:
                days_left_line = (f"👑 Accès: <b>KING OF ALPHA</b>\n" if lang == 'fr' else f"👑 Access: <b>KING OF ALPHA</b>\n")
            else:
                days_left_line = (f"👑 Accès: <b>KING</b>\n" if lang == 'fr' else f"👑 Access: <b>KING</b>\n")
        elif user.tier != TierLevel.FREE and user.subscription_end:
            days_left = user.days_until_expiry
            days_left_line = (f"⏰ Expire dans: {days_left} jours\n" if lang == 'fr' else f"⏰ Expires in: {days_left} days\n")
        # Calls stats
        def _core_tier_from_model(t):
            try:
                name = t.name.lower()
            except Exception:
                return CoreTierLevel.FREE
            return CoreTierLevel.PREMIUM if name == 'premium' else CoreTierLevel.FREE
        calls_count, potential_pct = get_today_stats_for_tier(_core_tier_from_model(user.tier))
        calls_label = ("Appels aujourd'hui" if lang == 'fr' else "Calls today")
        potential_label = ("Potentiel" if lang == 'fr' else "Potential")
        help_line2 = ('Tape /help pour voir toutes les commandes!' if lang == 'fr' else 'Type /help to see all commands!')
        tier_line2 = "" if user.tier == TierLevel.PREMIUM else f"🏆 <b>Tier: {tier_label}</b>\n"
        # FREE daily quota line (shown only to FREE users)
        quota_line2 = ""
        if user.tier == TierLevel.FREE:
            today_used = user.alerts_today if user.last_alert_date == date.today() else 0
            max_alerts = TierManager.get_features(_core_tier_from_model(user.tier)).get("max_alerts_per_day", 2)
            quota_line2 = (f"📣 {today_used}/{max_alerts} today\n" if lang != 'fr' else f"📣 {today_used}/{max_alerts} aujourd’hui\n")
        
        # Calculate real-time stats from UserBet
        # IMPORTANT: UserBet.user_id is telegram_id, NOT database user.id!
        total_bets_count = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0
        
        total_profit_calc = db.query(
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit))
        ).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0.0
        
        # Calculate total stake for ROI
        total_stake_calc2 = db.query(
            func.sum(UserBet.total_stake)
        ).filter(
            UserBet.user_id == user_tg.id
        ).scalar() or 0.0
        
        # Calculate ROI
        roi2 = (total_profit_calc / total_stake_calc2 * 100) if total_stake_calc2 > 0 else 0.0
        
        # Calculate current win streak
        recent_bets2 = db.query(UserBet).filter(
            UserBet.user_id == user_tg.id
        ).order_by(UserBet.created_at.desc()).limit(10).all()
        
        win_streak2 = 0
        for bet in recent_bets2:
            # Check if bet is a win (actual_profit if confirmed, else expected_profit for pending)
            profit = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
            if profit > 0:
                win_streak2 += 1
            else:
                break  # Stop at first loss
        
        # Determine performance badge
        badge2 = ""
        if roi2 > 30 or win_streak2 >= 5:
            badge2 = " 🔥 HOT STREAK"
        elif total_bets_count >= 10 and roi2 > 20:
            badge2 = " 💎 DIAMOND HANDS"
        elif total_profit_calc > 5000:
            badge2 = " 🚀 ROCKET"
        elif user.tier == TierLevel.PREMIUM and total_bets_count >= 50:
            badge2 = " 👑 KING"
        
        # For FREE users, show how many calls ALPHA gets (to drive upgrade)
        if user.tier == TierLevel.FREE:
            # Get ALPHA stats to show what they're missing
            alpha_calls, alpha_potential = get_today_stats_for_tier(CoreTierLevel.PREMIUM)
            # Get user's actual usage today
            today_used_menu = user.alerts_today if user.last_alert_date == date.today() else 0
            
            # Generate daily motivational example (changes every 24h based on date)
            import hashlib
            today_str = date.today().isoformat()
            seed = int(hashlib.md5(today_str.encode()).hexdigest()[:8], 16)
            
            # Randomize but keep realistic
            num_bets = (seed % 4) + 3  # 3-6 bets
            ev_pct = ((seed >> 8) % 6) + 5  # 5-10%
            bankroll = ((seed >> 16) % 40 + 10) * 100  # $1000-$5000
            profit = round(bankroll * (num_bets * ev_pct / 100), 2)
            
            if lang == 'fr':
                stats_line2 = f"💎 Alpha aujourd'hui: <b>{alpha_calls} calls</b>  •  📈 <b>{alpha_potential:.1f}% potential</b>\n"
                stats_line2 += f"🆓 Toi (BETA): <b>{today_used_menu}/5 calls aujourd'hui</b>\n\n"
                stats_line2 += f"💡 <i>Exemple: {num_bets} bets à {ev_pct}% EV avec ${bankroll} = <b>+${profit}</b> profit! ASSURÉ</i>\n\n"
            else:
                stats_line2 = f"💎 Alpha today: <b>{alpha_calls} calls</b>  •  📈 <b>{alpha_potential:.1f}% potential</b>\n"
                stats_line2 += f"🆓 You (BETA): <b>{today_used_menu}/5 calls today</b>\n\n"
                stats_line2 += f"💡 <i>Example: {num_bets} bets at {ev_pct}% EV with ${bankroll} = <b>+${profit}</b> profit! GUARANTEED</i>\n\n"
        else:
            # ALPHA: show their stats normally
            stats_line2 = f"📣 {calls_label}: <b>{calls_count}</b>\n📈 {potential_label}: <b>{potential_pct}%</b>\n\n"
        
        # If user has pending confirmations, show special confirmation menu
        if has_pending:
            # Get ALL pending bets (no date filtering)
            pending_bets = db.query(UserBet).filter(
                and_(
                    UserBet.user_id == user_tg.id,
                    UserBet.status == 'pending'
                )
            ).all()
            
            # Filter to only ready bets
            today = date.today()
            ready_bets = []
            for bet in pending_bets:
                if bet.match_date and bet.match_date < today:
                    ready_bets.append(bet)
                elif bet.match_date is None and bet.bet_date and bet.bet_date < today:
                    ready_bets.append(bet)
            
            # Build confirmation message
            if lang == 'fr':
                menu_text = f"📋 <b>CONFIRMATIONS EN ATTENTE</b>\n\n⚠️ <b>{len(ready_bets)} confirmation(s) nécessaire(s):</b>\n"
            else:
                menu_text = f"📋 <b>PENDING CONFIRMATIONS</b>\n\n⚠️ <b>{len(ready_bets)} confirmation(s) needed:</b>\n"
            
            # Show first 5 bets
            for bet in ready_bets[:5]:
                bet_emoji = "🎲" if bet.bet_type == 'middle' else "✅" if bet.bet_type == 'arbitrage' else "📈"
                match = bet.match_name or "Match"
                menu_text += f"• {bet_emoji} {match} (${bet.total_stake:.0f})\n"
            
            if len(ready_bets) > 5:
                menu_text += f"  ... {'et' if lang == 'fr' else 'and'} {len(ready_bets) - 5} {'autre(s)' if lang == 'fr' else 'more'}\n"
            
            menu_text += f"\n💡 {'Clique sur le bouton pour recevoir tous les questionnaires!' if lang == 'fr' else 'Click the button to receive all questionnaires!'}"
            
            # Only ONE button: send questionnaires
            btn_text = f"📨 {'Envoyer tous les questionnaires' if lang == 'fr' else 'Send all questionnaires'}"
            keyboard = [
                [InlineKeyboardButton(text=btn_text, callback_data="resend_all_questionnaires")]
            ]
        else:
            # Normal menu
            menu_text = (
                f"🎰 <b>{title} {user_tg.first_name}!{badge2}</b>\n\n"
                f"💰 {desc}\n\n"
                f"{tier_line2}"
                f"{quota_line2}{days_left_line}"
                f"💵 <b>Profit total: ${total_profit_calc:.2f}</b>\n"
                f"📊 <b>Bets placés: {total_bets_count}</b>\n"
                f"{stats_line2}"
                f"{help_line2}"
            )
            # Check bet_focus_mode
            bet_focus = getattr(user, 'bet_focus_mode', False)
            
            # Generate auth token for dashboard
            import base64, json, time as time_module
            dash_token = base64.b64encode(json.dumps({"telegramId": user.telegram_id, "username": user_tg.username or user_tg.first_name or str(user.telegram_id), "tier": user.tier.value if hasattr(user.tier, 'value') else str(user.tier), "ts": int(time_module.time())}, separators=(',', ':')).encode()).decode()
            dash_url = f"https://smartrisk0.xyz/dash?token={dash_token}"
            
            # Build menu keyboard
            keyboard = await build_menu_keyboard(user, lang, dash_url, bet_focus)
            # Admin button if user is admin (env or DB or role)
            # Import admin system helper
            from bot.admin_approval_system import is_any_admin
            
            # Check if user is admin (checks role column in DB)
            if is_any_admin(user_tg.id):
                admin_label = "🛠️ Admin" if lang == "fr" else "🛠️ Admin"
                keyboard.append([InlineKeyboardButton(text=admin_label, callback_data="open_admin")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await BotMessageManager.send_or_edit(
            event=callback,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "last_calls")
async def callback_last_calls(callback: types.CallbackQuery):
    """Premium-only submenu to view last calls by type."""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        if (not user) or user.tier != TierLevel.PREMIUM:
            title = "🔒 Réservé aux ALPHA" if lang == 'fr' else "🔒 Alpha Only"
            body = (
                "Active ALPHA pour voir les derniers appels par type."
                if lang == 'fr' else
                "Activate ALPHA to view last calls by type."
            )
            kb = [
                [InlineKeyboardButton(text=("🔥 Acheter ALPHA" if lang == 'fr' else "🔥 Buy ALPHA"), callback_data="show_tiers")],
                [InlineKeyboardButton(text=("◀️ Menu" if lang == 'fr' else "◀️ Menu"), callback_data="main_menu")],
            ]
            await BotMessageManager.send_or_edit(
                event=callback,
                text=f"{title}\n\n{body}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return

        # PREMIUM submenu - Using new Last Calls Pro system
        title = "🕒 Derniers Appels" if lang == 'fr' else "🕒 Last Calls"
        subtitle = ("Choisis une catégorie:\n\n✨ Nouveau: Pagination, tri par %, filtres casino!" if lang == 'fr' else "Choose a category:\n\n✨ New: Pagination, sort by %, casino filters!")
        kb = [
            [InlineKeyboardButton(text=("⚖️ Arbitrage" if lang == 'fr' else "⚖️ Arbitrage"), callback_data="lastcalls_arbitrage_page_1")],
            [InlineKeyboardButton(text=("🎯 Middle" if lang == 'fr' else "🎯 Middle"), callback_data="lastcalls_middle_page_1")],
            [InlineKeyboardButton(text=("💎 Good EV" if lang == 'fr' else "💎 Good EV"), callback_data="lastcalls_goodev_page_1")],
            [InlineKeyboardButton(text=("◀️ Menu" if lang == 'fr' else "◀️ Menu"), callback_data="main_menu")],
        ]
        await BotMessageManager.send_or_edit(
            event=callback,
            text=f"{title}\n\n{subtitle}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "last_calls_arbitrage")
async def callback_last_calls_arbitrage(callback: types.CallbackQuery):
    """Show last 10 arbitrage calls as clickable menu."""
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        # Get last arbitrage from DropEvent table, filtered by user's % preferences
        from models.drop_event import DropEvent
        user_min = user.min_arb_percent or 0.5
        user_max = user.max_arb_percent or 100.0
        
        # Get all recent drops and filter in Python (since arb_percentage can be in payload)
        all_drops = (
            db.query(DropEvent)
            .order_by(DropEvent.received_at.desc())
            .limit(50)  # Get more to filter down to 10 after filtering
            .all()
        )
        
        # Filter by user's percentage preference
        drops = []
        for d in all_drops:
            try:
                pct = d.arb_percentage or (d.payload or {}).get('arb_percentage') or 0
                if user_min <= pct <= user_max:
                    drops.append(d)
                    if len(drops) >= 10:
                        break
            except Exception:
                continue

        if not drops:
            msg = ("📈 Aucun arbitrage récent." if lang == 'fr' else "📈 No recent arbitrage.")
            kb = [
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")],
                [InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")],
            ]
            await BotMessageManager.send_or_edit(
                event=callback,
                text=msg,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return

        title = "📈 <b>Derniers ARBITRAGES</b>\n\nSélectionnez un call:" if lang == 'fr' else "📈 <b>Last ARBITRAGES</b>\n\nSelect a call:"
        
        # Build keyboard with buttons for each call
        kb = []
        for idx, d in enumerate(drops, start=1):
            try:
                match = (d.payload or {}).get('match') or d.match or 'N/A'
                pct = d.arb_percentage or (d.payload or {}).get('arb_percentage') or 0
                btn_text = f"{idx}. {pct:.2f}% • {match[:30]}"
            except Exception:
                btn_text = f"{idx}. {d.match[:30] if d.match else 'N/A'}"
            kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_arb_{d.id}")])
        
        # Navigation buttons
        kb.append([InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")])
        kb.append([InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")])

        await BotMessageManager.send_or_edit(
            event=callback,
            text=title,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("view_arb_"))
async def callback_view_arb_detail(callback: types.CallbackQuery):
    """Show detailed view of a specific arbitrage call."""
    await callback.answer()
    db = SessionLocal()
    try:
        drop_id = int(callback.data.split('_')[2])
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        from models.drop_event import DropEvent
        drop = db.query(DropEvent).filter(DropEvent.id == drop_id).first()
        
        if not drop or not drop.payload:
            msg = ("❌ Call introuvable." if lang == 'fr' else "❌ Call not found.")
            await callback.answer(msg, show_alert=True)
            return
        
        # Format like original arbitrage alert
        arb_data = drop.payload
        from core.calculator import ArbitrageCalculator
        from core.tiers import TierManager
        from core.casinos import get_casino_logo, get_casino_referral_link
        from utils.odds_api_links import get_links_for_drop, get_fallback_url
        
        calculator = ArbitrageCalculator()
        bankroll = user.default_bankroll
        odds_list = [outcome['odds'] for outcome in arb_data.get('outcomes', [])]
        safe_calc = calculator.calculate_safe_stakes(bankroll, odds_list)
        
        if lang == 'fr':
            title_line = f"📈 <b>ARBITRAGE - {arb_data.get('arb_percentage', 0)}%</b>\n\n"
            cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
            profit_line = f"✅ <b>Profit Garanti: ${safe_calc['profit']:.2f}</b>\n\n"
            stake_label = "Miser"
        else:
            title_line = f"📈 <b>ARBITRAGE - {arb_data.get('arb_percentage', 0)}%</b>\n\n"
            cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
            profit_line = f"✅ <b>Guaranteed Profit: ${safe_calc['profit']:.2f}</b>\n\n"
            stake_label = "Stake"
        
        message_text = (
            title_line
            + f"🏟️ <b>{arb_data.get('match', 'N/A')}</b>\n"
            + f"⚽ {arb_data.get('league', 'N/A')} - {arb_data.get('market', 'N/A')}\n\n"
            + cashh_line
            + profit_line
        )
        
        for i, outcome_data in enumerate(arb_data.get('outcomes', [])):
            logo = get_casino_logo(outcome_data.get('casino', ''))
            odds = outcome_data.get('odds', 0)
            odds_str = f"+{odds}" if odds > 0 else str(odds)
            stake = safe_calc['stakes'][i]
            return_amount = safe_calc['returns'][i]
            message_text += f"{logo} <b>[{outcome_data.get('casino', 'N/A')}]</b> {outcome_data.get('outcome', 'N/A')}\n💵 {stake_label}: ${stake:.2f} ({odds_str}) → ${return_amount:.2f}\n\n"
        
        # Build keyboard with interactive buttons
        kb = []
        
        # Casino links (row 1) - always show with deep/ref/fallback
        features = TierManager.get_features(user.tier)
        casino_buttons = []
        links = get_links_for_drop(arb_data)
        for outcome_data in arb_data.get('outcomes', []):
            casino_name = outcome_data.get('casino', '')
            logo = get_casino_logo(casino_name)
            link = links.get(casino_name)
            if not link:
                link = get_casino_referral_link(casino_name)
            if not link:
                link = get_fallback_url(casino_name)
            if link:
                casino_buttons.append(
                    InlineKeyboardButton(text=f"{logo} {casino_name} ↗", url=link)
                )
        if casino_buttons:
            kb.append(casino_buttons)
        
        # Row 2: I BET + Calculator + Change CASHH
        total_stake = bankroll
        expected_profit = safe_calc.get('profit', 0)
        i_bet_text = ("💰 I BET" if lang == 'en' else "💰 JE PARIE")
        calc_text = ("🧮 Calculator" if lang == 'en' else "🧮 Calculateur")
        cashh_text = ("💰 Change CASHH" if lang == 'en' else "💰 Changer CASHH")
        # Use per-call change cashh like live alerts (tokenized in main_new via chg_cashh_)
        eid_for_cashh = arb_data.get('event_id', drop.event_id)
        row2 = [
            InlineKeyboardButton(
                text=i_bet_text,
                callback_data=f"i_bet_{drop.id}_{total_stake}_{expected_profit}"
            )
        ]
        # Always show calculator like live
        row2.append(
            InlineKeyboardButton(
                text=calc_text,
                callback_data=f"calc_{arb_data.get('event_id', drop.event_id)}|menu"
            )
        )
        row2.append(
            InlineKeyboardButton(
                text=cashh_text,
                callback_data=f"chg_cashhA_{drop.id}"
            )
        )
        kb.append(row2)
        
        # Row 3: Last Calls only
        last_calls_text = ("🕒 Last Calls" if lang != 'fr' else "🕒 Derniers Calls")
        kb.append([InlineKeyboardButton(text=last_calls_text, callback_data="last_calls")])
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("cashh_custA_"))
async def callback_custom_amount_last_arb(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        drop_id = int(callback.data.split('_')[2])
    except Exception:
        return
    await state.set_state(LastArbCashh.awaiting_amount)
    await state.update_data(drop_id=drop_id, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await callback.message.answer("💰 Enter a custom amount ($):\nEx: 350")


@router.message(LastArbCashh.awaiting_amount)
async def handle_custom_amount_last_arb(message: types.Message, state: FSMContext):
    txt = (message.text or "").strip().replace('$','').replace(',','')
    try:
        amount = float(txt)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Invalid amount. Eg: 350")
        return
    data = await state.get_data()
    drop_id = int(data.get('drop_id'))
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    db = SessionLocal()
    try:
        from models.drop_event import DropEvent
        drop = db.query(DropEvent).filter(DropEvent.id == drop_id).first()
        if not drop or not drop.payload:
            await message.answer("❌ Call not found")
            await state.clear()
            return
        arb_data = drop.payload
        from core.calculator import ArbitrageCalculator
        from core.casinos import get_casino_logo, get_casino_referral_link
        from utils.odds_api_links import get_links_for_drop, get_fallback_url
        odds_list = [int(out.get('odds', 0)) for out in arb_data.get('outcomes', [])]
        safe_calc = ArbitrageCalculator.calculate_safe_stakes(amount, odds_list)
        # Build message
        title_line = f"📈 <b>ARBITRAGE - {arb_data.get('arb_percentage', 0)}%</b>\n\n"
        cashh_line = f"💰 <b>CASHH: ${amount}</b>\n"
        profit_line = f"✅ <b>Guaranteed Profit: ${safe_calc['profit']:.2f}</b>\n\n"
        stake_label = "Stake"
        message_text = (
            title_line
            + f"🏟️ <b>{arb_data.get('match', 'N/A')}</b>\n"
            + f"⚽ {arb_data.get('league', 'N/A')} - {arb_data.get('market', 'N/A')}\n\n"
            + cashh_line
            + profit_line
        )
        for i, outcome_data in enumerate(arb_data.get('outcomes', [])):
            logo = get_casino_logo(outcome_data.get('casino', ''))
            odds = outcome_data.get('odds', 0)
            odds_str = f"+{odds}" if int(odds) > 0 else str(odds)
            stake = safe_calc['stakes'][i]
            return_amount = safe_calc['returns'][i]
            message_text += f"{logo} <b>[{outcome_data.get('casino', 'N/A')}]</b> {outcome_data.get('outcome', 'N/A')}\n💵 {stake_label}: ${stake:.2f} ({odds_str}) → ${return_amount:.2f}\n\n"
        # Keyboard
        kb = []
        casino_buttons = []
        links = get_links_for_drop(arb_data)
        for outcome_data in arb_data.get('outcomes', []):
            casino_name = outcome_data.get('casino', '')
            logo = get_casino_logo(casino_name)
            link = links.get(casino_name) or get_casino_referral_link(casino_name) or get_fallback_url(casino_name)
            if link:
                casino_buttons.append(InlineKeyboardButton(text=f"{logo} {casino_name} ↗", url=link))
        if casino_buttons:
            kb.append(casino_buttons)
        calc_text = "🧮 Calculator"
        kb.append([
            InlineKeyboardButton(text="💰 I BET", callback_data=f"i_bet_{drop.id}_{amount}_{safe_calc.get('profit',0)}"),
            InlineKeyboardButton(text=calc_text, callback_data=f"calc_{arb_data.get('event_id', drop.event_id)}|menu"),
            InlineKeyboardButton(text="💰 Change CASHH", callback_data=f"chg_cashhA_{drop.id}")
        ])
        last_calls_text = "🕒 Last Calls"
        kb.append([InlineKeyboardButton(text=last_calls_text, callback_data="last_calls")])
        try:
            await message.bot.edit_message_text(
                message_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
            )
        except Exception:
            await message.answer(message_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    finally:
        db.close()
    await state.clear()


@router.callback_query(F.data.startswith("chg_cashhA_"))
async def callback_change_cashh_last_arb(callback: types.CallbackQuery):
    """Local Change CASHH menu for last-calls arbitrage detail."""
    await callback.answer()
    db = SessionLocal()
    try:
        drop_id = int(callback.data.split('_')[1])
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        from models.drop_event import DropEvent
        drop = db.query(DropEvent).filter(DropEvent.id == drop_id).first()
        if not drop or not drop.payload:
            await callback.answer("❌ Call not found" if lang!='fr' else "❌ Call introuvable", show_alert=True)
            return
        amounts = [100, 200, 300, 500, 1000]
        title = "💰 Changer CASHH (local)" if lang=='fr' else "💰 Change CASHH (local)"
        kb = [[InlineKeyboardButton(text=f"${a}", callback_data=f"acbA_{drop_id}_{a}")] for a in amounts]
        kb.append([InlineKeyboardButton(text=("✏️ Montant personnalisé" if lang=='fr' else "✏️ Custom amount"), callback_data=f"cashh_custA_{drop_id}")])
        kb.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data=f"view_arb_{drop_id}")])
        await BotMessageManager.send_or_edit(
            event=callback,
            text=title,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("acbA_"))
async def callback_quick_amount_last_arb(callback: types.CallbackQuery):
    """Apply selected amount to recalc and re-render detail view (local)."""
    await callback.answer()
    db = SessionLocal()
    try:
        _, drop_id, amt = callback.data.split('_')
        drop_id = int(drop_id)
        amount = float(amt)
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        from models.drop_event import DropEvent
        drop = db.query(DropEvent).filter(DropEvent.id == drop_id).first()
        if not drop or not drop.payload:
            await callback.answer("❌ Call not found" if lang!='fr' else "❌ Call introuvable", show_alert=True)
            return
        arb_data = drop.payload
        from core.calculator import ArbitrageCalculator
        from core.casinos import get_casino_logo, get_casino_referral_link
        from utils.odds_api_links import get_links_for_drop, get_fallback_url
        odds_list = [int(out.get('odds', 0)) for out in arb_data.get('outcomes', [])]
        safe_calc = ArbitrageCalculator.calculate_safe_stakes(amount, odds_list)
        # Build message
        if lang == 'fr':
            title_line = f"📈 <b>ARBITRAGE - {arb_data.get('arb_percentage', 0)}%</b>\n\n"
            cashh_line = f"💰 <b>CASHH: ${amount}</b>\n"
            profit_line = f"✅ <b>Profit Garanti: ${safe_calc['profit']:.2f}</b>\n\n"
            stake_label = "Miser"
        else:
            title_line = f"📈 <b>ARBITRAGE - {arb_data.get('arb_percentage', 0)}%</b>\n\n"
            cashh_line = f"💰 <b>CASHH: ${amount}</b>\n"
            profit_line = f"✅ <b>Guaranteed Profit: ${safe_calc['profit']:.2f}</b>\n\n"
            stake_label = "Stake"
        message_text = (
            title_line
            + f"🏟️ <b>{arb_data.get('match', 'N/A')}</b>\n"
            + f"⚽ {arb_data.get('league', 'N/A')} - {arb_data.get('market', 'N/A')}\n\n"
            + cashh_line
            + profit_line
        )
        for i, outcome_data in enumerate(arb_data.get('outcomes', [])):
            logo = get_casino_logo(outcome_data.get('casino', ''))
            odds = outcome_data.get('odds', 0)
            odds_str = f"+{odds}" if odds > 0 else str(odds)
            stake = safe_calc['stakes'][i]
            return_amount = safe_calc['returns'][i]
            message_text += f"{logo} <b>[{outcome_data.get('casino', 'N/A')}]</b> {outcome_data.get('outcome', 'N/A')}\n💵 {stake_label}: ${stake:.2f} ({odds_str}) → ${return_amount:.2f}\n\n"
        # Keyboard rows
        kb = []
        casino_buttons = []
        links = get_links_for_drop(arb_data)
        for outcome_data in arb_data.get('outcomes', []):
            casino_name = outcome_data.get('casino', '')
            logo = get_casino_logo(casino_name)
            link = links.get(casino_name) or get_casino_referral_link(casino_name) or get_fallback_url(casino_name)
            if link:
                casino_buttons.append(InlineKeyboardButton(text=f"{logo} {casino_name} ↗", url=link))
        if casino_buttons:
            kb.append(casino_buttons)
        # Row 2
        i_bet_text = ("💰 I BET" if lang=='en' else "💰 JE PARIE")
        calc_text = ("🧮 Calculator" if lang=='en' else "🧮 Calculateur")
        kb.append([
            InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{drop.id}_{amount}_{safe_calc.get('profit',0)}"),
            InlineKeyboardButton(text=calc_text, callback_data=f"calc_{arb_data.get('event_id', drop.event_id)}|menu"),
            InlineKeyboardButton(text=("💰 Change CASHH" if lang!='fr' else "💰 Changer CASHH"), callback_data=f"chg_cashhA_{drop.id}")
        ])
        # Row 3
        last_calls_text = ("🕒 Last Calls" if lang != 'fr' else "🕒 Derniers Calls")
        kb.append([InlineKeyboardButton(text=last_calls_text, callback_data="last_calls")])
        await BotMessageManager.send_or_edit(
            event=callback,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "last_calls_middle")
async def callback_last_calls_middle(callback: types.CallbackQuery):
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        # Get last Middles and filter by user's % preferences
        from utils.last_calls_store import get_recent_middle
        user_min = user.min_middle_percent or 0.5
        user_max = user.max_middle_percent or 100.0
        
        all_items = get_recent_middle(50)  # Get more to filter
        items = []
        for it in all_items:
            try:
                pct = float(it.get('middle_percent', 0))
                if user_min <= pct <= user_max:
                    items.append(it)
                    if len(items) >= 10:
                        break
            except Exception:
                continue

        if not items:
            msg = ("🎯 Aucun middle récent." if lang == 'fr' else "🎯 No recent middle.")
            kb = [
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")],
                [InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")],
            ]
            await BotMessageManager.send_or_edit(
                event=callback,
                text=msg,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return

        title = "🎯 <b>Derniers MIDDLE</b>\n\nSélectionnez un call:" if lang == 'fr' else "🎯 <b>Last MIDDLE</b>\n\nSelect a call:"
        
        # Build keyboard with buttons for each call
        kb = []
        for idx, it in enumerate(items, start=1):
            try:
                pct = float(it.get('middle_percent', 0))
            except Exception:
                pct = 0
            t1 = it.get('team1', 'N/A')
            t2 = it.get('team2', 'N/A')
            btn_text = f"{idx}. {pct:.2f}% • {t1} vs {t2}"[:60]
            kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_middle_{idx-1}")])
        
        # Navigation buttons
        kb.append([InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")])
        kb.append([InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")])

        await BotMessageManager.send_or_edit(
            event=callback,
            text=title,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("view_middle_"))
async def callback_view_middle_detail(callback: types.CallbackQuery):
    """Show detailed view of a specific middle call."""
    await callback.answer()
    db = SessionLocal()
    try:
        idx = int(callback.data.split('_')[2])
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        from utils.last_calls_store import get_recent_middle
        items = get_recent_middle(10)
        
        if idx >= len(items):
            msg = ("❌ Call introuvable." if lang == 'fr' else "❌ Call not found.")
            await callback.answer(msg, show_alert=True)
            return
        
        last_middle = items[idx]
        
        # Format Middle message
        from utils.oddsjam_formatters import format_middle_message
        from utils.oddsjam_parser import calculate_middle_stakes
        from core.casinos import get_casino_logo
        from utils.odds_api_links import get_fallback_url
        
        bankroll = user.default_bankroll
        calc = calculate_middle_stakes(
            last_middle['side_a']['odds'],
            last_middle['side_b']['odds'],
            bankroll
        )
        
        # Recommended total stake (2% of bankroll)
        rec_stake = round(bankroll * 0.02, 2)
        rec_calc = calculate_middle_stakes(
            last_middle['side_a']['odds'],
            last_middle['side_b']['odds'],
            rec_stake
        )
        
        message_text = format_middle_message(last_middle, calc, bankroll, lang)
        
        # Build keyboard with interactive buttons
        kb = []
        
        # Bookmaker links (both sides) row 1
        bookmaker_a_url = get_fallback_url(last_middle['side_a']['bookmaker'])
        bookmaker_b_url = get_fallback_url(last_middle['side_b']['bookmaker'])
        logo_a = get_casino_logo(last_middle['side_a']['bookmaker'])
        logo_b = get_casino_logo(last_middle['side_b']['bookmaker'])
        
        kb.append([
            InlineKeyboardButton(
                text=f"{logo_a} {last_middle['side_a']['bookmaker']} ↗",
                url=bookmaker_a_url
            ),
            InlineKeyboardButton(
                text=f"{logo_b} {last_middle['side_b']['bookmaker']} ↗",
                url=bookmaker_b_url
            )
        ])
        
        # Row 2: I BET (Recommended + My CASHH) + Settings
        kb.append([
            InlineKeyboardButton(
                text=("💡 Recommended" if lang == 'en' else "💡 Recommandé") + f" (${rec_calc['total_stake']:.2f})",
                callback_data=f"middle_bet_{rec_calc['total_stake']:.2f}_{rec_calc['middle_profit']:.2f}"
            ),
            InlineKeyboardButton(
                text=("💵 My CASHH" if lang == 'en' else "💵 Mon CASHH") + f" (${calc['total_stake']:.2f})",
                callback_data=f"middle_bet_{calc['total_stake']:.2f}_{calc['middle_profit']:.2f}"
            ),
            InlineKeyboardButton(
                text=("⚙️ Settings" if lang == 'en' else "⚙️ Paramètres"),
                callback_data="settings_main"
            )
        ])
        
        # Row 3: Last Calls only
        last_calls_text = ("🕒 Last Calls" if lang != 'fr' else "🕒 Derniers Calls")
        kb.append([InlineKeyboardButton(text=last_calls_text, callback_data="last_calls")])
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "last_calls_good_ev")
async def callback_last_calls_good_ev(callback: types.CallbackQuery):
    await callback.answer()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        # Get last Good EVs and filter by user's % preferences
        from utils.last_calls_store import get_recent_good_odds
        user_min = user.min_good_ev_percent or 0.5
        user_max = user.max_good_ev_percent or 100.0
        
        all_items = get_recent_good_odds(50)  # Get more to filter
        items = []
        for it in all_items:
            try:
                pct = float(it.get('ev_percent', 0))
                if user_min <= pct <= user_max:
                    items.append(it)
                    if len(items) >= 10:
                        break
            except Exception:
                continue

        if not items:
            msg = ("💎 Aucun Good EV récent." if lang == 'fr' else "💎 No recent Good EV.")
            kb = [
                [InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")],
                [InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")],
            ]
            await BotMessageManager.send_or_edit(
                event=callback,
                text=msg,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                parse_mode=ParseMode.HTML,
            )
            return

        title = "💎 <b>Derniers GOOD EV</b>\n\nSélectionnez un call:" if lang == 'fr' else "💎 <b>Last GOOD EV</b>\n\nSelect a call:"
        
        # Build keyboard with buttons for each call
        kb = []
        for idx, it in enumerate(items, start=1):
            try:
                pct = float(it.get('ev_percent', 0))
            except Exception:
                pct = 0
            t1 = it.get('team1', 'N/A')
            t2 = it.get('team2', 'N/A')
            btn_text = f"{idx}. {pct:.2f}% • {t1} vs {t2}"[:60]
            kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_good_ev_{idx-1}")])
        
        # Navigation buttons
        kb.append([InlineKeyboardButton(text=("◀️ Retour" if lang == 'fr' else "◀️ Back"), callback_data="last_calls")])
        kb.append([InlineKeyboardButton(text=("🏠 Menu" if lang == 'fr' else "🏠 Menu"), callback_data="main_menu")])

        await BotMessageManager.send_or_edit(
            event=callback,
            text=title,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("view_good_ev_"))
async def callback_view_good_ev_detail(callback: types.CallbackQuery):
    """Show detailed view of a specific Good EV call."""
    await callback.answer()
    db = SessionLocal()
    try:
        idx = int(callback.data.split('_')[3])
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else "en") or "en"
        
        from utils.last_calls_store import get_recent_good_odds
        items = get_recent_good_odds(10)
        
        if idx >= len(items):
            msg = ("❌ Call introuvable." if lang == 'fr' else "❌ Call not found.")
            await callback.answer(msg, show_alert=True)
            return
        
        last_good_odds = items[idx]
        
        # Format Good Odds message
        from utils.oddsjam_formatters import format_good_odds_message
        from utils.ev_quality import get_user_profile
        from core.casinos import get_casino_logo
        from utils.odds_api_links import get_fallback_url
        
        bankroll = user.default_bankroll
        total_bets = user.total_bets or 0
        user_profile = get_user_profile(total_bets)
        
        message_text = format_good_odds_message(last_good_odds, bankroll, lang, user_profile, total_bets)
        
        # Build keyboard with interactive buttons
        kb = []
        
        # Bookmaker link (row 1)
        bookmaker_url = get_fallback_url(last_good_odds.get('bookmaker', ''))
        logo = get_casino_logo(last_good_odds.get('bookmaker', ''))
        kb.append([
            InlineKeyboardButton(
                text=f"{logo} {last_good_odds.get('bookmaker', 'N/A')} ↗",
                url=bookmaker_url
            )
        ])
        
        # I BET buttons (Recommended + My CASHH)
        try:
            ev_percent = float(last_good_odds.get('ev_percent', 0))
        except Exception:
            ev_percent = 0
        
        # Recommended stake
        if ev_percent >= 18.0:
            rec_ratio = 0.05
        elif ev_percent >= 12.0:
            rec_ratio = 0.035
        elif ev_percent >= 8.0:
            rec_ratio = 0.02
        else:
            rec_ratio = 0.01
        rec_stake = round(bankroll * rec_ratio, 2)
        my_stake = round(bankroll, 2)
        rec_ev_profit = round(rec_stake * (ev_percent/100.0), 2)
        my_ev_profit = round(my_stake * (ev_percent/100.0), 2)
        
        # Row 2: I BET Recommended + My CASHH + Settings
        kb.append([
            InlineKeyboardButton(
                text=(f"💡 Recommended (${rec_stake:.2f})" if lang == 'en' else f"💡 Recommandé (${rec_stake:.2f})"),
                callback_data=f"good_ev_bet_{rec_stake:.2f}_{rec_ev_profit:.2f}"
            ),
            InlineKeyboardButton(
                text=(f"💵 My CASHH (${my_stake:.2f})" if lang == 'en' else f"💵 Mon CASHH (${my_stake:.2f})"),
                callback_data=f"good_ev_bet_{my_stake:.2f}_{my_ev_profit:.2f}"
            ),
            InlineKeyboardButton(
                text=("⚙️ Settings" if lang == 'en' else "⚙️ Paramètres"),
                callback_data="settings_main"
            )
        ])
        
        # Row 3: Last Calls only
        last_calls_text = ("🕒 Last Calls" if lang != 'fr' else "🕒 Derniers Calls")
        kb.append([InlineKeyboardButton(text=last_calls_text, callback_data="last_calls")])
        
        await BotMessageManager.send_or_edit(
            event=callback,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML,
        )
    finally:
        db.close()


@router.callback_query(F.data == "change_bankroll")
async def callback_change_bankroll(callback: types.CallbackQuery, state: FSMContext):
    """Start bankroll change flow"""
    await callback.answer()
    # Localize prompt
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else 'en') or 'en'
    finally:
        db.close()
    if lang == 'en':
        prompt = "💰 Enter your new default CASHH ($):\nExample: 500"
    else:
        prompt = "💰 Entre ton nouveau CASHH par défaut (en $):\nExemple: 500"
    await callback.message.answer(prompt)
    await state.set_state(UserStates.awaiting_bankroll)


@router.message(UserStates.awaiting_bankroll)
async def process_bankroll_change(message: types.Message, state: FSMContext):
    """Process bankroll change"""
    try:
        bankroll = float(message.text.replace(",", ".").replace("$", ""))
        if bankroll <= 0:
            raise ValueError
        
        # Update in database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
            if user:
                user.default_bankroll = bankroll
                db.commit()
                
                lang = (user.language if user else 'en') or 'en'
                txt = (
                    f"✅ Default CASHH updated: <b>${bankroll:.2f}</b>"
                    if lang == 'en' else
                    f"✅ CASHH mis à jour: <b>${bankroll:.2f}</b>"
                )
                await message.answer(txt, parse_mode=ParseMode.HTML)
        finally:
            db.close()
        
        await state.clear()
    
    except ValueError:
        await message.answer(
            "⚠️ Invalid amount. Enter a positive number (e.g., 500)"
        )


@router.callback_query(F.data == "change_risk")
async def callback_change_risk(callback: types.CallbackQuery, state: FSMContext):
    """Start risk percentage change flow"""
    await callback.answer()
    # Localize prompt
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        lang = (user.language if user else 'en') or 'en'
    finally:
        db.close()
    if lang == 'en':
        prompt = "🎯 Enter your new default risk percentage (%):\nExample: 5 (for 5%)"
    else:
        prompt = "🎯 Entre ton nouveau pourcentage de risque par défaut (%):\nExemple: 5 (pour 5%)"
    await callback.message.answer(prompt)
    await state.set_state(UserStates.awaiting_risk_percentage)


@router.message(UserStates.awaiting_risk_percentage)
async def process_risk_change(message: types.Message, state: FSMContext):
    """Process risk percentage change"""
    try:
        risk = float(message.text.replace(",", ".").replace("%", ""))
        if risk <= 0 or risk > 100:
            raise ValueError
        
        # Update in database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
            if user:
                user.default_risk_percentage = risk
                db.commit()
                
                lang = (user.language if user else 'en') or 'en'
                txt = (
                    f"✅ Default risk updated: <b>{risk}%</b>"
                    if lang == 'en' else
                    f"✅ Risk mis à jour: <b>{risk}%</b>"
                )
                await message.answer(txt, parse_mode=ParseMode.HTML)
        finally:
            db.close()
        
        await state.clear()
    
    except ValueError:
        await message.answer(
            "⚠️ Invalid percentage. Enter a number between 0 and 100 (e.g., 5)"
        )


@router.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: types.CallbackQuery):
    """Toggle notifications on/off"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.notifications_enabled = not user.notifications_enabled
            db.commit()
            
            lang = user.language or "en"
            status = ("✅ Enabled" if user.notifications_enabled else "❌ Disabled") if lang == 'en' else ("✅ Activées" if user.notifications_enabled else "❌ Désactivées")
            await callback.answer((f"Notifications: {status}" if lang == 'en' else f"Notifications: {status}"), show_alert=True)
            
            # Refresh settings page (edit in place)
            await callback_settings(callback)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_good_odds")
async def callback_toggle_good_odds(callback: types.CallbackQuery):
    """Toggle Good Odds alerts on/off (PREMIUM only)"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user and user.tier == TierLevel.PREMIUM:
            user.enable_good_odds = not user.enable_good_odds
            db.commit()
            
            lang = user.language or "en"
            status = ("✅ ON" if user.enable_good_odds else "❌ OFF")
            await callback.answer((f"Good Odds Alerts: {status}" if lang == 'en' else f"Good Odds Alerts: {status}"), show_alert=True)
            
            # Refresh settings page
            await callback_settings(callback)
        else:
            await callback.answer("❌ PREMIUM only" if (user and user.language == 'en') else "❌ PREMIUM seulement", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_middle")
async def callback_toggle_middle(callback: types.CallbackQuery):
    """Toggle Middle opportunities on/off (PREMIUM only)"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user and user.tier == TierLevel.PREMIUM:
            user.enable_middle = not user.enable_middle
            db.commit()
            
            lang = user.language or "en"
            status = ("✅ ON" if user.enable_middle else "❌ OFF")
            await callback.answer((f"Middle Opportunities: {status}" if lang == 'en' else f"Middle Opportunities: {status}"), show_alert=True)
            
            # Refresh settings page
            await callback_settings(callback)
        else:
            await callback.answer("❌ PREMIUM only" if (user and user.language == 'en') else "❌ PREMIUM seulement", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_bet_focus")
async def callback_toggle_bet_focus(callback: types.CallbackQuery):
    """Toggle Bet Focus Mode on/off (PREMIUM only)"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user and user.tier == TierLevel.PREMIUM:
            # Toggle bet_focus_mode
            current_state = getattr(user, 'bet_focus_mode', False)
            user.bet_focus_mode = not current_state
            db.commit()
            
            lang = user.language or 'en'
            status = "✅ ON" if user.bet_focus_mode else "❌ OFF"
            await callback.answer((f"Bet Focus Mode: {status}" if lang == 'en' else f"Bet Focus Mode: {status}"), show_alert=True)
            
            # Refresh settings page
            await callback_settings(callback)
        else:
            await callback.answer("❌ PREMIUM only" if (user and user.language == 'en') else "❌ PREMIUM seulement", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_match_today")
async def callback_toggle_match_today(callback: types.CallbackQuery):
    """Toggle Match Today filter - only receive alerts for matches starting TODAY"""
    await callback.answer()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            # Toggle match_today_only
            current_state = getattr(user, 'match_today_only', False)
            user.match_today_only = not current_state
            db.commit()
            
            lang = user.language or 'en'
            status = "✅ ON" if user.match_today_only else "❌ OFF"
            if lang == 'fr':
                message = f"Match Today: {status}\n\nVous recevrez {'seulement' if user.match_today_only else 'tous'} les calls dont le match commence aujourd'hui."
            else:
                message = f"Match Today: {status}\n\nYou will receive {'only' if user.match_today_only else 'all'} calls where the match starts today."
            
            await callback.answer(message, show_alert=True)
            
            # Refresh settings page
            await callback_settings(callback)
    finally:
        db.close()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: types.CallbackQuery):
    """Cancel action"""
    await callback.answer("Annulé")
    await callback.message.delete()
