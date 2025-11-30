"""
ArbitrageBot Canada - Main Entry Point
Integrates existing bot with new tier/referral system
"""
import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI, Request, Header
import uvicorn
import re
import secrets
import logging

# Import handlers
from bot import handlers, admin_handlers, learn_handlers, casino_handlers, language_handlers, bet_handlers, bet_handlers_ev_middle, middle_handlers, add_bet_flow, percent_filters, stake_rounding_handlers, casino_filter_handlers, bet_details_pro, last_calls_pro, learn_guide_pro, debug_command, simulation_handler, middle_outcome_tracker, intelligent_questionnaire, pending_confirmations, parlay_preferences_handler, force_commands_handler, feedback_vouch_handler, admin_feedback_menu
from bot import daily_confirmation, web_auth_handler
from bot.auto_confirm_middleware import AutoconfirmMiddleware
from bot.nowpayments_handler import NOWPaymentsManager
from bot.commands_setup import setup_bot_commands, setup_menu_button

import hashlib

# Import core modules
from core.parser import parse_arbitrage_alert
from core.calculator import ArbitrageCalculator
from core.tiers import TierManager, TierLevel
from core.referrals import ReferralManager
from core.casinos import get_casino, get_casino_logo, get_casino_referral_link

# Import existing utils
from config import BOT_TOKEN, ADMIN_CHAT_ID
from utils.parser_ai import extract_from_email
from utils.image_card import generate_card
from utils.drops_stats import get_today_stats_for_tier, record_drop
from realtime_parlay_generator import on_drop_received
from utils.odds_api_links import get_links_for_drop, get_fallback_url
from utils.odds_enricher import enrich_alert_with_api
from utils.last_calls_store import push_good_odds, push_middle
from utils.call_processor import (
    BettingCall, Side, EventDatetime, ArbAnalysis,
    process_call_from_drop,
    enrich_call_with_odds_api,
    analyze_arbitrage_two_way,
    format_call_message,
    should_send_call
)

# Database
from database import SessionLocal, init_db
from models.user import User
from models.drop_event import DropEvent

# In-memory stores
DROPS = {}  # Store for drops
PENDING_CALLS = {}  # Store for BettingCalls awaiting verification
# Map drop_event_id (DB id) -> BettingCall.call_id for per-call CASHH changes
CALL_IDS_BY_DROP_ID: dict[str, str] = {}
PENDING_CALLS_FILE = "pending_calls.pkl"

# Deduplication store: hash -> timestamp
SENT_CALLS_CACHE = {}  # {call_hash: timestamp}
CACHE_EXPIRY_MINUTES = 10  # Keep hashes for 10 minutes

# Initialize
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()
calc_router = Router()

# CORS for web dashboard
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Web Dashboard API
from api.web_api import router as web_router
app.include_router(web_router)

# Early logger initialization (used by load_pending_calls)
logger = logging.getLogger(__name__)

# ===== CASINO & SPORT FILTER HELPERS =====
def user_passes_casino_filter(user, casinos: list) -> bool:
    """
    Check if user's selected_casinos filter allows these casinos.
    Returns True if user should receive alert, False if filtered out.
    If user has no filter (null/empty), allow all casinos.
    """
    import json
    try:
        selected_casinos_str = user.selected_casinos
        if not selected_casinos_str:
            return True  # No filter = allow all
        
        selected = json.loads(selected_casinos_str)
        if not selected:
            return True  # Empty list = allow all
        
        # Normalize casino names for comparison
        selected_lower = [c.lower().strip() for c in selected]
        casinos_lower = [c.lower().strip() for c in casinos if c]
        
        # Check if ANY casino from alert is in user's selected list
        for casino in casinos_lower:
            if casino in selected_lower:
                return True
        
        logger.debug(f"🚫 Casino filter blocked: casinos={casinos}, selected={selected}")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Casino filter error: {e}")
        return True  # On error, allow through

def user_passes_sport_filter(user, sport: str) -> bool:
    """
    Check if user's selected_sports filter allows this sport.
    Returns True if user should receive alert, False if filtered out.
    If user has no filter (null/empty), allow all sports.
    """
    import json
    try:
        selected_sports_str = user.selected_sports
        if not selected_sports_str:
            return True  # No filter = allow all
        
        selected = json.loads(selected_sports_str)
        if not selected:
            return True  # Empty list = allow all
        
        # Normalize sport name
        sport_lower = (sport or "").lower().strip()
        selected_lower = [s.lower().strip() for s in selected]
        
        # Check if sport is in user's selected list
        if sport_lower in selected_lower:
            return True
        
        # Also check partial matches (e.g., "nba" matches "basketball")
        sport_mappings = {
            'nba': 'basketball', 'ncaa basketball': 'basketball', 'ncaab': 'basketball',
            'nfl': 'football', 'ncaa football': 'football', 'ncaaf': 'football',
            'nhl': 'hockey', 'ice hockey': 'hockey',
            'mlb': 'baseball',
            'mls': 'soccer', 'la liga': 'soccer', 'premier league': 'soccer', 'serie a': 'soccer', 'bundesliga': 'soccer', 'ligue 1': 'soccer',
            'ufc': 'mma', 'mixed martial arts': 'mma',
            'atp': 'tennis', 'wta': 'tennis',
        }
        
        # Try mapping
        for key, mapped in sport_mappings.items():
            if key in sport_lower and mapped in selected_lower:
                return True
        
        logger.debug(f"🚫 Sport filter blocked: sport={sport}, selected={selected}")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Sport filter error: {e}")
        return True  # On error, allow through

def generate_call_hash(call_data: dict) -> str:
    """
    Generate a unique hash for a call based on essential content
    Ignores time/date to detect true duplicates
    """
    # Extract essential fields that identify a unique call
    match = call_data.get('match', '')
    market = call_data.get('market', '')
    league = call_data.get('league', '')
    
    # For arbitrage/middle: include outcomes (bookmakers + odds + selections)
    outcomes = call_data.get('outcomes', [])
    outcomes_str = ''
    for outcome in sorted(outcomes, key=lambda x: x.get('casino', '')):
        outcomes_str += f"{outcome.get('casino', '')}{outcome.get('outcome', '')}{outcome.get('odds', '')}"
    
    # For good_ev: include bookmaker + selection + odds
    if call_data.get('bookmaker'):
        outcomes_str += f"{call_data.get('bookmaker', '')}{call_data.get('selection', '')}{call_data.get('odds', '')}"
    
    # For middle: include side_a and side_b
    if call_data.get('side_a'):
        side_a = call_data['side_a']
        outcomes_str += f"{side_a.get('bookmaker', '')}{side_a.get('selection', '')}{side_a.get('odds', '')}"
    if call_data.get('side_b'):
        side_b = call_data['side_b']
        outcomes_str += f"{side_b.get('bookmaker', '')}{side_b.get('selection', '')}{side_b.get('odds', '')}"
    
    # Create hash from essential content (without time/date)
    content = f"{match}|{market}|{league}|{outcomes_str}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def is_duplicate_call(call_data: dict) -> bool:
    """
    Check if this call was already sent recently (within CACHE_EXPIRY_MINUTES)
    Returns True if duplicate, False if new call
    """
    global SENT_CALLS_CACHE
    
    # Clean old entries first
    now = datetime.now()
    expired_keys = [
        key for key, timestamp in SENT_CALLS_CACHE.items()
        if (now - timestamp).total_seconds() > CACHE_EXPIRY_MINUTES * 60
    ]
    for key in expired_keys:
        del SENT_CALLS_CACHE[key]
    
    # Generate hash for this call
    call_hash = generate_call_hash(call_data)
    
    # Check if already sent recently
    if call_hash in SENT_CALLS_CACHE:
        time_since = (now - SENT_CALLS_CACHE[call_hash]).total_seconds()
        logger.warning(f"🚫 DUPLICATE CALL DETECTED! Hash: {call_hash}, sent {time_since:.0f}s ago")
        return True
    
    # Mark as sent
    SENT_CALLS_CACHE[call_hash] = now
    logger.info(f"✅ New call registered: {call_hash}")
    return False


# Load pending calls from disk if exists
def load_pending_calls():
    global PENDING_CALLS
    try:
        import pickle
        if os.path.exists(PENDING_CALLS_FILE):
            with open(PENDING_CALLS_FILE, 'rb') as f:
                PENDING_CALLS = pickle.load(f)
            logger.info(f"✅ Loaded {len(PENDING_CALLS)} pending calls from disk")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load pending calls: {e}")

def save_pending_calls():
    try:
        import pickle
        with open(PENDING_CALLS_FILE, 'wb') as f:
            pickle.dump(PENDING_CALLS, f)
    except Exception as e:
        logger.warning(f"⚠️ Failed to save pending calls: {e}")

load_pending_calls()

# Debug flag: allow sending duplicates (for testing)
ALLOW_DUPLICATE_SEND = os.getenv("ALLOW_DUPLICATE_SEND", "1").strip() in ("1", "true", "True")
DEBUG_ADMIN_PREVIEW = os.getenv("DEBUG_ADMIN_PREVIEW", "0").strip() in ("1", "true", "True")

# Module-level logger (already initialized above)

# Safe callback answer to avoid TelegramBadRequest when query is too old or already answered
async def safe_callback_answer(callback: types.CallbackQuery, text: str = "", show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception:
        try:
            logger.debug("Ignored stale callback.answer")
        except Exception:
            pass
# ===== States =====
class CashhChangeStates(StatesGroup):
    awaiting_amount = State()

class CalculatorStates(StatesGroup):
    awaiting_custom_cash = State()
    awaiting_odds_side1 = State()
    awaiting_odds_side2 = State()
    awaiting_risked_percent = State()
    awaiting_risked_favor = State()

# Middle FSM for custom CASHH input
class MiddleStates(StatesGroup):
    awaiting_custom_cashh = State()

# Storage for drops
DROPS: dict[str, dict] = {}
# Map short tokens -> event_id to keep callback_data under 64 chars
CALC_TOKENS: dict[str, str] = {}
# Storage for last received Good Odds and Middle calls
LAST_GOOD_ODDS: dict = {}
LAST_MIDDLE: dict = {}

def _token_for_eid(eid: str) -> str:
    # Reuse existing token if any
    for t, e in CALC_TOKENS.items():
        if e == eid:
            return t
    t = secrets.token_hex(3)  # 6 hex chars
    CALC_TOKENS[t] = eid
    return t

def _to_int_odds(o) -> int:
    """Convert incoming American odds (possibly as '+120' string) to int safely."""
    try:
        return int(str(o).strip())
    except Exception:
        return 0

def _compute_arb_percent(data: dict) -> float:
    """Fallback compute of arbitrage % from the first two outcomes' odds."""
    try:
        outs = (data.get('outcomes') or [])[:2]
        if len(outs) < 2:
            return 0.0
        odds_list = [_to_int_odds(outs[0].get('odds')), _to_int_odds(outs[1].get('odds'))]
        if 0 in odds_list:
            return 0.0
        return float(ArbitrageCalculator.calculate_arbitrage_percentage(odds_list))
    except Exception:
        return 0.0

# Include routers (order matters for handler resolution)
dp.include_router(web_auth_handler.router)  # Web authentication handler
dp.include_router(force_commands_handler.router)  # Put first to override
dp.include_router(pending_confirmations.router)  # Put before handlers to have priority
dp.include_router(parlay_preferences_handler.router)  # Put before handlers to have priority
from bot import parlays_info_handler
dp.include_router(parlays_info_handler.router)  # Parlays info page
from bot import verify_odds_handler
dp.include_router(verify_odds_handler.router)  # Verify odds for alerts
from bot import bonus_handler
dp.include_router(bonus_handler.router)  # Bonus marketing system
from bot import admin_approval_system
dp.include_router(admin_approval_system.router)  # Admin approval system (multi-level admins)
from bot import admin_actions_final
dp.include_router(admin_actions_final.router)  # Final admin actions (add/remove, broadcast request, etc)
from bot import admin_request_handlers
dp.include_router(admin_request_handlers.router)  # Admin request handlers (free access, ban with approval)
dp.include_router(feedback_vouch_handler.router)  # MUST be before handlers for FSM to work!
dp.include_router(handlers.router)
dp.include_router(admin_handlers.router)

# ML Stats Command (admin monitoring) - Put here for command priority
from bot import ml_stats_command
dp.include_router(ml_stats_command.router)

dp.include_router(learn_handlers.router)
dp.include_router(casino_handlers.router)
dp.include_router(language_handlers.router)
dp.include_router(debug_command.router)

# New manual add-bet flow should come before bet_handlers to ensure
# its FSM message handlers are processed before generic text handlers.
dp.include_router(add_bet_flow.router)
dp.include_router(percent_filters.router)
dp.include_router(stake_rounding_handlers.router)
dp.include_router(casino_filter_handlers.router)
from bot import sport_filter
dp.include_router(sport_filter.router)
dp.include_router(bet_details_pro.router)
dp.include_router(last_calls_pro.router)
dp.include_router(learn_guide_pro.router)
dp.include_router(bet_handlers.router)
dp.include_router(bet_handlers_ev_middle.router)
dp.include_router(middle_handlers.router)
dp.include_router(middle_outcome_tracker.router)
# feedback_vouch_handler.router moved to top (before handlers.router) for FSM priority
dp.include_router(admin_feedback_menu.router)  # Admin menu for feedbacks/vouches
dp.include_router(intelligent_questionnaire.router)
dp.include_router(daily_confirmation.router)
dp.include_router(simulation_handler.router)
dp.include_router(calc_router)

# Book Health Monitor System
from bot import book_health_main
dp.include_router(book_health_main.router)

# Global middleware: auto-confirm yesterday stats on first interaction after midnight
dp.update.outer_middleware(AutoconfirmMiddleware())

# Debug middleware for callbacks
from debug_middleware import DebugCallbackMiddleware
dp.callback_query.outer_middleware(DebugCallbackMiddleware())

# Group whitelist middleware - Bot only works in private chats and admin group
from bot.group_whitelist_middleware import GroupWhitelistMiddleware
dp.update.outer_middleware(GroupWhitelistMiddleware())

# Anti-spam middleware to prevent button spam (Apple-style clean UX)
from bot.anti_spam_middleware import AntiSpamMiddleware
dp.callback_query.middleware(AntiSpamMiddleware(timeout=1.0))  # 1 second cooldown

# Middle Questionnaire Middleware - FORCE users to answer pending middle questionnaires
# This middleware blocks ALL commands/callbacks until pending middle bets are confirmed
from bot.middle_questionnaire_middleware import MiddleQuestionnaireMiddleware
dp.message.middleware(MiddleQuestionnaireMiddleware())  # Block messages
dp.callback_query.middleware(MiddleQuestionnaireMiddleware())  # Block callbacks

# Middle handlers directly on dp (not calc_router)
MIDDLE_BETS_PLACED = {}  # {message_id: user_id}
LAST_MIDDLES = []  # Store last 10 middle messages for Last Calls
LAST_GOOD_EV = []  # Store last 10 Good EV messages for Last Calls

def _register_current_middle_from_callback(callback: types.CallbackQuery):
    """Store the current middle message text into LAST_MIDDLES (ring buffer of 10)."""
    try:
        text = (callback.message.text or callback.message.caption or "").strip()
        if not text:
            return
        # Avoid duplicates: if same text already last, skip
        if LAST_MIDDLES and LAST_MIDDLES[-1].get('text') == text:
            return
        LAST_MIDDLES.append({'text': text})
        # Cap buffer size
        if len(LAST_MIDDLES) > 10:
            del LAST_MIDDLES[0]
    except Exception:
        pass

def _reconstruct_drop_from_message_text(text: str) -> dict | None:
    try:
        lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
        match = None
        league = None
        market = None
        casinos = []
        outcomes = []
        odds_list = []
        # match line
        for i, l in enumerate(lines):
            if l.startswith("🏟️ "):
                match = l[2:].strip()
                # league/market line expected next
                if i + 1 < len(lines) and " - " in lines[i+1]:
                    lm = lines[i+1]
                    left, right = lm.split(" - ", 1)
                    left = left.strip().lstrip("🏈🏀⚽🏒🏅").strip()
                    league = left
                    market = right.strip()
                break
        if not match or not league or not market:
            return None
        # sides and odds
        i = 0
        while i < len(lines) and len(casinos) < 2:
            l = lines[i]
            if "[" in l and "]" in l:
                try:
                    inside = l.split("[",1)[1]
                    book = inside.split("]",1)[0].strip()
                    rest = inside.split("]",1)[1].strip()
                    casinos.append(book)
                    outcomes.append(rest)
                    # find next line with odds
                    j = i+1
                    found_odds = None
                    while j < len(lines) and j < i+4 and found_odds is None:
                        lj = lines[j]
                        if lj.startswith("💵 ") and "(" in lj and ")" in lj:
                            inside_par = lj.split("(",1)[1].split(")",1)[0]
                            # take first signed int in inside_par
                            m = re.search(r"[+\-]?\d+", inside_par)
                            if m:
                                found_odds = int(m.group(0))
                                break
                        j += 1
                    odds_list.append(found_odds if found_odds is not None else -110)
                except Exception:
                    pass
            i += 1
        if len(casinos) < 2:
            return None
        drop = {
            'sport': '',
            'league': league,
            'market': market,
            'match': match,
            'outcomes': [
                {'casino': casinos[0], 'outcome': outcomes[0] if len(outcomes)>0 else '', 'odds': odds_list[0] if len(odds_list)>0 else -110},
                {'casino': casinos[1], 'outcome': outcomes[1] if len(outcomes)>1 else '', 'odds': odds_list[1] if len(odds_list)>1 else -110},
            ]
        }
        return drop
    except Exception:
        return None
def _register_current_goodev_from_callback(callback: types.CallbackQuery):
    try:
        text = (callback.message.text or callback.message.caption or "").strip()
        if not text:
            return
        if LAST_GOOD_EV and LAST_GOOD_EV[-1].get('text') == text:
            return
        LAST_GOOD_EV.append({'text': text})
        if len(LAST_GOOD_EV) > 10:
            del LAST_GOOD_EV[0]
    except Exception:
        pass

@dp.callback_query(F.data.startswith("midnew_bet_"))
async def midnew_bet_handler_dp(callback: types.CallbackQuery):
    """Handle Middle I BET button"""
    await safe_callback_answer(callback)
    _register_current_middle_from_callback(callback)
    
    # Get current keyboard
    current_kb = callback.message.reply_markup.inline_keyboard if callback.message.reply_markup else []
    
    # Rebuild keyboard with checkmark on I BET button BUT keep casino buttons
    new_kb = []
    casino_buttons_found = False
    
    for row in current_kb:
        new_row = []
        for btn in row:
            # Keep casino buttons (they have URL not callback_data)
            if hasattr(btn, 'url') and btn.url:
                new_row.append(btn)
                casino_buttons_found = True
            elif btn.callback_data and "midnew_bet_" in btn.callback_data:
                # Replace I BET with checkmark version
                new_row.append(InlineKeyboardButton(
                    text="✅ BET PLACED!",
                    callback_data="noop"
                ))
            elif btn.callback_data and ("midnew_calc_" in btn.callback_data or "midnew_cashh_" in btn.callback_data):
                # Remove calculator and change CASHH buttons after bet
                pass
            else:
                new_row.append(btn)
        if new_row:
            new_kb.append(new_row)
    
    # Add "Oops mistake" button
    new_kb.append([InlineKeyboardButton(
        text="❌ Oops, mistake!",
        callback_data="midnew_undo"
    )])
    
    # Add confirmation to message
    current_text = callback.message.text or ""
    confirmation = "\n\n✅ <b>MIDDLE BET ENREGISTRÉ!</b>\n📊 Saved to your stats"
    
    if "MIDDLE BET ENREGISTRÉ" not in current_text:
        new_text = current_text + confirmation
    else:
        new_text = current_text
    
    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb),
            parse_mode=ParseMode.HTML
        )
    except:
        pass


@dp.message(MiddleStates.awaiting_custom_cashh)
async def middle_custom_cashh_message(message: types.Message, state: FSMContext):
    """Handle custom CASHH amount input and re-render full message."""
    text = (message.text or "").strip().replace('$','').replace(',','')
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Montant invalide. Ex: 750")
        return

    # Compute new stakes
    from utils.middle_calculator import calculate_middle_stakes
    calc = calculate_middle_stakes(-105, 120, amount)

    new_text = (
        f"✅🎰 <b>MIDDLE SAFE - PROFIT GARANTI + JACKPOT!</b> 🎰✅\n\n"
        f"🏈 <b>New England Patriots vs Cincinnati Bengals</b>\n"
        f"📊 NFL - Player Receptions\n"
        f"👤 Chase Brown\n"
        f"💰 <b>CASHH: ${amount:.2f}</b> (mis à jour!)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>CONFIGURATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟️ <b>[Mise-o-jeu]</b> Over 3.5\n"
        f"💵 Mise: <b>${calc['stake_a']:.2f}</b> (-105)\n"
        f"📈 Retour: ${calc['return_a']:.2f}\n\n"
        f"❄️ <b>[Coolbet]</b> Under 4.5\n"
        f"💵 Mise: <b>${calc['stake_b']:.2f}</b> (+120)\n"
        f"📈 Retour: ${calc['return_b']:.2f}\n\n"
        f"💰 <b>Total: ${amount:.2f}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>SCÉNARIOS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ <b>Over 3.5 hits seul</b>\n"
        f"✅ Profit: <b>${calc['profit_a_only']:.2f}</b>\n\n"
        f"2️⃣ <b>MIDDLE HIT! 🎰</b>\n"
        f"🚀 Zone magique: Exactement 4 receptions\n"
        f"💰 Profit: <b>${calc['profit_both']:.2f}</b> (107% ROI!)\n\n"
        f"3️⃣ <b>Under 4.5 hits seul</b>\n"
        f"✅ Profit: <b>${calc['profit_b_only']:.2f}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Stakes recalculés avec ${amount}!</b>"
    )

    # Edit the previous message
    data = await state.get_data()
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    try:
        await message.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Retour au message", callback_data="midnew_back_to_msg")]]))
    except Exception:
        await message.answer(new_text, parse_mode=ParseMode.HTML)
    await state.clear()

@dp.callback_query(F.data.startswith("midnew_calc_"))
async def midnew_calc_handler_dp(callback: types.CallbackQuery):
    """Show calculator info"""
    await safe_callback_answer(callback)
    _register_current_middle_from_callback(callback)
    
    calc_text = """🧮 <b>CALCULATEUR MIDDLE - Chase Brown</b>

<b>📊 Configuration:</b>
• Over 3.5 @ -105 → Mise: $264.91
• Under 4.5 @ +120 → Mise: $235.09
• Total misé: $500.00

<b>💰 Profits possibles:</b>
• Si Over 3.5 seul: +$17.20 (3.4% ROI)
• Si MIDDLE (exactement 4): +$534.40 (107% ROI!)
• Si Under 4.5 seul: +$17.20 (3.4% ROI)

<b>📈 Analyse:</b>
• Type: <b>MIDDLE SAFE</b> (profit garanti)
• Gap: 1.0 reception (excellent!)
• Probabilité middle: ~20%
• Expected Value: +21.4%

<b>📌 Simulation 100 bets:</b>
• 80 fois profit normal: $1,376
• 20 fois middle hit: $10,688
• <b>Total: +$12,064</b>"""
    
    keyboard = [[InlineKeyboardButton(text="◀️ Retour au message", callback_data="midnew_back")]]
    
    try:
        await callback.message.edit_text(
            calc_text, 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

@dp.callback_query(F.data.startswith("midnew_cashh_"))
async def midnew_cashh_handler_dp(callback: types.CallbackQuery):
    """Show CASHH change menu"""
    await safe_callback_answer(callback)
    _register_current_middle_from_callback(callback)
    
    keyboard = []
    # Quick amounts in 2 columns
    keyboard.append([
        InlineKeyboardButton(text="$100", callback_data="midnew_setcash_100"),
        InlineKeyboardButton(text="$200", callback_data="midnew_setcash_200")
    ])
    keyboard.append([
        InlineKeyboardButton(text="$300", callback_data="midnew_setcash_300"),
        InlineKeyboardButton(text="$500", callback_data="midnew_setcash_500")
    ])
    keyboard.append([
        InlineKeyboardButton(text="$1000", callback_data="midnew_setcash_1000"),
        InlineKeyboardButton(text="✏️ Custom", callback_data="midnew_setcash_custom")
    ])
    keyboard.append([InlineKeyboardButton(text="◀️ Retour au message", callback_data="midnew_back_to_msg")])
    
    try:
        await callback.message.edit_text(
            "💰 <b>Changer CASHH pour ce bet</b>\n\nChoisis un montant ou entre un montant custom:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

@dp.callback_query(F.data.startswith("midnew_setcash_"))
async def midnew_setcash_handler_dp(callback: types.CallbackQuery, state: FSMContext):
    """Handle cash amount selection"""
    await safe_callback_answer(callback)
    _register_current_middle_from_callback(callback)
    
    # Extract amount
    data = callback.data.split('_')
    if len(data) < 3:
        return
    
    amount_str = data[2]
    
    if amount_str == "custom":
        # Show custom input prompt and set FSM state
        await callback.message.edit_text(
            "💰 <b>Entre un montant personnalisé</b>\n\n"
            "Envoie juste le montant (ex: 750)",
            parse_mode=ParseMode.HTML
        )
        await state.set_state(MiddleStates.awaiting_custom_cashh)
        # Save message info to edit later
        await state.update_data(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        return
    
    try:
        amount = float(amount_str)
    except:
        return
    
    # Recalculate with new amount
    from utils.middle_calculator import calculate_middle_stakes
    from core.casinos import get_casino_referral_link, get_casino_logo
    from utils.odds_api_links import get_fallback_url
    
    # Recalc with new amount
    calc = calculate_middle_stakes(-105, 120, amount)
    
    # Full middle message with new calculations
    new_text = f"""✅🎰 <b>MIDDLE SAFE - PROFIT GARANTI + JACKPOT!</b> 🎰✅

🏈 <b>New England Patriots vs Cincinnati Bengals</b>
📊 NFL - Player Receptions
👤 Chase Brown
💰 <b>CASHH: ${amount:.2f}</b> (mis à jour!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>CONFIGURATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎟️ <b>[Mise-o-jeu]</b> Over 3.5
💵 Mise: <b>${calc['stake_a']:.2f}</b> (-105)
📈 Retour: ${calc['return_a']:.2f}

❄️ <b>[Coolbet]</b> Under 4.5
💵 Mise: <b>${calc['stake_b']:.2f}</b> (+120)
📈 Retour: ${calc['return_b']:.2f}

💰 <b>Total: ${amount:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>SCÉNARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ <b>Over 3.5 hits seul</b>
✅ Profit: <b>${calc['profit_a_only']:.2f}</b>

2️⃣ <b>MIDDLE HIT! 🎰</b>
🚀 Zone magique: Exactement 4 receptions
💰 Profit: <b>${calc['profit_both']:.2f}</b> (107% ROI!)

3️⃣ <b>Under 4.5 hits seul</b>
✅ Profit: <b>${calc['profit_b_only']:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ <b>Stakes recalculés avec ${amount}!</b>"""

    keyboard = [[InlineKeyboardButton(text="◀️ Retour au message", callback_data="midnew_back_to_msg")]]
    
    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

@dp.callback_query(F.data == "midnew_back_to_msg")
async def midnew_back_to_msg_handler_dp(callback: types.CallbackQuery):
    """Return to original middle message"""
    await safe_callback_answer(callback)
    # Import for casinos
    from core.casinos import get_casino_referral_link, get_casino_logo
    from utils.odds_api_links import get_fallback_url

    # Restore full original message (prefer the last stored middle text)
    original_text = (LAST_MIDDLES[-1]['text'] if LAST_MIDDLES else (callback.message.text or ""))

    # Rebuild full keyboard
    keyboard = []
    url_a = get_casino_referral_link("Mise-o-jeu") or get_fallback_url("Mise-o-jeu")
    url_b = get_casino_referral_link("Coolbet") or get_fallback_url("Coolbet")
    if url_a and url_b:
        keyboard.append([
            InlineKeyboardButton(text=f"{get_casino_logo('Mise-o-jeu')} Mise-o-jeu", url=url_a),
            InlineKeyboardButton(text=f"{get_casino_logo('Coolbet')} Coolbet", url=url_b)
        ])
    keyboard.append([InlineKeyboardButton(text="💰 I BET", callback_data="midnew_bet_back")])
    keyboard.append([
        InlineKeyboardButton(text="🧮 Calculator", callback_data="midnew_calc_back"),
        InlineKeyboardButton(text="💵 Change CASHH", callback_data="midnew_cashh_back")
    ])

    try:
        await callback.message.edit_text(
            original_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

# Capture Good EV messages on any Good EV callback
@dp.callback_query(F.data.startswith("good_ev_"))
async def _capture_good_ev(callback: types.CallbackQuery):
    _register_current_goodev_from_callback(callback)
    # Do not interfere with existing handlers; just acknowledge silently
    try:
        await callback.answer()
    except Exception:
        pass

@dp.callback_query(F.data == "midnew_back")
async def midnew_back_handler_dp(callback: types.CallbackQuery):
    """Back to the full middle message"""
    await safe_callback_answer(callback)
    await midnew_back_to_msg_handler_dp(callback)

@dp.callback_query(F.data == "midnew_undo")
async def midnew_undo_handler_dp(callback: types.CallbackQuery):
    """Undo the bet - restore original buttons"""
    await safe_callback_answer(callback, "❌ Bet annulé")
    
    # Import for casinos
    from core.casinos import get_casino_referral_link, get_casino_logo
    from utils.odds_api_links import get_fallback_url
    
    # Restore original buttons with casino links
    keyboard = []
    
    # Add casino buttons (hardcoded for now - Mise-o-jeu and Coolbet)
    url_a = get_casino_referral_link("Mise-o-jeu") or get_fallback_url("Mise-o-jeu")
    url_b = get_casino_referral_link("Coolbet") or get_fallback_url("Coolbet")
    
    if url_a and url_b:
        keyboard.append([
            InlineKeyboardButton(text=f"{get_casino_logo('Mise-o-jeu')} Mise-o-jeu", url=url_a),
            InlineKeyboardButton(text=f"{get_casino_logo('Coolbet')} Coolbet", url=url_b)
        ])
    
    keyboard.append([InlineKeyboardButton(text="💰 I BET", callback_data="midnew_bet_undo")])
    keyboard.append([
        InlineKeyboardButton(text="🧮 Calculator", callback_data="midnew_calc_undo"),
        InlineKeyboardButton(text="💵 Change CASHH", callback_data="midnew_cashh_undo")
    ])
    
    # Remove confirmation from message
    current_text = callback.message.text or ""
    if "✅ <b>MIDDLE BET ENREGISTRÉ!</b>" in current_text:
        new_text = current_text.replace("\n\n✅ <b>MIDDLE BET ENREGISTRÉ!</b>\n📊 Saved to your stats", "")
    else:
        new_text = current_text
    
    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode=ParseMode.HTML
        )
    except:
        pass


async def send_arbitrage_alert_to_users(arb_data: dict):
    """
    Send arbitrage alert to all eligible users based on their tier
    
    Args:
        arb_data: Parsed arbitrage data from source bot
    """
    # DEDUPLICATION CHECK - Block duplicate calls
    if is_duplicate_call(arb_data):
        logger.warning(f"🚫 ARBITRAGE DUPLICATE BLOCKED: {arb_data.get('match', 'Unknown')} - {arb_data.get('arb_percentage', 0)}%")
        return
    
    db = SessionLocal()
    
    try:
        # Ensure arb % present for gating
        try:
            ap = float(arb_data.get('arb_percentage') or 0)
        except Exception:
            ap = 0.0
        if ap <= 0:
            ap = _compute_arb_percent(arb_data)
            arb_data['arb_percentage'] = ap
        
        # ✅ OPTIMIZATION #2: API enrichment already done in /public/drop, skip double enrichment
        # arb_data should already be enriched if it's a new call (not duplicate)
        # This saves 2-3s per call by avoiding redundant API calls

        # Get all active users (notifications filter handled per-user to treat NULL as enabled)
        users = db.query(User).filter(
            User.is_active == True,
            User.is_banned == False,
        ).all()
        
        print(f"🔍 DEBUG: Found {len(users)} active users in DB")
        print(f"🔍 DEBUG: Arb percentage: {arb_data.get('arb_percentage')}%")
        
        # ✅ OPTIMIZATION #4: Process users in PARALLEL with asyncio.gather
        # Helper function to process and send to one user
        async def process_user_send(user):
            """Process one user and send alert if eligible. Returns True if sent."""
            try:
                # Resolve user's effective tier (respect subscription expiry)
                def _core_tier_from_model(t):
                    try:
                        name = t.name.lower()
                    except Exception:
                        return TierLevel.FREE
                    return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE

                tier_core = _core_tier_from_model(user.tier)
                
                # downgrade to FREE if subscription expired (but NOT lifetime!)
                if tier_core != TierLevel.FREE and not user.subscription_active:
                    tier_core = TierLevel.FREE

                # Skip if user explicitly disabled notifications
                if user.notifications_enabled is False:
                    return False

                # Check if user can view this alert
                if not TierManager.can_view_alert(tier_core, arb_data['arb_percentage']):
                    return False
                
                # Check user's custom percentage filter for arbitrage
                arb_percent = float(arb_data.get('arb_percentage', 0))
                user_min = user.min_arb_percent or 0.5
                user_max = user.max_arb_percent or 100.0
                if not (user_min <= arb_percent <= user_max):
                    return False
                
                # Check casino filter (both sides of arbitrage)
                casinos = []
                for outcome in arb_data.get('outcomes', []):
                    casino = outcome.get('casino') or outcome.get('bookmaker', '')
                    if casino:
                        casinos.append(casino)
                if casinos and not user_passes_casino_filter(user, casinos):
                    return False
                
                # Check sport filter
                sport = arb_data.get('sport', '') or arb_data.get('league', '')
                if not user_passes_sport_filter(user, sport):
                    return False
                
                # Check "Match Today Only" filter
                if getattr(user, 'match_today_only', False):
                    commence_time_iso = arb_data.get('commence_time')
                    if commence_time_iso:
                        try:
                            from datetime import datetime, date, timezone
                            dt = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
                            match_date = dt.date()
                            today_date = date.today()
                            if match_date != today_date:
                                return False
                        except Exception:
                            pass  # If can't parse, let it through
                
                # Check daily alert limit
                features = TierManager.get_features(tier_core)
                max_alerts = features.get('max_alerts_per_day', 5)
                if not user.can_receive_alert_today(max_alerts):
                    return False
                
                # Check spacing for FREE tier (2 hours between calls)
                if tier_core == TierLevel.FREE:
                    min_spacing = features.get('min_spacing_minutes', 120)
                    if user.last_alert_at:
                        from datetime import datetime, timedelta
                        time_since_last = datetime.now() - user.last_alert_at.replace(tzinfo=None)
                        if time_since_last < timedelta(minutes=min_spacing):
                            return False
                
                # Apply delay for FREE tier ONLY for first alert
                delay = 0
                if tier_core == TierLevel.FREE and user.last_alert_at is None:
                    delay = TierManager.get_alert_delay(tier_core)  # 15 minutes
                
                if delay > 0:
                    # Schedule delayed send (first alert only)
                    asyncio.create_task(send_delayed_alert(user.telegram_id, arb_data, delay))
                    user.increment_alert_count()
                    return False  # Don't count as immediate send
                else:
                    # Send immediately
                    await send_alert_to_user(user.telegram_id, tier_core, arb_data)
                    user.increment_alert_count()
                    return True
            except Exception as e:
                print(f"❌ ERROR: process_user_send failed for {user.telegram_id}: {e}")
                return False
        
        # ⚡ Send to all users in PARALLEL (saves 6-7s)
        results = await asyncio.gather(*[process_user_send(u) for u in users], return_exceptions=True)
        sent_count = sum(1 for r in results if r is True)
        print(f"📊 DEBUG: Sent to {sent_count}/{len(users)} users (PARALLEL)")
        db.commit()
    
    finally:
        db.close()


async def send_delayed_alert(user_id: int, arb_data: dict, delay_minutes: int):
    """
    Send alert after delay
    
    Args:
        user_id: User's telegram ID
        arb_data: Arbitrage data
        delay_minutes: Delay in minutes
    """
    await asyncio.sleep(delay_minutes * 60)
    
    # Get user tier
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            def _core_tier_from_model(t):
                try:
                    name = t.name.lower()
                except Exception:
                    return TierLevel.FREE
                return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE
            tier_core = _core_tier_from_model(user.tier)
            try:
                if tier_core != TierLevel.FREE and not user.subscription_active:
                    tier_core = TierLevel.FREE
            except Exception:
                pass
            try:
                await send_alert_to_user(user_id, tier_core, arb_data)
            except Exception as e:
                print(f"❌ ERROR: delayed send_alert_to_user failed for {user_id}: {e}")
    finally:
        db.close()


async def send_alert_to_user(user_id: int, tier: TierLevel, arb_data: dict, use_new_processor: bool = True):
    """
    Send formatted arbitrage alert to a user
    
    Args:
        user_id: User's telegram ID
        tier: User's tier level
        arb_data: Arbitrage data
        use_new_processor: Use enriched processor with Odds API
    """
    calculator = ArbitrageCalculator()
    
    # Get user preferences first (including rounding)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return
        # Use 'language' field from User model ("fr"/"en")
        lang_pref = (user.language or 'en') if hasattr(user, 'language') else 'en'
        # Get rounding preferences
        user_rounding = user.stake_rounding or 0
        user_mode = getattr(user, 'rounding_mode', 'nearest') or 'nearest'
        # Get user bankroll
        user_bankroll = user.default_bankroll or TierManager.get_features(tier).get('bankroll_amount', 750)
    finally:
        db.close()
    
    # Try new enriched processor
    if use_new_processor:
        try:
            # Process call with enrichment - use user's bankroll
            betting_call = process_call_from_drop(arb_data, user_bankroll)
            
            # Apply user's stake rounding to the betting call with CORRECT recalculation
            if betting_call and user_rounding > 0 and len(betting_call.sides) >= 2:
                from utils.stake_rounder import round_arbitrage_stakes
                
                stake_a = betting_call.sides[0].stake
                stake_b = betting_call.sides[1].stake
                odds_a = betting_call.sides[0].odds_american
                odds_b = betting_call.sides[1].odds_american
                
                rounded_result = round_arbitrage_stakes(
                    stake_a, stake_b, odds_a, odds_b,
                    user_bankroll, user_rounding, user_mode
                )
                
                if rounded_result:
                    # Update stakes with rounded values
                    betting_call.sides[0].stake = rounded_result['stake_a']
                    betting_call.sides[1].stake = rounded_result['stake_b']
                    # Update returns with recalculated values
                    betting_call.sides[0].expected_return = rounded_result['return_a']
                    betting_call.sides[1].expected_return = rounded_result['return_b']
                    # Recalculate arbitrage analysis with new stakes
                    betting_call = analyze_arbitrage_two_way(betting_call)
            
            if betting_call:
                # Store for later verification
                PENDING_CALLS[betting_call.call_id] = betting_call
                save_pending_calls()
                
                # Format enriched message
                message_text = format_call_message(betting_call, lang=lang_pref, verified=False)
                
                # Build keyboard with casino links and verify button
                keyboard = []
                
                # Casino buttons with best available links
                casino_buttons = []
                for side in betting_call.sides[:2]:
                    # Priority: deep link > referral > fallback
                    link = side.deep_link or None
                    if not link:
                        link = get_casino_referral_link(side.book_name)
                    if not link:
                        link = side.fallback_link
                    
                    # Always have a link (use generic site URL as last resort)
                    if not link:
                        link = f"https://{side.book_name.lower().replace(' ', '')}.com"
                    
                    logger.info(f"🔗 Casino button for {side.book_name}: deep={side.deep_link}, referral={get_casino_referral_link(side.book_name)}, fallback={side.fallback_link}, final={link}")
                    
                    if link:
                        casino_buttons.append(
                            InlineKeyboardButton(
                                text=f"{get_casino_logo(side.book_name)} {side.book_name}",
                                url=link
                            )
                        )
                
                if casino_buttons:
                    keyboard.append(casino_buttons)
                
                # JE PARIE button with profit
                drop_event_id = arb_data.get('drop_event_id', 0)
                
                # If drop_event_id is 0, try to find it from DB using event_id
                if drop_event_id == 0:
                    event_id = arb_data.get('event_id')
                    if event_id:
                        db = SessionLocal()
                        try:
                            from models.drop_event import DropEvent
                            drop_ev = db.query(DropEvent).filter(DropEvent.event_id == event_id).first()
                            if drop_ev:
                                drop_event_id = drop_ev.id
                                arb_data['drop_event_id'] = drop_ev.id  # Update for future use
                                logger.info(f"✅ Found drop_event_id={drop_ev.id} for event_id={event_id}")
                        finally:
                            db.close()
                
                total_stake = sum(s.stake for s in betting_call.sides)
                expected_profit = betting_call.arb_analysis.min_profit if betting_call.arb_analysis else 0

                # Map drop_event_id -> call_id so CASHH changes can rebuild the
                # same enriched keyboard (including Verify Odds button)
                try:
                    if drop_event_id:
                        CALL_IDS_BY_DROP_ID[str(drop_event_id)] = betting_call.call_id
                except Exception:
                    pass
                
                i_bet_text = f"💰 JE PARIE (${expected_profit:.2f} profit)" if lang_pref == 'fr' else f"💰 I BET (${expected_profit:.2f} profit)"
                keyboard.append([
                    InlineKeyboardButton(
                        text=i_bet_text,
                        callback_data=f"i_bet_{drop_event_id}_{total_stake:.0f}_{expected_profit:.2f}"
                    )
                ])
                
                # Calculator button (BRONZE+)
                features = TierManager.get_features(tier)
                if features.get('show_calculator'):
                    keyboard.append([
                        InlineKeyboardButton(
                            text="🧮 Calculateur Custom" if lang_pref == 'fr' else "🧮 Custom Calculator",
                            callback_data=f"calc_{drop_event_id}|menu"
                        )
                    ])
                
                # Change CASHH button
                keyboard.append([
                    InlineKeyboardButton(
                        text="💰 Changer CASHH" if lang_pref == 'fr' else "💰 Change CASHH",
                        callback_data=f"change_bankroll_{drop_event_id}"
                    )
                ])
                
                # Verify odds button - DISABLED FOR NOW (not working properly)
                # keyboard.append([
                #     InlineKeyboardButton(
                #         text="✅ Vérifier les cotes" if lang_pref == 'fr' else "✅ Verify Odds",
                #         callback_data=f"verify_odds:{betting_call.call_id}"
                #     )
                # ])
                
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                # Send message
                try:
                    print(f"📤 DEBUG: Sending enriched message to {user_id}")
                except Exception:
                    pass
                
                await bot.send_message(
                    user_id, 
                    message_text, 
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=False,  # Show link previews
                    protect_content=True  # Prevent forwarding and copying
                )
                
                try:
                    print(f"✅ DEBUG: Successfully sent enriched message to {user_id}")
                except Exception:
                    pass
                
                return
                
        except Exception as e:
            logger.error(f"Failed to use new processor: {e}")
            # Continue with old method below
    
    # Fallback to old method
    calculator = ArbitrageCalculator()
    
    # Get user's default bankroll and language
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        bankroll = user.default_bankroll if user else 400.0
        lang_pref = (user.language if user else "en") or "en"
    finally:
        db.close()
    
    # Extract odds (limit to 2 outcomes) and cast to int robustly
    outcomes_list = (arb_data.get('outcomes') or [])[:2]
    if len(outcomes_list) < 2:
        print(f"❌ ERROR: Not enough outcomes to send alert for user {user_id}")
        return
    odds_list = [_to_int_odds(outcome.get('odds')) for outcome in outcomes_list]
    
    # Calculate SAFE mode (guaranteed arbitrage if available)
    safe_calc = calculator.calculate_safe_stakes(bankroll, odds_list)

    # If no strict arbitrage according to our calculator, fall back to
    # an equal-stake allocation so we still send the alert.
    if not safe_calc.get('has_arbitrage'):
        try:
            print(f"⚠️ DEBUG: No strict arbitrage for user {user_id}, using equal-stake fallback")
            n = len(odds_list)
            if n == 0:
                return
            # Split bankroll equally and compute returns
            stake_each = round(bankroll / n, 2)
            stakes = [stake_each] * n
            decimals = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
            returns = [round(stakes[i] * decimals[i], 2) for i in range(n)]
            profit = min(returns) - bankroll
            roi = ArbitrageCalculator.compute_roi(bankroll, profit)
            safe_calc = {
                "mode": "SAFE",
                "has_arbitrage": False,
                "stakes": stakes,
                "returns": returns,
                "profit": round(profit, 2),
                "roi_percent": roi.get("roi_percent", 0.0),
            }
        except Exception as e:
            print(f"❌ ERROR: fallback stakes failed for user {user_id}: {e}")
            return
    
    # Build message (localized)
    if lang_pref == 'fr':
        title_line = f"🚨 <b>ALERTE ARBITRAGE - {arb_data['arb_percentage']}%</b> 🚨\n\n"
        cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
        profit_line = f"✅ <b>Profit Garanti: ${safe_calc['profit']}</b> (ROI: {safe_calc.get('roi_percent', 0):.2f}%)\n\n"
        stake_label = "Miser"
        return_label = "Retour"
    else:
        title_line = f"🚨 <b>ARBITRAGE ALERT - {arb_data['arb_percentage']}%</b> 🚨\n\n"
        cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
        profit_line = f"✅ <b>Guaranteed Profit: ${safe_calc['profit']}</b> (ROI: {safe_calc.get('roi_percent', 0):.2f}%)\n\n"
        stake_label = "Stake"
        return_label = "Return"

    # Extract time from API enrichment or original field
    time_str = arb_data.get('formatted_time', '') or arb_data.get('commence_time', '') or arb_data.get('time', '')
    time_line = f"🕐 {time_str}\n" if time_str and time_str != 'TBD' else ""
    
    # Get correct sport emoji
    from utils.sport_emoji import get_sport_emoji
    sport_emoji = get_sport_emoji(arb_data.get('league',''), arb_data.get('sport',''))
    
    message_text = (
        title_line
        + f"🏟️ <b>{arb_data.get('match') or arb_data.get('event') or 'Match'}</b>\n"
        + f"{sport_emoji} {arb_data.get('league','')} - {arb_data.get('market','')}\n"
        + time_line
        + "\n"
        + cashh_line
        + profit_line
    )
    
    # Add each outcome
    for i, outcome_data in enumerate(outcomes_list):
        casino_name = outcome_data.get('casino','')
        casino_info = get_casino(casino_name)
        logo = get_casino_logo(casino_name)
        odds_val = _to_int_odds(outcome_data.get('odds'))
        odds_str = f"+{odds_val}" if odds_val > 0 else str(odds_val)
        stake = safe_calc['stakes'][i]
        return_amount = safe_calc['returns'][i]
        
        message_text += (
            f"{logo} <b>[{casino_name}]</b> {outcome_data.get('outcome','')}\n"
            f"💵 {stake_label}: <code>${stake}</code> ({odds_str}) → {return_label}: ${return_amount:.2f}\n\n"
        )
    
    # Add odds change warning
    if lang_pref == 'fr':
        message_text += "⚠️ <b>Attention: les cotes peuvent changer - toujours vérifier avant de bet!</b>\n\n"
    else:
        message_text += "⚠️ <b>Odds can change - always verify before betting!</b>\n\n"
    
    # Build inline keyboard
    keyboard = []
    
    # Casino links with deep links (BRONZE+)
    features = TierManager.get_features(tier)
    if features.get('referral_links'):
        casino_buttons = []
        
        # UTILISER les deep_links DÉJÀ enrichis par odds_enricher!
        deep_links = arb_data.get('deep_links', {})
        
        # Debug
        print(f"📊 DEBUG deep_links keys: {list(deep_links.keys()) if deep_links else 'None'}")
        print(f"📊 DEBUG outcomes casinos: {[o['casino'] for o in arb_data['outcomes']]}")
        
        for outcome_data in arb_data['outcomes']:
            casino_name = outcome_data['casino']
            logo = get_casino_logo(casino_name)
            
            # PRIORITÉ: 1) Deep link enrichi, 2) Fallback
            # Try exact match first
            link = deep_links.get(casino_name)
            
            # If not found, try case-insensitive match
            if not link and deep_links:
                for key, value in deep_links.items():
                    if key.lower() == casino_name.lower():
                        link = value
                        print(f"✅ Found deep link via case-insensitive match: {casino_name} → {key}")
                        break
            
            if not link:
                link = get_fallback_url(casino_name)
                print(f"⚠️ No deep link found for '{casino_name}', using fallback")
            else:
                print(f"✅ Using deep link for {casino_name}: {link[:70]}...")
            
            casino_buttons.append(
                InlineKeyboardButton(
                    text=f"{logo} {casino_name}",
                    url=link
                )
            )
        
        if casino_buttons:
            keyboard.append(casino_buttons)
    
    # I BET button - Track this bet
    # Get drop_event_id for tracking
    drop_event_id = arb_data.get('drop_event_id', 0)
    total_stake = bankroll
    expected_profit = safe_calc.get('profit', 0)
    
    i_bet_text = f"💰 I BET (${expected_profit:.2f} profit)" if lang_pref == 'en' else f"💰 JE PARIE (${expected_profit:.2f} profit)"
    keyboard.append([
        InlineKeyboardButton(
            text=i_bet_text,
            callback_data=f"i_bet_{drop_event_id}_{total_stake}_{expected_profit}"
        )
    ])
    
    # Calculator button (BRONZE+)
    if features.get('show_calculator'):
        keyboard.append([
            InlineKeyboardButton(
                text="🧮 Calculateur Custom",
                callback_data=f"calc_{arb_data.get('event_id','')}"
            )
        ])
    
    # If no referral links available for this tier, offer Casinos menu button
    if not features.get('referral_links'):
        keyboard.append([
            InlineKeyboardButton(text=("🎰 Casinos" if lang_pref != 'fr' else "🎰 Casinos"), callback_data="show_casinos")
        ])

    # Per-call Change CASHH button
    cashh_text = "💰 Changer CASHH" if lang_pref == 'fr' else "💰 Change CASHH"
    keyboard.append([
        InlineKeyboardButton(text=cashh_text, callback_data=f"chg_cashh_{arb_data['event_id']}")
    ])
    
    # Verify Odds button - Real-time verification via The Odds API
    verify_text = "🔍 Vérifier Cotes" if lang_pref == 'fr' else "🔍 Verify Odds"
    keyboard.append([
        InlineKeyboardButton(text=verify_text, callback_data=f"verify_arb_{drop_event_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    try:
        print(f"📤 DEBUG: Attempting to send message to {user_id}")
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=False,
            protect_content=True  # Prevent forwarding and copying
        )
        print(f"✅ DEBUG: Successfully sent message to {user_id}")
    except Exception as e:
        print(f"❌ ERROR: Failed to send alert to {user_id}: {e}")
        import traceback
        traceback.print_exc()


# ===== FastAPI Endpoints =====

@app.post("/public/drop")
async def receive_drop(req: Request):
    """
    Receive arbitrage drop from external source
    Format: JSON with event details
    """
    d = await req.json()
    eid = d.get("event_id")
    try:
        print(f"📥 DEBUG: /public/drop received eid={eid}")
    except Exception:
        pass
    if not eid:
        return {"ok": False, "error": "missing event_id"}
    
    # Normalize arb percentage to float for gating logic
    try:
        d["arb_percentage"] = float(d.get("arb_percentage") or 0)
    except Exception:
        d["arb_percentage"] = 0.0
    
    # ✅ OPTIMIZATION #1: Check duplicate BEFORE API enrichment (saves 2-3s per duplicate)
    db = SessionLocal()
    is_duplicate = False
    existing_drop_id = None
    try:
        ev = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        if ev:
            is_duplicate = True
            existing_drop_id = ev.id  # ✅ Save ID before closing session
            print(f"🚨 DUPLICATE event_id: {eid} - Skipping API enrichment")
    finally:
        db.close()
    
    # ✅ OPTIMIZATION #2: Enrich in BACKGROUND (non-blocking!) to keep bot fast
    if not is_duplicate:
        # Send call IMMEDIATELY, enrich in background
        print(f"⚡ SPEED: Sending call immediately, enrichment in background")
        
        # Start enrichment in background (won't block)
        async def enrich_in_background():
            try:
                from utils.odds_enricher import enrich_alert_with_api
                enriched = enrich_alert_with_api(d, 'arbitrage')
                # Update stored drop with enriched data
                DROPS[eid] = enriched
                print(f"🔗 Background enrichment done: {len(enriched.get('deep_links', {}))} deep links")
                
                # ✅ Also update the database with enriched data (for web dashboard)
                try:
                    db_update = SessionLocal()
                    ev_update = db_update.query(DropEvent).filter(DropEvent.event_id == eid).first()
                    if ev_update:
                        ev_update.payload = enriched
                        db_update.commit()
                        print(f"💾 DB updated with formatted_time: {enriched.get('formatted_time', 'N/A')}")
                except Exception as db_err:
                    print(f"⚠️ DB update failed: {db_err}")
                finally:
                    try:
                        db_update.close()
                    except:
                        pass
            except Exception as e:
                print(f"⚠️ Background enrichment failed: {e}")
        
        # Launch in background, don't wait
        asyncio.create_task(enrich_in_background())
    else:
        print(f"⚡ SKIP: Enrichment skipped for duplicate {eid}")
        # ✅ Assign drop_event_id immediately for duplicates
        if existing_drop_id:
            d['drop_event_id'] = existing_drop_id
    
    # Mark receive time for later re-send to new PREMIUM users
    d["received_at"] = datetime.now().isoformat()
    DROPS[eid] = d
    try:
        drop_id = record_drop(d)
        # ⚡ Parlays générés APRÈS envoi aux users (voir fin de fonction)
    except Exception:
        drop_id = None
    # Persist to DB (duplicate already detected above)
    db = SessionLocal()
    try:
        ev = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        if ev:
            # Update existing duplicate
            # Refresh timestamp so it appears in Last Calls, and update payload/ap if provided
            try:
                try:
                    ap = float(d.get('arb_percentage') or 0)
                except Exception:
                    ap = 0.0
                if ap <= 0:
                    ap = _compute_arb_percent(d)
                    d['arb_percentage'] = ap
                ev.arb_percentage = ap if ap else ev.arb_percentage
                ev.match = d.get('match') or ev.match
                ev.league = d.get('league') or ev.league
                ev.market = d.get('market') or ev.market
                ev.payload = d or ev.payload
                ev.received_at = datetime.now()
                db.commit()
                print(f"♻️ DEBUG: Refreshed duplicate drop {eid} (id={ev.id})")
            except Exception as _e:
                try:
                    db.rollback()
                except Exception:
                    pass
        else:
            ev = DropEvent(event_id=eid)
            db.add(ev)
        
        if not is_duplicate:
            ev.received_at = datetime.now()
            try:
                ap = float(d.get('arb_percentage') or 0)
            except Exception:
                ap = 0.0
            if ap <= 0:
                ap = _compute_arb_percent(d)
                d['arb_percentage'] = ap
            ev.arb_percentage = ap
            ev.match = d.get('match') or d.get('event')
            ev.league = d.get('league')
            ev.market = d.get('market')
            ev.payload = d
            db.commit()
            # Add drop_event_id to data for bet tracking
            d['drop_event_id'] = ev.id
            try:
                print(f"💾 DEBUG: Stored drop {eid} with id={ev.id} (arb%={ev.arb_percentage})")
            except Exception:
                pass
    except Exception:
        db.rollback()
    finally:
        db.close()
    
    # Debug: show duplicate state and flag
    try:
        print(f"🔧 DEBUG: receive_drop is_duplicate={is_duplicate}, ALLOW_DUPLICATE_SEND={ALLOW_DUPLICATE_SEND}")
    except Exception:
        pass

    # Skip sending if duplicate unless debug flag enabled
    if is_duplicate and not ALLOW_DUPLICATE_SEND:
        try:
            print("🔧 DEBUG: Skipping send_arbitrage_alert_to_users because duplicate and ALLOW_DUPLICATE_SEND=0")
        except Exception:
            pass
        return {"ok": True, "skipped": "duplicate"}
    
    # ✅ Ensure drop_event_id is present (already set above for duplicates, set here for new drops)
    if 'drop_event_id' not in d and existing_drop_id:
        d['drop_event_id'] = existing_drop_id
    
    # Send to users
    try:
        print("🚀 DEBUG: Calling send_arbitrage_alert_to_users")
    except Exception:
        pass
    await send_arbitrage_alert_to_users(d)
    
    # Also send full alert to admin as PREMIUM (no extra info line) when explicitly enabled
    if ADMIN_CHAT_ID and DEBUG_ADMIN_PREVIEW:
        # Send full alert to admin as PREMIUM to include all buttons
        try:
            print(f"👑 DEBUG: Sending admin preview to {ADMIN_CHAT_ID}")
            await send_alert_to_user(int(ADMIN_CHAT_ID), TierLevel.PREMIUM, d)
        except Exception as e:
            print(f"❌ ERROR: Failed to send admin preview: {e}")
    
    # ⚡ APRÈS envoi: générer parlays en background (non-bloquant)
    if drop_id:
        try:
            asyncio.create_task(asyncio.to_thread(on_drop_received, drop_id))
        except Exception:
            pass  # Don't block if parlay generation fails
    
    return {"ok": True}


@app.post("/public/email")
async def receive_email(req: Request):
    """
    Receive email notification from source bot
    Parse and distribute to users
    """
    payload = await req.json()
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    
    # Gating: only process expected notifications
    subj = (subject or "").strip()
    if not (subj.startswith("Arbitrage Bet Notification:") or subj.startswith("Arbitrage Bet Notifcation:")):
        return {"ok": False, "reason": "subject_mismatch"}
    
    # Extract using AI parser (existing)
    drop = extract_from_email(subject, body)
    eid = drop.get("event_id")
    if not eid:
        return {"ok": False, "error": "missing event_id after parse"}
    
    drop["received_at"] = datetime.now().isoformat()
    DROPS[eid] = drop
    try:
        drop_id = record_drop(drop)
        # ⚡ Parlays générés APRÈS envoi aux users (voir fin de fonction)
    except Exception:
        drop_id = None
    # Persist to DB for durability (prefer parsed fields if available)
    db = SessionLocal()
    try:
        ev = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        if not ev:
            ev = DropEvent(event_id=eid)
            db.add(ev)
        ev.received_at = datetime.now()
        src = None
        try:
            src = parse_arbitrage_alert(body) or drop
        except Exception:
            src = drop
        try:
            ev.arb_percentage = float((src or {}).get('arb_percentage') or drop.get('arb_percentage') or 0)
        except Exception:
            ev.arb_percentage = 0.0
        ev.match = (src or {}).get('match') or drop.get('match') or drop.get('event')
        ev.league = (src or {}).get('league') or drop.get('league')
        ev.market = (src or {}).get('market') or drop.get('market')
        ev.payload = src or drop
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    
    # Parse with new parser for standardized format
    # (The email body likely contains the raw alert text)
    parsed = parse_arbitrage_alert(body)
    
    if parsed:
        # Normalize arb percentage to float for gating logic
        try:
            parsed["arb_percentage"] = float(parsed.get("arb_percentage") or 0)
        except Exception:
            parsed["arb_percentage"] = 0.0
        # Send to users using new system
        await send_arbitrage_alert_to_users(parsed)
    
    # Generate image card (existing functionality)
    try:
        img_path = generate_card(drop)
        
        # Send to admin with image
        if ADMIN_CHAT_ID:
            try:
                with open(img_path, "rb") as f:
                    await bot.send_photo(
                        chat_id=ADMIN_CHAT_ID,
                        photo=f,
                        caption=f"📧 Email Alert\n{drop.get('match', 'Unknown')}",
                        parse_mode=ParseMode.HTML
                    )
            except:
                pass
    except:
        pass
    
    # ⚡ APRÈS envoi: générer parlays en background (non-bloquant)
    if drop_id:
        try:
            asyncio.create_task(asyncio.to_thread(on_drop_received, drop_id))
        except Exception:
            pass  # Don't block if parlay generation fails
    
    return {"ok": True, "event_id": eid}


@app.post("/api/oddsjam/positive_ev")
async def handle_positive_ev(req: Request):
    """
    Receive Positive EV (Good Odds) notification from Tasker
    Send to all PREMIUM users who have enable_good_odds=True
    
    AUTO-ROUTING: If text contains 'Arbitrage Alert', route to arbitrage handler
    """
    try:
        data = await req.json()
        notif_text = data.get('text', '')
        
        if not notif_text:
            return {"status": "error", "message": "Missing text"}
        
        # 🔥 AUTO-DETECT: If this is an Arbitrage Alert, route to correct handler
        # Check for "Arbitrage Alert" specifically, not just emoji (which all alerts have)
        if "Arbitrage Alert" in notif_text:
            logger.info(f"🔄 Auto-routing Arbitrage Alert from /positive_ev to arbitrage handler")
            from utils.oddsjam_parser import parse_arbitrage_from_text
            arb_data = parse_arbitrage_from_text(notif_text)
            if arb_data:
                await send_arbitrage_alert_to_users(arb_data)
                return {"status": "success", "type": "arbitrage_routed"}
            else:
                logger.error(f"Failed to parse routed arbitrage: {notif_text}")
                return {"status": "error", "message": "Failed to parse arbitrage"}
        
        # Import parser
        from utils.oddsjam_parser import parse_positive_ev_notification
        from utils.oddsjam_formatters import format_good_odds_message
        from utils.odds_api_links import get_links_for_drop, get_fallback_url
        from utils.ev_quality import get_user_profile, SYSTEM_MIN_EV
        from utils.odds_enricher import enrich_alert_with_api
        
        # Parse notification
        parsed = parse_positive_ev_notification(notif_text)
        
        if not parsed:
            logger.error(f"Failed to parse Positive EV: {notif_text}")
            return {"status": "error", "message": "Failed to parse"}
        
        # Enrichir avec les données API SEULEMENT si EV >= 10% (pour économiser l'API)
        try:
            ev_percent = float(parsed.get('ev_percent', 0))
            if ev_percent >= 10.0:
                logger.info(f"Good EV {ev_percent}% >= 10%, enriching with API")
                enriched = enrich_alert_with_api(parsed, 'good_ev')
                if enriched:
                    parsed = enriched
                else:
                    logger.warning("API enrichment returned None for Good EV, using original data")
            else:
                logger.info(f"Good EV {ev_percent}% < 10%, skipping API enrichment to save quota")
                # Remove any existing commence_time or formatted_time to prevent date display for low EV
                parsed.pop('commence_time', None)
                parsed.pop('formatted_time', None)
        except Exception as e:
            logger.error(f"API enrichment failed for Good EV: {e}, using original data")
            # Remove dates on API failure too
            parsed.pop('commence_time', None)
            parsed.pop('formatted_time', None)
        
        # Store last Good Odds call (in-memory store for old menu)
        try:
            push_good_odds(parsed)
        except Exception:
            pass

        # Persist Good EV drop in DropEvent so Last Calls Pro can load it
        try:
            eid = hashlib.sha256(notif_text.encode('utf-8')).hexdigest()[:32]
            drop_record = {
                'event_id': eid,
                'bet_type': 'good_ev',
                'arb_percentage': float(parsed.get('ev_percent') or 0.0),
                'match': f"{parsed.get('team1','')} vs {parsed.get('team2','')}",
                'league': parsed.get('league'),
                'market': parsed.get('market'),
                # Store full parsed data for calculator/CASHH changes
                'bookmaker': parsed.get('bookmaker'),
                'selection': parsed.get('selection'),
                'player': parsed.get('player'),  # 🎯 NOM DU JOUEUR pour parlays!
                'odds': parsed.get('odds'),
                'ev_percent': float(parsed.get('ev_percent') or 0.0),
                'team1': parsed.get('team1'),
                'team2': parsed.get('team2'),
                # Match time from API enrichment
                'formatted_time': parsed.get('formatted_time'),
                'commence_time': parsed.get('commence_time'),
                # Build outcomes array so casino filters & details view work
                'outcomes': [
                    {
                        'casino': parsed.get('bookmaker'),
                        'outcome': parsed.get('selection'),
                        'odds': parsed.get('odds'),
                    }
                ],
            }
            # Store in-memory for Change CASHH / Calculator
            DROPS[eid] = drop_record
            # Persist to DB for Last Calls
            drop_id = record_drop(drop_record)
            # ⚡ Parlays générés APRÈS envoi aux users (non-bloquant)
        except Exception as e:
            logger.error(f"Failed to record Good EV drop: {e}")
            drop_id = None
        
        # Check if EV meets system minimum
        try:
            ev_percent = float(parsed['ev_percent'])
            if ev_percent < SYSTEM_MIN_EV:
                logger.info(f"EV {ev_percent}% below system minimum ({SYSTEM_MIN_EV}%), skipping")
                return {"status": "skipped", "reason": "ev_too_low"}
        except:
            ev_percent = 0.0
        
        # DEDUPLICATION CHECK - Block duplicate Good EV calls
        if is_duplicate_call(parsed):
            logger.warning(f"🚫 GOOD EV DUPLICATE BLOCKED: {parsed.get('match', 'Unknown')} - {parsed.get('ev_percent', 0)}%")
            return {"status": "duplicate", "message": "Duplicate call blocked"}
        
        # Get users with Good EV enabled
        # NOTE: We do NOT filter by tier in SQL to avoid Enum mismatch between
        # core.tiers.TierLevel and models.user.TierLevel. Instead, we filter
        # tier in Python below (only non-FREE users receive alerts).
        db = SessionLocal()
        try:
            logger.info("\n" + "="*60)
            logger.info("🔔 GOOD EV ALERT - Starting to query users...")
            logger.info("Filtering: enable_good_odds=True, is_banned=False, notifications_enabled=True")
            users = db.query(User).filter(
                User.enable_good_odds == True,
                User.is_banned == False,
                User.notifications_enabled == True,
            ).all()
            logger.info(f"✅ Found {len(users)} users matching Good EV filters")
            if len(users) == 0:
                logger.warning("⚠️ NO USERS have enable_good_odds=True! No one will receive this alert.")
            
            sent_count = 0
            for user in users:
                try:
                    # Check if user's tier can receive Good EV alerts
                    def _core_tier_from_model(t):
                        try:
                            name = t.name.lower()
                        except Exception:
                            return TierLevel.FREE
                        return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE
                    
                    tier_core = _core_tier_from_model(user.tier)
                    
                    # Check subscription is active (don't downgrade lifetime!)
                    logger.info(f"🔍 Good EV: User {user.telegram_id} tier={user.tier.name}, sub_end={user.subscription_end}, sub_active={user.subscription_active}")
                    if tier_core != TierLevel.FREE and not user.subscription_active:
                        logger.warning(f"⚠️ Good EV: User {user.telegram_id} subscription expired, skipping")
                        continue
                    
                    features = TierManager.get_features(tier_core)
                    
                    if not features.get('can_receive_good_ev', False):
                        logger.warning(f"🚫 BLOCKED: User {user.telegram_id} tier {tier_core.name} cannot receive Good Odds")
                        continue
                    # Check user's custom percentage filter for Good +EV
                    user_min_ev = user.min_good_ev_percent or 0.5
                    user_max_ev = user.max_good_ev_percent or 100.0
                    if not (user_min_ev <= ev_percent <= user_max_ev):
                        continue
                    
                    # Check casino filter
                    bookmaker = parsed.get('bookmaker', '')
                    if not user_passes_casino_filter(user, [bookmaker]):
                        logger.info(f"🎰 Good EV: User {user.telegram_id} SKIPPED - casino filter (bookmaker: {bookmaker})")
                        continue
                    
                    # Check sport filter
                    sport = parsed.get('sport', '') or parsed.get('league', '')
                    if not user_passes_sport_filter(user, sport):
                        logger.info(f"🏅 Good EV: User {user.telegram_id} SKIPPED - sport filter (sport: {sport})")
                        continue
                    
                    # Check "Match Today Only" filter
                    if getattr(user, 'match_today_only', False):
                        commence_time_iso = parsed.get('commence_time')
                        if commence_time_iso:
                            try:
                                from datetime import datetime, date, timezone
                                dt = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
                                match_date = dt.date()
                                today_date = date.today()
                                
                                if match_date != today_date:
                                    logger.info(f"🔍 Good EV: User {user.telegram_id} SKIPPED - match not today (match: {match_date}, today: {today_date})")
                                    continue
                            except Exception as e:
                                logger.warning(f"⚠️ WARNING: Could not parse commence_time for Good EV match today filter: {e}")
                                # If can't parse, let it through
                    
                    user_cash = user.default_bankroll
                    
                    # Determine user profile based on total_bets
                    # For now use total_bets as proxy (later can track good_odds_bets separately)
                    total_bets = user.total_bets or 0
                    user_profile = get_user_profile(total_bets)
                    
                    message = format_good_odds_message(parsed, user_cash, user.language, user_profile, total_bets)
                    
                    # Recommended stake based on EV quality tiers
                    # <8% => 1%, 8-12% => 2%, 12-18% => 3.5%, >=18% => 5%
                    if ev_percent >= 18.0:
                        rec_ratio = 0.05
                    elif ev_percent >= 12.0:
                        rec_ratio = 0.035
                    elif ev_percent >= 8.0:
                        rec_ratio = 0.02
                    else:
                        rec_ratio = 0.01
                    rec_stake = round(user_cash * rec_ratio, 2)
                    my_stake = round(user_cash, 2)
                    
                    # Calculate TRUE profit if you WIN (not just EV)
                    try:
                        odds_value = parsed.get('odds', 0)
                        if odds_value > 0:  # American odds positive
                            decimal_odds = 1 + (odds_value / 100)
                        else:  # American odds negative
                            decimal_odds = 1 + (100 / abs(odds_value))
                        rec_ev_profit = round(rec_stake * (decimal_odds - 1), 2)
                        my_ev_profit = round(my_stake * (decimal_odds - 1), 2)
                    except:
                        # Fallback to old EV calculation if odds parsing fails
                        rec_ev_profit = round(rec_stake * (ev_percent/100.0), 2)
                        my_ev_profit = round(my_stake * (ev_percent/100.0), 2)
                    
                    # Build keyboard - unified layout like arbitrage
                    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    # UTILISER les deep_links DÉJÀ enrichis!
                    deep_links = parsed.get('deep_links', {})
                    bookmaker_url = deep_links.get(parsed.get('bookmaker')) or get_fallback_url(parsed.get('bookmaker'))
                    
                    # Create unique call_id for Good Odds (for Verify Odds / persistence)
                    import uuid
                    call_id = str(uuid.uuid4())[:8]
                    
                    # Store Good Odds data in PENDING_CALLS for verification
                    from dataclasses import dataclass
                    @dataclass
                    class GoodEVCall:
                        call_id: str
                        data: dict
                        user_cash: float
                    
                    goodev_call = GoodEVCall(
                        call_id=call_id,
                        data=parsed,
                        user_cash=user_cash
                    )
                    PENDING_CALLS[call_id] = goodev_call
                    
                    # Use recommended stake for JE PARIE button
                    # NOTE: For per-call CASHH changes and calculator flows we reuse
                    # the same mechanisms as arbitrage, keyed by the event_id `eid`.
                    keyboard = [
                        # Row 1: Casino button
                        [InlineKeyboardButton(
                            text=f"{get_casino_logo(parsed['bookmaker'])} {parsed['bookmaker']}",
                            url=bookmaker_url
                        )],
                        # Row 2: JE PARIE button (using recommended stake)
                        [InlineKeyboardButton(
                            text=(f"💰 I BET (+${rec_ev_profit:.2f} if win)" if user.language == 'en' else f"💰 JE PARIE (+${rec_ev_profit:.2f} profit)"),
                            callback_data=f"good_ev_bet_{eid}_{rec_stake:.2f}_{rec_ev_profit:.2f}"
                        )],
                        # Row 3: Calculator Custom (unified system)
                        [InlineKeyboardButton(
                            text=("🧮 Custom Calculator" if user.language == 'en' else "🧮 Calculateur Custom"),
                            callback_data=f"calc_{eid}|menu"
                        )],
                        # Row 4: Simulation & Risk
                        [InlineKeyboardButton(
                            text=("📊 Simulation & Risk" if user.language == 'en' else "📊 Simulation & Risque"),
                            callback_data=f"sim_{eid}"
                        )],
                        # Row 5: Change CASHH (per-call, like arbitrage)
                        [InlineKeyboardButton(
                            text=("💰 Change CASHH" if user.language == 'en' else "💰 Changer CASHH"),
                            callback_data=f"chg_cashh_{eid}"
                        )],
                        # Row 6: Verify Odds - Real-time verification via The Odds API
                        [InlineKeyboardButton(
                            text=("🔍 Verify Odds" if user.language == 'en' else "🔍 Vérifier Cotes"),
                            callback_data=f"verify_goodev_{eid}"
                        )]
                    ]
                    
                    msg_sent = await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                        parse_mode=ParseMode.HTML,
                        protect_content=True  # Prevent forwarding and copying
                    )
                    sent_count += 1
                    logger.info(f"✅ Good EV sent successfully to {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to send Good Odds to user {user.telegram_id}: {e}")
                    # Log full traceback for debugging
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                logger.info(f"Good Odds alert sent to {sent_count} users")
            except Exception:
                print(f"Good Odds alert sent to {sent_count} users")
            
            # ⚡ APRÈS envoi: générer parlays en background (non-bloquant)
            if drop_id:
                try:
                    asyncio.create_task(asyncio.to_thread(on_drop_received, drop_id))
                except Exception:
                    pass  # Don't block if parlay generation fails
            
            return {"status": "success", "sent": sent_count}
            
        finally:
            db.close()
            
    except Exception as e:
        try:
            logger.error(f"Error in handle_positive_ev: {e}")
        except Exception:
            print(f"Error in handle_positive_ev: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/oddsjam/middle")
async def handle_middle(req: Request):
    """
    Receive Middle notification from Tasker
    Send to all PREMIUM users who have enable_middle=True
    """
    try:
        data = await req.json()
        notif_text = data.get('text', '')
        
        if not notif_text:
            return {"status": "error", "message": "Missing text"}
        
        # Import parser
        from utils.oddsjam_parser import parse_middle_notification, calculate_middle_stakes, parse_arbitrage_from_text
        from utils.oddsjam_formatters import format_middle_message
        from utils.odds_api_links import get_fallback_url
        
        # Detect if it's a pure arbitrage alert (coming from Tasker/bridge)
        # We keep real "Middle Alert" notifications on the dedicated middle pipeline
        is_arbitrage = "Arbitrage Alert" in notif_text
        
        if is_arbitrage:
            # Use new enriched system for arbitrages
            try:
                arb_data = parse_arbitrage_from_text(notif_text)
                if not arb_data:
                    logger.error(f"Failed to parse Arbitrage: {notif_text}")
                    return {"status": "error", "message": "Failed to parse arbitrage"}
                
                # Send via the standard arbitrage flow
                await send_arbitrage_alert_to_users(arb_data)
                return {"status": "success", "type": "arbitrage"}
            except Exception as e:
                logger.error(f"Failed to process arbitrage: {e}")
                return {"status": "error", "message": str(e)}
        
        # Otherwise parse as true Middle
        parsed = parse_middle_notification(notif_text)
        
        if not parsed:
            logger.error(f"Failed to parse Middle: {notif_text}")
            return {"status": "error", "message": "Failed to parse"}
        
        # Enrichir avec les données API SEULEMENT si middle >= 1% (pour économiser l'API)
        try:
            middle_percent = float(parsed.get('middle_percent', 0))
            if middle_percent >= 1.0:
                logger.info(f"Middle {middle_percent}% >= 1%, enriching with API")
                enriched = enrich_alert_with_api(parsed, 'middle')
                if enriched:
                    parsed = enriched
                else:
                    logger.warning("API enrichment returned None, using original data")
            else:
                logger.info(f"Middle {middle_percent}% < 1%, skipping API enrichment to save quota")
                # Remove any existing commence_time or formatted_time to prevent date display for low% middle
                parsed.pop('commence_time', None)
                parsed.pop('formatted_time', None)
        except Exception as e:
            logger.error(f"API enrichment failed: {e}, using original data")
            # Remove dates on API failure too
            parsed.pop('commence_time', None)
            parsed.pop('formatted_time', None)
        
        # Store last Middle call (in-memory store for old menu)
        try:
            push_middle(parsed)
        except Exception:
            pass

        # Persist Middle drop in DropEvent so Last Calls Pro can load it
        try:
            eid = hashlib.sha256(notif_text.encode('utf-8')).hexdigest()[:32]
            middle_pct = float(parsed.get('middle_percent') or 0.0)
            drop_record = {
                'event_id': eid,
                'bet_type': 'middle',
                'arb_percentage': middle_pct,
                'match': f"{parsed.get('team1','')} vs {parsed.get('team2','')}",
                'league': parsed.get('league'),
                'market': parsed.get('market'),
                'team1': parsed.get('team1'),
                'team2': parsed.get('team2'),
                'middle_percent': middle_pct,
                'side_a': parsed.get('side_a'),
                'side_b': parsed.get('side_b'),
                # Match time from API enrichment
                'formatted_time': parsed.get('formatted_time'),
                'commence_time': parsed.get('commence_time'),
                # Standard outcomes array for filters/details
                'outcomes': [
                    {
                        'casino': parsed['side_a']['bookmaker'],
                        'outcome': f"{parsed['side_a']['team']} {parsed['side_a']['line']}",
                        'odds': parsed['side_a']['odds'],
                    },
                    {
                        'casino': parsed['side_b']['bookmaker'],
                        'outcome': f"{parsed['side_b']['team']} {parsed['side_b']['line']}",
                        'odds': parsed['side_b']['odds'],
                    },
                ],
            }
            # Store in-memory for Change CASHH / Calculator
            DROPS[eid] = drop_record
            # Persist to DB for Last Calls
            drop_id = record_drop(drop_record)
            # ⚡ Parlays générés APRÈS envoi aux users (non-bloquant)
        except Exception as e:
            logger.error(f"Failed to record Middle drop: {e}")
            drop_id = None
        
        # DEDUPLICATION CHECK - Block duplicate Middle calls
        if is_duplicate_call(parsed):
            logger.warning(f"🚫 MIDDLE DUPLICATE BLOCKED: {parsed.get('match', 'Unknown')} - {parsed.get('middle_percent', 0)}%")
            return {"status": "duplicate", "message": "Duplicate call blocked"}
        
        # Get users with Middle enabled (filter tier in Python to avoid Enum DB mismatch)
        db = SessionLocal()
        try:
            logger.info("\n" + "="*60)
            logger.info("🔔 MIDDLE ALERT - Starting to query users...")
            logger.info("Filtering: enable_middle=True, is_banned=False, notifications_enabled=True")
            users = db.query(User).filter(
                User.enable_middle == True,
                User.is_banned == False,
                User.notifications_enabled == True
            ).all()
            logger.info(f"✅ Found {len(users)} users matching Middle filters")
            if len(users) == 0:
                logger.warning("⚠️ NO USERS have enable_middle=True! No one will receive this alert.")
            
            sent_count = 0
            for user in users:
                try:
                    # Check if user's tier can receive Middle alerts
                    def _core_tier_from_model(t):
                        try:
                            name = t.name.lower()
                        except Exception:
                            return TierLevel.FREE
                        return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE
                    
                    tier_core = _core_tier_from_model(user.tier)
                    
                    # Check subscription is active (don't downgrade lifetime!)
                    logger.info(f"🔍 Middle: User {user.telegram_id} tier={user.tier.name}, sub_end={user.subscription_end}, sub_active={user.subscription_active}")
                    if tier_core != TierLevel.FREE and not user.subscription_active:
                        logger.warning(f"⚠️ Middle: User {user.telegram_id} subscription expired, skipping")
                        continue
                    
                    features = TierManager.get_features(tier_core)
                    
                    if not features.get('can_receive_middle', False):
                        logger.warning(f"🚫 BLOCKED: User {user.telegram_id} tier {tier_core.name} cannot receive Middle")
                        continue
                    
                    # Check user's custom percentage filter for Middle
                    middle_percent = float(parsed.get('middle_percent', 0))
                    user_min_middle = user.min_middle_percent or 0.5
                    user_max_middle = user.max_middle_percent or 100.0
                    if not (user_min_middle <= middle_percent <= user_max_middle):
                        continue
                    
                    # Check casino filter (both sides of middle)
                    bookmaker_a = parsed.get('side_a', {}).get('bookmaker', '')
                    bookmaker_b = parsed.get('side_b', {}).get('bookmaker', '')
                    if not user_passes_casino_filter(user, [bookmaker_a, bookmaker_b]):
                        logger.info(f"🎰 Middle: User {user.telegram_id} SKIPPED - casino filter (casinos: {bookmaker_a}, {bookmaker_b})")
                        continue
                    
                    # Check sport filter
                    sport = parsed.get('sport', '') or parsed.get('league', '')
                    if not user_passes_sport_filter(user, sport):
                        logger.info(f"🏅 Middle: User {user.telegram_id} SKIPPED - sport filter (sport: {sport})")
                        continue
                    
                    # Check "Match Today Only" filter
                    if getattr(user, 'match_today_only', False):
                        commence_time_iso = parsed.get('commence_time')
                        if commence_time_iso:
                            try:
                                from datetime import datetime, date, timezone
                                dt = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
                                match_date = dt.date()
                                today_date = date.today()
                                
                                if match_date != today_date:
                                    logger.info(f"🔍 Middle: User {user.telegram_id} SKIPPED - match not today (match: {match_date}, today: {today_date})")
                                    continue
                            except Exception as e:
                                logger.warning(f"⚠️ WARNING: Could not parse commence_time for Middle match today filter: {e}")
                                # If can't parse, let it through
                    
                    user_cash = user.default_bankroll
                    user_rounding = user.stake_rounding or 0
                    
                    # Calculate stakes with user's rounding preference
                    calc = calculate_middle_stakes(
                        parsed['side_a']['odds'],
                        parsed['side_b']['odds'],
                        user_cash,
                    )
                    # Recommended total stake for Middle (default 2% of bankroll)
                    rec_stake = round(user_cash * 0.02, 2)
                    rec_calc = calculate_middle_stakes(
                        parsed['side_a']['odds'],
                        parsed['side_b']['odds'],
                        rec_stake,
                    )
                    
                    message = format_middle_message(parsed, calc, user_cash, user.language, user_rounding)
                    
                    # Build keyboard - unified layout like arbitrage
                    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    # UTILISER les deep_links DÉJÀ enrichis!
                    deep_links = parsed.get('deep_links', {})
                    bookmaker_a_url = deep_links.get(parsed['side_a']['bookmaker']) or get_fallback_url(parsed['side_a']['bookmaker'])
                    bookmaker_b_url = deep_links.get(parsed['side_b']['bookmaker']) or get_fallback_url(parsed['side_b']['bookmaker'])
                    
                    # Create unique call_id for Middle
                    import uuid
                    call_id = str(uuid.uuid4())[:8]
                    
                    # Store Middle data in PENDING_CALLS for verification
                    from dataclasses import dataclass
                    @dataclass
                    class MiddleCall:
                        call_id: str
                        data: dict
                        user_cash: float
                    
                    middle_call = MiddleCall(
                        call_id=call_id,
                        data=parsed,
                        user_cash=user_cash
                    )
                    PENDING_CALLS[call_id] = middle_call
                    
                    # Use recommended stake for JE PARIE button
                    # NOTE: For per-call CASHH changes and calculator flows we
                    # reuse the same mechanisms as arbitrage, keyed by `eid`.
                    keyboard = [
                        # Row 1: Casino buttons (2 casinos for middle)
                        [
                            InlineKeyboardButton(
                                text=f"{get_casino_logo(parsed['side_a']['bookmaker'])} {parsed['side_a']['bookmaker']}",
                                url=bookmaker_a_url
                            ),
                            InlineKeyboardButton(
                                text=f"{get_casino_logo(parsed['side_b']['bookmaker'])} {parsed['side_b']['bookmaker']}",
                                url=bookmaker_b_url
                            )
                        ],
                        # Row 2: JE PARIE button (using FULL bankroll to match message)
                        [InlineKeyboardButton(
                            text=(f"💰 I BET (${calc['no_middle_profit']:.2f} profit)" if user.language == 'en' else f"💰 JE PARIE (${calc['no_middle_profit']:.2f} profit)"),
                            callback_data=f"middle_bet_{eid}_{calc['total_stake']:.2f}_{calc['no_middle_profit']:.2f}_{calc['middle_profit']:.2f}"
                        )],
                        # Row 3: Calculator Custom (unified system)
                        [InlineKeyboardButton(
                            text=("🧮 Custom Calculator" if user.language == 'en' else "🧮 Calculateur Custom"),
                            callback_data=f"calc_{eid}|menu"
                        )],
                        # Row 4: Simulation & Risk
                        [InlineKeyboardButton(
                            text=("📊 Simulation & Risk" if user.language == 'en' else "📊 Simulation & Risque"),
                            callback_data=f"sim_{eid}"
                        )],
                        # Row 5: Change CASHH (per-call, like arbitrage)
                        [InlineKeyboardButton(
                            text=("💰 Change CASHH" if user.language == 'en' else "💰 Changer CASHH"),
                            callback_data=f"chg_cashh_{eid}"
                        )],
                        # Row 6: Verify Odds - Real-time verification via The Odds API
                        [InlineKeyboardButton(
                            text=("🔍 Verify Odds" if user.language == 'en' else "🔍 Vérifier Cotes"),
                            callback_data=f"verify_middle_{eid}"
                        )]
                    ]
                    
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                        parse_mode=ParseMode.HTML,
                        protect_content=True  # Prevent forwarding and copying
                    )
                    sent_count += 1
                    logger.info(f"✅ Middle sent successfully to {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to send Middle to user {user.telegram_id}: {e}")
                    # Log full traceback for debugging
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                logger.info(f"Middle alert sent to {sent_count} users")
            except Exception:
                print(f"Middle alert sent to {sent_count} users")
            
            # ⚡ APRÈS envoi: générer parlays en background (non-bloquant)
            if drop_id:
                try:
                    asyncio.create_task(asyncio.to_thread(on_drop_received, drop_id))
                except Exception:
                    pass  # Don't block if parlay generation fails
            
            return {"status": "success", "sent": sent_count}
            
        finally:
            db.close()
            
    except Exception as e:
        try:
            logger.error(f"Error in handle_middle: {e}")
        except Exception:
            print(f"Error in handle_middle: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/webhook/nowpayments")
async def nowpayments_webhook(request: Request, x_nowpayments_sig: str = Header(None)):
    """
    NOWPayments IPN webhook to auto-activate PREMIUM after payment.
    Validates signature, activates the user, sends welcome, and re-sends recent drops.
    """
    try:
        raw = await request.body()
        logger.info(f"🔔 NOWPayments webhook received! Signature: {x_nowpayments_sig}")
        
        if not NOWPaymentsManager.verify_ipn_signature(raw, x_nowpayments_sig):
            logger.error("❌ Webhook signature validation failed!")
            return {"status": "error", "message": "invalid_signature"}
        
        logger.info("✅ Webhook signature validated!")
        data = await request.json()
        logger.info(f"📦 Webhook data: {data}")
    except Exception as e:
        logger.error(f"❌ Error parsing webhook: {e}")
        return {"status": "error", "message": str(e)}
    status = (data.get("payment_status") or data.get("status") or "").lower()
    logger.info(f"💰 Payment status: {status}")
    
    if status not in ("finished", "confirmed", "confirmed_partial"):  # accept common success statuses
        logger.warning(f"⚠️ Ignoring payment with status: {status}")
        return {"status": "ignored", "payment_status": status}

    order_id = data.get("order_id") or ""
    logger.info(f"📄 Order ID: {order_id}")
    
    telegram_id = None
    if isinstance(order_id, str) and order_id.startswith("premium_"):
        parts = order_id.split("_")
        if len(parts) >= 3 and parts[1].isdigit():
            telegram_id = int(parts[1])
            logger.info(f"✅ Telegram ID extracted from order_id: {telegram_id}")

    # Fallback via invoice mapping if available
    if telegram_id is None:
        invoice_id = str(data.get("invoice_id") or data.get("id") or "")
        logger.info(f"🔍 Trying to find telegram_id via invoice_id: {invoice_id}")
        try:
            from bot.nowpayments_handler import PAYMENT_MAP
            telegram_id = PAYMENT_MAP.get(invoice_id)
            if telegram_id:
                logger.info(f"✅ Telegram ID found in PAYMENT_MAP: {telegram_id}")
        except Exception as e:
            logger.error(f"❌ Error accessing PAYMENT_MAP: {e}")
            telegram_id = None

    if not telegram_id:
        logger.error("❌ Could not find telegram_id from webhook data!")
        return {"status": "error", "message": "telegram_id_not_found"}

    logger.info(f"🚀 Activating PREMIUM for user {telegram_id}...")
    
    # Activate PREMIUM
    ok = NOWPaymentsManager.activate_premium(telegram_id)
    if not ok:
        logger.error(f"❌ Failed to activate PREMIUM for user {telegram_id}")
        return {"status": "error", "message": "user_not_found"}
    
    logger.info(f"✅ User {telegram_id} activated to PREMIUM!")

    # Determine payment amount (fallback to configured price)
    try:
        price_amount = float(data.get("price_amount") or data.get("order_amount") or 0)
    except Exception:
        price_amount = 0.0
    if price_amount <= 0:
        try:
            price_amount = float(TierManager.get_price(TierLevel.PREMIUM))
        except Exception:
            price_amount = 200.0
    
    # Check if payment was with bonus (price = 150) and mark as redeemed
    if price_amount == 150.0:
        try:
            from bot.bonus_handler import BonusManager
            BonusManager.redeem_bonus(telegram_id)
            logger.info(f"✅ Bonus redeemed for user {telegram_id} after payment")
        except Exception as e:
            logger.error(f"Error redeeming bonus for {telegram_id}: {e}")

    # Send welcome + compute and distribute referral commissions
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        lang = (user.language if user else "en") or "en"
        paying_username = f"@{(user.username or 'N/A')}" if user else f"<code>{telegram_id}</code>"
        # Reactivate referral (if previously canceled) and distribute commissions
        try:
            ReferralManager.reactivate_referral(db, telegram_id, TierLevel.PREMIUM)
        except Exception:
            pass
        result = ReferralManager.calculate_commission(db, telegram_id, float(price_amount), TierLevel.PREMIUM)
        # Prepare notifications to referrers
        tier1_text = None
        tier2_text = None
        if result.get("tier1_commission") and result.get("tier1_referrer_id"):
            r1 = db.query(User).filter(User.telegram_id == result["tier1_referrer_id"]).first()
            r1_lang = (r1.language if r1 else "en") or "en"
            amount = result["tier1_commission"]
            tier1_text = (
                f"🎁 Ton filleul {paying_username} a payé PREMIUM. Tu gagnes <b>${amount:.2f}</b> (20%)."
                if r1_lang == "fr" else
                f"🎁 Your referral {paying_username} paid PREMIUM. You earned <b>${amount:.2f}</b> (20%)."
            )
        if result.get("tier2_commission") and result.get("tier2_referrer_id"):
            r2 = db.query(User).filter(User.telegram_id == result["tier2_referrer_id"]).first()
            r2_lang = (r2.language if r2 else "en") or "en"
            amount2 = result["tier2_commission"]
            tier2_text = (
                f"🎁 Referral 2e niveau: {paying_username} a payé PREMIUM. Tu gagnes <b>${amount2:.2f}</b> (10%)."
                if r2_lang == "fr" else
                f"🎁 Tier-2 referral: {paying_username} paid PREMIUM. You earned <b>${amount2:.2f}</b> (10%)."
            )
    finally:
        db.close()

    welcome_text = (
        "🎉 <b>Bienvenue en PREMIUM!</b>\n\n"
        "Tu as maintenant accès à TOUTES les alertes en temps réel, au mode RISKED, au calculateur, et aux stats avancées.\n\n"
        "<b>Important:</b> Lis le <b>/guide</b> complet (<b>5 minutes</b>) pour éviter $500+ d'erreurs, puis clique <b>I BET</b> après chaque arb.\n\n"
        "Je t'envoie les alertes récentes encore actives."
        if lang == "fr" else
        "🎉 <b>Welcome to PREMIUM!</b>\n\nYou now have access to ALL real-time alerts, RISKED mode, calculator, and advanced stats.\n\n"
        "<b>Important:</b> Read the complete <b>/guide</b> (<b>5 minutes</b>) to avoid $500+ mistakes, then click <b>I BET</b> after each arb.\n\n"
        "I'll send you recent active alerts."
    )
    try:
        await bot.send_message(chat_id=telegram_id, text=welcome_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    # Notify referrers if any
    try:
        if 'tier1_text' in locals() and tier1_text and result.get("tier1_referrer_id"):
            await bot.send_message(chat_id=int(result.get("tier1_referrer_id")), text=tier1_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        if 'tier2_text' in locals() and tier2_text and result.get("tier2_referrer_id"):
            await bot.send_message(chat_id=int(result.get("tier2_referrer_id")), text=tier2_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass

    # Re-send recent drops (last 24h, up to 10) from DB
    sent = 0
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(hours=24)
        events = (
            db.query(DropEvent)
            .filter(DropEvent.received_at >= cutoff)
            .order_by(DropEvent.received_at.desc())
            .limit(20)
            .all()
        )
        for ev in events:
            if sent >= 10:
                break
            try:
                await send_alert_to_user(telegram_id, TierLevel.PREMIUM, ev.payload)
                sent += 1
            except Exception:
                continue
    finally:
        db.close()

    return {"status": "success", "activated": True, "sent": sent}


@app.post("/admin/resend_last")
async def admin_resend_last():
    """
    Admin utility: resend the most recent stored drop to ADMIN_CHAT_ID as a full alert.
    Useful to test delivery without waiting for a live alert.
    """
    # Find the most recent by received_at
    if not DROPS:
        return {"ok": False, "error": "no_drops"}
    from dateutil import parser as dateparser
    recent = []
    for d in DROPS.values():
        ts = d.get("received_at")
        try:
            dt = dateparser.isoparse(ts) if ts else None
        except Exception:
            dt = None
        recent.append((dt, d))
    recent.sort(key=lambda x: x[0] or datetime.min, reverse=True)
    last = recent[0][1]
    # Send as PREMIUM to ensure full content for testing
    await send_alert_to_user(int(ADMIN_CHAT_ID), TierLevel.PREMIUM, last)
    return {"ok": True, "sent_event_id": last.get("event_id")}


# ===== Calculator & Risked Interactive Handlers =====

def _get_user_prefs(user_id: int) -> tuple[float, str, float]:
    """Get user preferences from database."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            return user.default_bankroll or 400.0, (user.language or "en"), (user.default_risk_percentage or 5.0)
        return 400.0, "en", 5.0
    finally:
        db.close()


def _get_user_rounding(user_id: int) -> tuple[int, str]:
    """Get user stake rounding preferences from database.
    Returns (rounding_level, rounding_mode)
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            rounding_level = user.stake_rounding or 0
            rounding_mode = getattr(user, 'rounding_mode', 'nearest') or 'nearest'
            return rounding_level, rounding_mode
        return 0, 'nearest'
    finally:
        db.close()


def _format_currency(x: float) -> str:
    return f"${x:.2f}"


def _format_arbitrage_message(drop: dict, bankroll: float, lang: str = 'en', user_rounding: int = 0, user_mode: str = 'nearest') -> tuple[str, list]:
    """
    Format arbitrage message consistently with original format.
    Returns (message_text, stakes_list)
    """
    from utils.stake_rounder import round_arbitrage_stakes
    
    # Calculate stakes
    odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
    calc = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
    stakes = calc.get('stakes', [0, 0])
    returns = calc.get('returns', [0, 0])
    profit = calc.get('profit', 0)
    roi_pct = (profit / bankroll * 100) if bankroll > 0 else 0
    arb_percentage = drop.get('arb_percentage', roi_pct)  # Use original % from drop
    
    # Apply user's stake rounding preference with CORRECT recalculation
    if user_rounding > 0 and len(stakes) == 2 and len(odds_list) == 2:
        rounded_result = round_arbitrage_stakes(
            stakes[0], stakes[1], 
            odds_list[0], odds_list[1], 
            bankroll, user_rounding, user_mode
        )
        
        if rounded_result:
            # Use rounded values for everything
            stakes = [rounded_result['stake_a'], rounded_result['stake_b']]
            returns = [rounded_result['return_a'], rounded_result['return_b']]
            profit = rounded_result['profit_guaranteed']
            roi_pct = rounded_result['roi_percent']
            # IMPORTANT: Update arb_percentage in message avec valeur RECALCULÉE
            arb_percentage = roi_pct
        # Si rounded_result est None, on garde les valeurs originales (arrondi a tué l'arb)
    
    # Build message with original format
    # IMPORTANT: Use recalculated arb_percentage (after rounding) not original
    if lang == 'fr':
        title_line = f"🚨 <b>ALERTE ARBITRAGE - {arb_percentage:.2f}%</b> 🚨\n\n"
        cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
        profit_line = f"✅ <b>Profit Garanti: ${profit:.2f}</b> (ROI: {roi_pct:.2f}%)\n\n"
        stake_label = "Miser"
        return_label = "Retour"
        warning = "⚠️ <b>Attention: les cotes peuvent changer - toujours vérifier avant de bet!</b>\n"
    else:
        title_line = f"🚨 <b>ARBITRAGE ALERT - {arb_percentage:.2f}%</b> 🚨\n\n"
        cashh_line = f"💰 <b>CASHH: ${bankroll}</b>\n"
        profit_line = f"✅ <b>Guaranteed Profit: ${profit:.2f}</b> (ROI: {roi_pct:.2f}%)\n\n"
        stake_label = "Stake"
        return_label = "Return"
        warning = "⚠️ <b>Odds can change - always verify before betting!</b>\n"
    
    # Extract time
    time_str = drop.get('formatted_time', '') or drop.get('commence_time', '') or drop.get('time', '')
    time_line = f"🕐 {time_str}\n" if time_str and time_str != 'TBD' else ""
    
    # Get correct sport emoji
    from utils.sport_emoji import get_sport_emoji
    sport_emoji = get_sport_emoji(drop.get('league',''), drop.get('sport',''))
    
    message_text = (
        title_line
        + f"🏟️ <b>{drop.get('match') or drop.get('event') or 'Match'}</b>\n"
        + f"{sport_emoji} {drop.get('league','')} - {drop.get('market','')}\n"
        + time_line
        + "\n"
        + cashh_line
        + profit_line
    )
    
    # Add each outcome
    for i, outcome_data in enumerate(drop.get('outcomes', [])[:2]):
        casino_name = outcome_data.get('casino','')
        logo = get_casino_logo(casino_name)
        odds_val = int(outcome_data.get('odds', 0))
        odds_str = f"+{odds_val}" if odds_val > 0 else str(odds_val)
        
        message_text += (
            f"{logo} <b>[{casino_name}]</b> {outcome_data.get('outcome','')}\n"
            f"💵 {stake_label}: <code>${stakes[i]:.2f}</code> ({odds_str}) → {return_label}: ${returns[i]:.2f}\n\n"
        )
    
    message_text += warning
    
    return message_text, stakes


def _get_drop(event_id: str) -> dict | None:
    logger.info(f"🔍 _get_drop called with event_id: {event_id}")
    
    # Try in-memory first
    d = DROPS.get(event_id)
    if d:
        logger.info(f"✅ Found in DROPS (memory): bet_type={d.get('bet_type', 'unknown')}")
        return d
    
    logger.info(f"⚠️ Not in DROPS, trying DB...")
    
    # Fallback to DB - try both event_id and numeric ID
    db = SessionLocal()
    try:
        # First try as event_id
        ev = db.query(DropEvent).filter(DropEvent.event_id == event_id).first()
        if ev:
            logger.info(f"✅ Found in DB by event_id: id={ev.id}, bet_type={ev.bet_type}")
            # For Middle and Good EV from DB, ensure payload has all needed fields
            payload = ev.payload or {}
            payload['bet_type'] = ev.bet_type
            payload['event_id'] = ev.event_id
            payload['drop_event_id'] = ev.id  # Add DB id for I BET button
            return payload
        
        # If numeric, try as database ID
        try:
            db_id = int(event_id)
            ev = db.query(DropEvent).filter(DropEvent.id == db_id).first()
            if ev:
                logger.info(f"✅ Found in DB by numeric ID: id={ev.id}, bet_type={ev.bet_type}")
                payload = ev.payload or {}
                payload['bet_type'] = ev.bet_type
                payload['event_id'] = ev.event_id
                payload['drop_event_id'] = ev.id
                return payload
            else:
                logger.warning(f"❌ Not found in DB with id={db_id}")
        except ValueError:
            logger.info(f"❌ Not numeric, not found: {event_id}")
            return None
    finally:
        db.close()
    
    logger.warning(f"❌ Drop not found anywhere for event_id: {event_id}")
    return None


def _extract_event_id(data: str, prefix: str) -> tuple[str, list[str]]:
    # Accept extra params separated by '|': prefix_eventid|param|param
    parts = data.split('|')
    base = parts[0]
    extras = parts[1:]
    eid = base[len(prefix):]
    return eid, extras


@calc_router.callback_query(F.data.startswith("risked_"))
async def cb_risked(callback: types.CallbackQuery):
    await safe_callback_answer(callback)
    data = callback.data or ""
    eid, extras = _extract_event_id(data, "risked_")
    drop = _get_drop(eid)
    if not drop:
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    bankroll, lang, default_risk = _get_user_prefs(callback.from_user.id)

    # Defaults
    favor = 0
    risk_pct = default_risk
    # Parse extras like f0, r5
    for e in extras:
        if e.startswith('f') and e[1:].isdigit():
            favor = int(e[1:])
        if e.startswith('r'):
            try:
                risk_pct = float(e[1:])
            except:
                pass
    
    # Clamp risk_pct to 0.5-99%
    risk_pct = max(0.5, min(99.0, risk_pct))

    odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
    if len(odds_list) != 2:
        await safe_callback_answer(callback, "❌ RISKED supporte seulement 2 issues", show_alert=True)
        return

    calc = ArbitrageCalculator.calculate_risked_stakes(
        bankroll=bankroll,
        odds_list=odds_list,
        risk_percentage=risk_pct,
        favor_outcome=favor,
    )

    out_a = drop['outcomes'][0]
    out_b = drop['outcomes'][1]
    stakes = calc.get('stakes', [0, 0])
    profits = calc.get('profits', [0, 0])
    ratio = calc.get('risk_reward_ratio', 0)
    risk_loss = calc.get('risk_loss', 0)
    max_profit = calc.get('max_profit', 0)

    title = "⚠️ Mode RISKED" if lang == 'fr' else "⚠️ RISKED Mode"
    txt = (
        f"{title} — favor {'A' if favor==0 else 'B'} — risk {risk_pct:.1f}%\n\n"
        f"A) {out_a['outcome']} @ {out_a['odds']} [{out_a.get('casino','')}]\n"
        f"   Stake: <code>{_format_currency(stakes[0])}</code> → Profit: {_format_currency(profits[0])}\n"
        f"B) {out_b['outcome']} @ {out_b['odds']} [{out_b.get('casino','')}]\n"
        f"   Stake: <code>{_format_currency(stakes[1])}</code> → Profit: {_format_currency(profits[1])}\n\n"
        f"Max profit: {_format_currency(max_profit)}  |  Risk loss: {_format_currency(risk_loss)}  |  R/R: {ratio}"
    )

    # Controls
    kb = [
        [
            InlineKeyboardButton(text=("Favor A" if lang!='fr' else "Favor A"), callback_data=f"risked_{eid}|f0|r{risk_pct}"),
            InlineKeyboardButton(text=("Favor B" if lang!='fr' else "Favor B"), callback_data=f"risked_{eid}|f1|r{risk_pct}"),
        ],
        [
            InlineKeyboardButton(text="-1%", callback_data=f"risked_{eid}|f{favor}|r{max(risk_pct-1, 0.5):.1f}"),
            InlineKeyboardButton(text="+1%", callback_data=f"risked_{eid}|f{favor}|r{min(risk_pct+1, 99):.1f}"),
        ],
        [
            InlineKeyboardButton(text=("🧮 SAFE" if lang!='fr' else "🧮 SAFE"), callback_data=f"calc_{eid}|safe"),
            InlineKeyboardButton(text=("🔁 Calculatrice" if lang=='fr' else "🔁 Calculator"), callback_data=f"calc_{eid}|menu"),
            InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data=f"alert_{eid}|risked|f{favor}|r{risk_pct}"),
        ],
    ]
    await callback.message.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(
    # Generic calculator menu handler for callbacks like
    #   calc_{eid}|menu, calc_{eid}|safe, calc_changecash_{eid}
    # but NOT RISKED flows (calc_risk*) or change odds (calc_changeodds_), which have dedicated handlers.
    lambda c: c.data
    and c.data.startswith("calc_")
    and not c.data.startswith("calc_risk")
    and not c.data.startswith("calc_changeodds_")
)
async def cb_calc_menu(callback: types.CallbackQuery):
    """🧮 NEW ULTRA-SIMPLE CALCULATOR - Main menu"""
    await safe_callback_answer(callback)
    data = callback.data or ""
    # Special-case: "calc_changecash_{eid}" from custom calculator menu → reuse
    # the unified per-call CASHH flow (show_cashh_menu) instead of treating
    # "changecash_{eid}" as the event_id (which would break _get_drop).
    if data.startswith("calc_changecash_"):
        try:
            # Data format: calc_changecash_{eid}
            eid = data.split("_", 2)[2]
        except Exception:
            await safe_callback_answer(
                callback,
                "❌ Erreur" if (_get_user_prefs(callback.from_user.id)[1] == "fr") else "❌ Error",
                show_alert=True,
            )
            return
        # Delegate to the shared CASHH menu (no extra mode params here)
        await show_cashh_menu(callback, eid, [])
        return

    eid, extras = _extract_event_id(data, "calc_")
    drop = _get_drop(eid)
    if not drop:
        await safe_callback_answer(callback, "❌ Drop expiré" if (_get_user_prefs(callback.from_user.id)[1]=='fr') else "❌ Drop expired", show_alert=True)
        return
    bankroll, lang, default_risk = _get_user_prefs(callback.from_user.id)
    
    # Parse mode from extras
    mode = 'menu'
    for e in extras:
        if e == 'menu':
            mode = 'menu'
            break
        elif e == 'safe':
            # Show SAFE calculation
            await show_calc_safe(callback, eid, drop, bankroll, lang)
            return
        elif e == 'risked':
            # Start RISKED flow
            await start_calc_risked(callback, eid, drop, lang)
            return
    
    # Default: show main menu
    # Detect bet type
    bet_type = drop.get('bet_type', 'arbitrage')
    outcomes = drop.get('outcomes', [])
    match = drop.get('match', '')
    market = drop.get('market', '')
    
    # For Good EV (only 1 outcome), show simplified menu
    if bet_type == 'good_ev':
        if not outcomes:
            await safe_callback_answer(callback, "❌ Données incomplètes", show_alert=True)
            return
        o1 = outcomes[0]
        if lang == 'fr':
            msg = (
                f"🧮 <b>CALCULATEUR GOOD ODDS</b>\n\n"
                f"<b>Match actuel:</b>\n"
                f"{match}\n"
                f"{market}\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n\n"
                f"<b>Que veux-tu faire?</b>"
            )
            kb = [
                [InlineKeyboardButton(text="✅ Recalculer EV avec mon CASHH", callback_data=f"calc_{eid}|safe")],
                [InlineKeyboardButton(text="💰 Tester différents montants", callback_data=f"calc_changecash_{eid}")],
                [InlineKeyboardButton(text="◀️ Retour à l'alerte", callback_data=f"back_to_main_{eid}")],
            ]
        else:
            msg = (
                f"🧮 <b>GOOD ODDS CALCULATOR</b>\n\n"
                f"<b>Current match:</b>\n"
                f"{match}\n"
                f"{market}\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n\n"
                f"<b>What do you want to do?</b>"
            )
            kb = [
                [InlineKeyboardButton(text="✅ Recalculate EV with my CASHH", callback_data=f"calc_{eid}|safe")],
                [InlineKeyboardButton(text="💰 Test different amounts", callback_data=f"calc_changecash_{eid}")],
                [InlineKeyboardButton(text="◀️ Back to alert", callback_data=f"back_to_main_{eid}")],
            ]
        await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    # For Middle and Arbitrage, need 2 outcomes
    if len(outcomes) < 2:
        await safe_callback_answer(callback, "❌ Données incomplètes", show_alert=True)
        return
    
    o1, o2 = outcomes[:2]
    
    token = _token_for_eid(eid)
    # Title and buttons change based on bet_type
    if bet_type == 'middle':
        title_fr = "🧮 <b>CALCULATEUR MIDDLE</b>"
        title_en = "🧮 <b>MIDDLE CALCULATOR</b>"
        desc_fr = "Recalcule le middle avec ton CASHH ou change les cotes pour voir si c'est toujours un jackpot.\n\n"
        desc_en = "Recalculate middle with your CASHH or change odds to see if it's still a jackpot.\n\n"
    else:
        title_fr = "🧮 <b>CALCULATEUR CUSTOM</b>"
        title_en = "🧮 <b>CUSTOM CALCULATOR</b>"
        desc_fr = "Entre les cotes des 2 côtés pour calculer l'arbitrage.\n\n"
        desc_en = "Enter odds for both sides to calculate arbitrage.\n\n"
    
    if lang == 'fr':
        msg = (
            f"{title_fr}\n\n"
            f"{desc_fr}"
            f"<b>Match actuel:</b>\n"
            f"{match}\n"
            f"{market}\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n\n"
            f"<b>Que veux-tu faire?</b>"
        )
        recalc_text = "✅ Recalculer avec mon CASHH" if bet_type != 'middle' else "✅ Recalculer le middle avec mon CASHH"
        kb = [
            [InlineKeyboardButton(text=recalc_text, callback_data=f"calc_{eid}|safe")],
            [InlineKeyboardButton(text="💰 Changer le CASHH temporairement", callback_data=f"calc_changecash_{eid}")],
            [InlineKeyboardButton(text="🔄 Changer les cotes", callback_data=f"calc_changeodds_{eid}")],
            [InlineKeyboardButton(text="◀️ Retour à l'alerte", callback_data=f"back_to_main_{eid}")],
        ]
    else:
        msg = (
            f"{title_en}\n\n"
            f"{desc_en}"
            f"<b>Current match:</b>\n"
            f"{match}\n"
            f"{market}\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n\n"
            f"<b>What do you want to do?</b>"
        )
        recalc_text = "✅ Recalculate with my CASHH" if bet_type != 'middle' else "✅ Recalculate middle with my CASHH"
        kb = [
            [InlineKeyboardButton(text=recalc_text, callback_data=f"calc_{eid}|safe")],
            [InlineKeyboardButton(text="💰 Change CASHH temporarily", callback_data=f"calc_changecash_{eid}")],
            [InlineKeyboardButton(text="🔄 Change odds", callback_data=f"calc_changeodds_{eid}")],
            [InlineKeyboardButton(text="◀️ Back to alert", callback_data=f"back_to_main_{eid}")],
        ]
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.message(CalculatorStates.awaiting_risked_percent)
async def handle_risked_percent_input(message: types.Message, state: FSMContext):
    """Capture typed risk % and ask which side to favor."""
    txt = (message.text or "").replace(",", ".").strip()
    import re as _re
    m = _re.search(r"(\d+(?:\.\d+)?)", txt)
    if not m:
        await message.answer("❌ Invalid %. Enter a number like 3, 5 or 10.")
        return
    try:
        risk_pct = float(m.group(1))
    except Exception:
        await message.answer("❌ Invalid %. Enter a number like 3, 5 or 10.")
        return
    # Clamp reasonable bounds
    if risk_pct < 0.5:
        risk_pct = 0.5
    if risk_pct > 99:
        risk_pct = 99.0
    data = await state.get_data()
    eid = data.get("eid")
    drop = _get_drop(eid)
    if not drop:
        await message.answer("❌ Drop expired")
        await state.clear()
        return
    _, lang, _ = _get_user_prefs(message.from_user.id)
    outs = drop.get("outcomes", [])[:2]
    if len(outs) < 2:
        await message.answer("❌ Not enough outcomes")
        await state.clear()
        return
    o1, o2 = outs
    if lang == "fr":
        msg = f"⚠️ <b>RISKED {risk_pct:.1f}%</b>\n\n<b>Sur quel côté miser PLUS?</b>"
    else:
        msg = f"⚠️ <b>RISKED {risk_pct:.1f}%</b>\n\n<b>Which side to stake MORE?</b>"
    kb = [
        [InlineKeyboardButton(text=f"{get_casino_logo(o1.get('casino',''))} {o1.get('casino','')} - {o1.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|0")],
        [InlineKeyboardButton(text=f"{get_casino_logo(o2.get('casino',''))} {o2.get('casino','')} - {o2.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|1")],
    ]
    await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.clear()


async def show_calc_safe(callback: types.CallbackQuery, eid: str, drop: dict, bankroll: float, lang: str):
    """Show SAFE mode calculation - ultra-clear format"""
    bet_type = drop.get('bet_type', 'arbitrage')
    outcomes = drop.get('outcomes', [])
    
    # For Good EV: use rich formatter
    if bet_type == 'good_ev':
        from utils.oddsjam_formatters import format_good_odds_message
        try:
            text = format_good_odds_message(drop, bankroll, lang)
        except Exception as e:
            logger.error(f"Error formatting Good EV in calculator: {e}")
            await callback.answer("❌ Erreur" if lang=='fr' else "❌ Error", show_alert=True)
            return
        
        token = _token_for_eid(eid)
        if lang == 'fr':
            kb = [
                [InlineKeyboardButton(text="💰 Tester différents montants", callback_data=f"chg_cashhT_{token}")],
                [InlineKeyboardButton(text="◀️ Retour au menu", callback_data=f"cmenu_{token}")],
            ]
        else:
            kb = [
                [InlineKeyboardButton(text="💰 Test different amounts", callback_data=f"chg_cashhT_{token}")],
                [InlineKeyboardButton(text="◀️ Back to menu", callback_data=f"cmenu_{token}")],
            ]
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    # For Middle: use rich formatter
    if bet_type == 'middle':
        from utils.oddsjam_formatters import format_middle_message
        try:
            text = format_middle_message(drop, {}, bankroll, lang, rounding=0)
        except Exception as e:
            logger.error(f"Error formatting Middle in calculator: {e}")
            await callback.answer("❌ Erreur" if lang=='fr' else "❌ Error", show_alert=True)
            return
        
        token = _token_for_eid(eid)
        if lang == 'fr':
            kb = [
                [InlineKeyboardButton(text="💰 Tester différents montants", callback_data=f"chg_cashhT_{token}")],
                [InlineKeyboardButton(text="🔄 Changer les cotes", callback_data=f"chgo_{token}")],
                [InlineKeyboardButton(text="◀️ Retour au menu", callback_data=f"cmenu_{token}")],
            ]
        else:
            kb = [
                [InlineKeyboardButton(text="💰 Test different amounts", callback_data=f"chg_cashhT_{token}")],
                [InlineKeyboardButton(text="🔄 Change odds", callback_data=f"chgo_{token}")],
                [InlineKeyboardButton(text="◀️ Back to menu", callback_data=f"cmenu_{token}")],
            ]
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    # For Arbitrage: existing logic
    if len(outcomes) < 2:
        return
    
    o1, o2 = outcomes[:2]
    odds_list = [int(o1.get('odds', 0)), int(o2.get('odds', 0))]
    
    # Generate token for compact callbacks
    token = _token_for_eid(eid)
    
    # Calculate SAFE
    res = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
    stakes = res.get('stakes', [0, 0])
    returns = res.get('returns', [0, 0])
    profit = res.get('profit', 0)
    roi_pct = (profit / bankroll * 100) if bankroll > 0 else 0
    
    # Arrondis suggérés
    stake1_down = int(stakes[0])
    stake1_up = stake1_down + 1
    stake2_down = int(stakes[1])
    stake2_up = stake2_down + 1
    
    odds1_str = f"+{odds_list[0]}" if odds_list[0] > 0 else str(odds_list[0])
    odds2_str = f"+{odds_list[1]}" if odds_list[1] > 0 else str(odds_list[1])
    
    if lang == 'fr':
        # Use consistent format like main arbitrage message
        from utils.sport_emoji import get_sport_emoji
        sport_emoji = get_sport_emoji(drop.get('league',''), drop.get('sport',''))
        msg = (
            f"🚨 <b>ALERTE ARBITRAGE - {drop.get('arb_percentage', 0)}%</b> 🚨\n\n"
            f"🏟️ <b>{drop.get('match', '')}</b>\n"
            f"{sport_emoji} {drop.get('league', '')} - {drop.get('market', '')}\n"
        )
        
        # Add time if available
        time_str = drop.get('formatted_time', '') or drop.get('commence_time', '') or drop.get('time', '')
        if time_str and time_str != 'TBD':
            msg += f"🕐 {time_str}\n"
        
        msg += (
            f"\n"
            f"💰 <b>CASHH: ${bankroll:.2f}</b>\n"
            f"✅ <b>Profit Garanti: ${profit:.2f}</b> (ROI: {roi_pct:.2f}%)\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"💵 Miser: <code>${stakes[0]:.2f}</code> ({odds1_str}) → Retour: ${returns[0]:.2f}\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"💵 Miser: <code>${stakes[1]:.2f}</code> ({odds2_str}) → Retour: ${returns[1]:.2f}\n\n"
            f"⚠️ <b>Attention: les cotes peuvent changer - toujours vérifier avant de bet!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Détails du calcul:</b>\n"
            f"• Total misé: ${bankroll:.2f}\n"
            f"• Retour garanti: ${returns[0]:.2f}\n"
            f"• ROI: {roi_pct:.2f}%\n\n"
            f"💡 <b>Arrondis suggérés:</b>\n"
            f"{get_casino_logo(o1.get('casino',''))} {o1.get('casino','')}: ${stake1_down} ou ${stake1_up}\n"
            f"{get_casino_logo(o2.get('casino',''))} {o2.get('casino','')}: ${stake2_down} ou ${stake2_up}"
        )
        kb = [
            [InlineKeyboardButton(text="⚠️ Mode RISKED (avancé)", callback_data=f"crs_{token}")],
            [InlineKeyboardButton(text="💰 Changer CASHH", callback_data=f"chg_cashhT_{token}")],
            [InlineKeyboardButton(text="🔄 Changer cotes", callback_data=f"chgo_{token}")],
            [InlineKeyboardButton(text="◀️ Retour à l'alerte", callback_data=f"back_to_main_{eid}")],
        ]
    else:
        msg = (
            f"✅ <b>ARBITRAGE CALCULATION - SAFE MODE</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"✅ Guaranteed profit: <b>${profit:.2f}</b> ({roi_pct:.2f}%)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Odds: {odds1_str}\n"
            f"💵 Stake: <b>${stakes[0]:.2f}</b>\n"
            f"📈 If wins → Return: <b>${returns[0]:.2f}</b>\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Odds: {odds2_str}\n"
            f"💵 Stake: <b>${stakes[1]:.2f}</b>\n"
            f"📈 If wins → Return: <b>${returns[1]:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Summary:</b>\n"
            f"• Total staked: ${bankroll:.2f}\n"
            f"• Guaranteed return: ${returns[0]:.2f}\n"
            f"• Profit: ${profit:.2f}\n"
            f"• ROI: {roi_pct:.2f}%\n\n"
            f"⚠️ <b>Round your stakes:</b>\n"
            f"{get_casino_logo(o1.get('casino',''))} {o1.get('casino','')}: ${stake1_down} or ${stake1_up}\n"
            f"{get_casino_logo(o2.get('casino',''))} {o2.get('casino','')}: ${stake2_down} or ${stake2_up}"
        )
        kb = [
            [InlineKeyboardButton(text="⚠️ RISKED mode (advanced)", callback_data=f"crs_{token}")],
            [InlineKeyboardButton(text="💰 Change CASHH", callback_data=f"chg_cashhT_{token}")],
            [InlineKeyboardButton(text="🔄 Change odds", callback_data=f"chgo_{token}")],
            [InlineKeyboardButton(text="◀️ Back", callback_data=f"cmenu_{token}")],
        ]
    
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


async def start_calc_risked(callback: types.CallbackQuery, eid: str, drop: dict, lang: str):
    """Start RISKED mode flow with explanation"""
    user_id = callback.from_user.id
    
    # Show explanation + buttons; we'll read % via button callbacks
    
    if lang == 'fr':
        msg = (
            f"⚠️ <b>MODE RISKED - AVANCÉ</b>\n\n"
            f"Dans ce mode, tu acceptes une PETITE PERTE possible pour un GROS gain potentiel.\n\n"
            f"🎯 <b>Comment ça marche?</b>\n\n"
            f"Au lieu de balancer 50/50, tu mises:\n"
            f"• Plus sur un côté (celui que tu penses va gagner)\n"
            f"• Moins sur l'autre (protection partielle)\n\n"
            f"<b>Résultat:</b>\n"
            f"✅ Si ton côté favori gagne → GROS profit\n"
            f"❌ Si l'autre gagne → Petite perte acceptée\n\n"
            f"<b>QUEL % ES-TU PRÊT À RISQUER?</b>\n\n"
            f"Exemples:\n"
            f"• 3% = Risque ~-$15, Gain potentiel ~+$80\n"
            f"• 5% = Risque ~-$25, Gain potentiel ~+$120\n"
            f"• 10% = Risque ~-$50, Gain potentiel ~+$200\n"
            f"• 50% = Risque ~-$275, Gain potentiel ~+$500\n\n"
            f"⚠️ <i>Note: RISKED change la variance, pas l'EV.\n"
            f"Tu transformes profit garanti → gros swing.</i>\n\n"
            f"<b>Entre un % (ex: 5, max 99%):</b>"
        )
    else:
        msg = (
            f"⚠️ <b>RISKED MODE - ADVANCED</b>\n\n"
            f"In this mode, you accept a SMALL LOSS possibility for a BIG potential gain.\n\n"
            f"🎯 <b>How it works:</b>\n\n"
            f"Instead of balancing 50/50, you stake:\n"
            f"• More on one side (the one you think will win)\n"
            f"• Less on the other (partial protection)\n\n"
            f"<b>Result:</b>\n"
            f"✅ If your favored side wins → BIG profit\n"
            f"❌ If the other wins → Small accepted loss\n\n"
            f"<b>WHAT % ARE YOU WILLING TO RISK?</b>\n\n"
            f"Examples:\n"
            f"• 3% = Risk ~-$15, Potential gain ~+$80\n"
            f"• 5% = Risk ~-$25, Potential gain ~+$120\n"
            f"• 10% = Risk ~-$50, Potential gain ~+$200\n"
            f"• 50% = Risk ~-$275, Potential gain ~+$500\n\n"
            f"⚠️ <i>Note: RISKED changes variance, not EV.\n"
            f"You trade guaranteed profit → big swing.</i>\n\n"
            f"<b>Enter a % (eg: 5, max 99%):</b>"
        )
    
    # Can't set state from here without proper FSMContext, will handle in separate handler
    # For now, just show message with back button
    kb = [[InlineKeyboardButton(text="◀️ Retour" if lang=='fr' else "◀️ Back", callback_data=f"calc_{eid}|menu")]]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("alert_"))
async def cb_alert_back(callback: types.CallbackQuery):
    """Render full alert view with current parameters (mode/risk/favor/aggr)."""
    await safe_callback_answer(callback)
    data = callback.data or ""
    eid, extras = _extract_event_id(data, "alert_")
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    bankroll, lang, default_risk = _get_user_prefs(callback.from_user.id)
    # Defaults
    mode = 'safe'
    favor = 0
    risk_pct = default_risk
    aggr_p = 70.0
    for e in extras:
        if e in ("safe", "balanced"):
            mode = e
        elif e.startswith('risked'):
            mode = 'risked'
        elif e.startswith('aggr'):
            mode = 'aggr'
        elif e.startswith('f') and e[1:].isdigit():
            favor = int(e[1:])
        elif e.startswith('r'):
            try:
                risk_pct = float(e[1:])
            except:
                pass
        elif e.startswith('p'):
            try:
                aggr_p = float(e[1:])
            except:
                pass
        elif e.startswith('b'):
            try:
                bankroll = float(e[1:])
            except:
                pass

    odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
    calc = ArbitrageCalculator()
    stakes = None
    returns = None
    
    from utils.sport_emoji import get_sport_emoji
    sport_emoji = get_sport_emoji(drop.get('league',''), drop.get('sport',''))
    
    header = f"🚨 <b>ARBITRAGE ALERT - {drop.get('arb_percentage',0)}%</b> 🚨\n\n"
    body_top = (
        f"🏟️ <b>{drop.get('match','')}</b>\n"
        f"{sport_emoji} {drop.get('league','')} - {drop.get('market','')}\n\n"
        f"💰 <b>CASHH: {_format_currency(bankroll)}</b>\n"
    )
    # Compute stakes per selected mode
    if mode == 'risked' and len(odds_list) == 2:
        res = ArbitrageCalculator.calculate_risked_stakes(bankroll, odds_list, risk_percentage=risk_pct, favor_outcome=favor)
        stakes = res.get('stakes')
        returns = res.get('returns')
    elif mode == 'balanced' and len(odds_list) == 2:
        res = ArbitrageCalculator.calculate_balanced(bankroll, odds_list)
        stakes = res.get('stakes')
        returns = [stakes[i]*ArbitrageCalculator.american_to_decimal(odds_list[i]) for i in range(2)]
    elif mode == 'aggr' and len(odds_list) == 2:
        res = ArbitrageCalculator.calculate_aggressive(bankroll, odds_list, favor_percentage=aggr_p, favor_outcome=favor)
        stakes = res.get('stakes')
        returns = [stakes[i]*ArbitrageCalculator.american_to_decimal(odds_list[i]) for i in range(2)]
    else:
        res = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
        stakes = res.get('stakes')
        returns = res.get('returns')

    # Build outcomes lines with stakes
    lines = []
    for i, out in enumerate(drop.get('outcomes', [])[:2]):
        odds = out.get('odds')
        casino = out.get('casino')
        stake_i = stakes[i] if stakes else 0
        ret_i = returns[i] if returns else 0
        odds_str = f"+{odds}" if isinstance(odds, int) and odds > 0 else str(odds)
        lines.append(
            f"{get_casino_logo(casino)} <b>[{casino}]</b> {out['outcome']}\n"
            f"💵 Miser: <code>{_format_currency(stake_i)}</code> ({odds_str}) → Retour: {_format_currency(ret_i)}\n"
        )
    text = header + body_top + ("".join(lines))

    # Keyboard features should reflect the user's tier
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        def _core_tier_from_model(t):
            try:
                name = t.name.lower()
            except Exception:
                return TierLevel.FREE
            return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE
        user_tier = _core_tier_from_model(u.tier) if u else TierLevel.FREE
        try:
            if user_tier != TierLevel.FREE and u and not u.subscription_active:
                user_tier = TierLevel.FREE
        except Exception:
            pass
    finally:
        db.close()
    features = TierManager.get_features(user_tier)
    kb = []
    # Casino buttons row with deep links (PREMIUM)
    casino_buttons = []
    
    # Try to get deep links from The Odds API
    sport_key = drop.get('sport_key')
    event_id_api = drop.get('event_id_api')
    
    # Get links (will use API if available, otherwise fallback)
    links = get_links_for_drop(
        drop,
        sport_key=sport_key,
        event_id=event_id_api
    )
    
    for out in drop.get('outcomes', [])[:2]:
        c = out.get('casino')
        
        # Priority: 1) Deep link from API, 2) Referral link, 3) Fallback
        link = links.get(c)
        if not link:
            link = get_casino_referral_link(c)
        if not link:
            link = get_fallback_url(c)
        
        if link:
            casino_buttons.append(InlineKeyboardButton(text=f"{get_casino_logo(c)} {c}", url=link))
    
    if casino_buttons:
        kb.append(casino_buttons)
    else:
        kb.append([InlineKeyboardButton(text=("🎰 Casinos" if lang!='fr' else "🎰 Casinos"), callback_data="show_casinos")])

    # Interactive tools row → replace RISKED with I BET (bet tracking)
    try:
        res_safe = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
        expected_profit = float(res_safe.get('profit', 0) or 0)
    except Exception:
        expected_profit = 0.0
    total_stake = bankroll
    # Resolve drop_event_id
    de_id = drop.get('drop_event_id')
    if not de_id:
        try:
            _db2 = SessionLocal()
            ev = _db2.query(DropEvent).filter(DropEvent.event_id == eid).first()
            de_id = ev.id if ev else 0
        except Exception:
            de_id = 0
        finally:
            try:
                _db2.close()
            except Exception:
                pass
    i_bet_text = (f"💰 JE PARIE (${expected_profit:.2f} profit)" if lang=='fr' else f"💰 I BET (${expected_profit:.2f} profit)")
    # Preserve current extras in Change CASHH flow
    extras_str = f"{mode}|f{favor}|r{risk_pct}|p{aggr_p}"
    kb.append([
        InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{de_id}_{total_stake}_{expected_profit}"),
        InlineKeyboardButton(text=("🔁 Calculatrice" if lang=='fr' else "🔁 Calculator"), callback_data=f"calc_{eid}|menu"),
        InlineKeyboardButton(text=("💰 Changer CASHH" if lang=='fr' else "💰 Change CASHH"), callback_data=f"chg_cashh_{eid}|{extras_str}"),
    ])

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("change_bankroll_"))
async def cb_change_bankroll_legacy(callback: types.CallbackQuery):
    """Handle legacy change_bankroll_ callbacks - redirect to new system."""
    await safe_callback_answer(callback)
    data = callback.data or ""
    
    # Extract drop_event_id from change_bankroll_{id}
    try:
        drop_event_id = data.split('_', 2)[2]
        logger.info(f"🔄 Legacy bankroll change for drop_event_id: {drop_event_id}")

        # Resolve Odds API event_id from DropEvent DB row
        event_id: str | None = None
        try:
            db = SessionLocal()
            ev = db.query(DropEvent).filter(DropEvent.id == int(drop_event_id)).first()
            if ev:
                event_id = ev.event_id
        except Exception as db_err:
            logger.error(f"❌ Failed to resolve event_id for drop_event_id={drop_event_id}: {db_err}")
        finally:
            try:
                db.close()
            except Exception:
                pass

        if not event_id:
            # Nothing to show – underlying drop is gone
            try:
                await callback.answer("❌ Drop expiré", show_alert=True)
            except Exception:
                pass
            return

        # Call the new handler logic with the resolved event_id
        await show_cashh_menu(callback, event_id)
        
    except Exception as e:
        logger.error(f"❌ Failed to handle legacy change_bankroll callback: {e}")
        try:
            await callback.answer("❌ Erreur lors du changement de budget", show_alert=True)
        except:
            pass

async def show_cashh_menu(callback: types.CallbackQuery, eid: str, extras: list = None):
    """Show the CASHH change menu for a given event ID."""
    if extras is None:
        extras = []
    
    logger.info(f"🔧 show_cashh_menu called for eid: {eid}")
    logger.info(f"  Checking if eid exists in DROPS: {eid in DROPS}")
    logger.info(f"  DROPS keys sample: {list(DROPS.keys())[:3]}...")  # Show first 3 keys
    
    # Defaults
    mode = 'safe'
    favor = 0
    risk_pct = _get_user_prefs(callback.from_user.id)[2]
    aggr_p = 70.0
    for e in extras:
        if e in ("safe", "balanced"):
            mode = e
        elif e.startswith('risked'):
            mode = 'risked'
        elif e.startswith('aggr'):
            mode = 'aggr'
        elif e.startswith('f') and e[1:].isdigit():
            favor = int(e[1:])
        elif e.startswith('r'):
            try:
                risk_pct = float(e[1:])
            except:
                pass
        elif e.startswith('p'):
            try:
                aggr_p = float(e[1:])
            except:
                pass
    
    # Build quick options with tokenized callback_data (avoid 64-char limit)
    token = _token_for_eid(eid)
    logger.info(f"🔧 Generated token: {token} for eid: {eid}")
    logger.info(f"  CALC_TOKENS[{token}] = {eid}")
    
    amounts = [100, 200, 300, 500, 1000]
    rows = []
    for a in amounts:
        rows.append([InlineKeyboardButton(text=f"${a}", callback_data=f"acb_{token}_{a}")])
    # Back button (no change)
    lang = _get_user_prefs(callback.from_user.id)[1]
    # Custom amount & Back buttons use the same token
    rows.append([InlineKeyboardButton(text=("✏️ Montant personnalisé" if lang=='fr' else "✏️ Custom amount"), callback_data=f"cashh_custT_{token}")])
    rows.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data=f"abk_{token}")])
    prompt = ("💰 <b>Changer CASHH (par appel)</b>\nChoisis un montant rapide:" if lang=='fr' else "💰 <b>Change CASHH (per-call)</b>\nChoose a quick amount:")
    
    try:
        await callback.message.edit_text(prompt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        logger.info(f"✅ Successfully showed CASHH menu for eid: {eid}")
    except Exception as e:
        logger.error(f"❌ Failed to edit message with CASHH menu: {e}")
        try:
            await callback.answer("❌ Erreur lors de l'affichage du menu", show_alert=True)
        except:
            pass

@calc_router.callback_query(F.data.startswith("chg_cashh_"))
async def cb_change_cashh(callback: types.CallbackQuery):
    """Show quick amounts to change bankroll for this alert without changing global settings."""
    await safe_callback_answer(callback)
    data = callback.data or ""
    logger.info(f"🔧 cb_change_cashh called with data: {data}")
    
    # Parse event id and optional extras
    # Format: chg_cashh_{eid} or chg_cashh_{eid}|{extras}
    try:
        # Remove the prefix to get the event ID and extras
        after_prefix = data.replace('chg_cashh_', '')
        logger.info(f"🔧 After removing prefix: {after_prefix}")
    except Exception as e:
        logger.error(f"❌ Failed to parse chg_cashh data: {e}")
        return
    
    if '|' in after_prefix:
        eid, extras_part = after_prefix.split('|', 1)
        extras = extras_part.split('|') if extras_part else []
    else:
        eid, extras = after_prefix, []
    
    # Use the shared function
    await show_cashh_menu(callback, eid, extras)

@calc_router.callback_query(F.data.startswith("cashh_cust"))
async def cb_change_cashh_custom(callback: types.CallbackQuery, state: FSMContext):
    """Prompt user for a custom per-call CASHH amount."""
    await safe_callback_answer(callback)
    data = callback.data or ""
    # Support both legacy cashh_cust_{eid} and new cashh_custT_{token}
    eid = None
    token = None
    if data.startswith("cashh_custT_"):
        try:
            token = data.split('_', 2)[2]
        except Exception:
            token = None
        eid = CALC_TOKENS.get(token)
    else:
        try:
            eid = data.split('_', 2)[2]
        except Exception:
            eid = None
    if not eid:
        await safe_callback_answer(callback, "❌ Error", show_alert=True)
        return
    await state.set_state(CashhChangeStates.awaiting_amount)
    await state.update_data(eid=eid, token=token, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    lang = _get_user_prefs(callback.from_user.id)[1]
    prompt = ("💰 Entre un montant personnalisé ($):\nEx: 350" if lang=='fr' else "💰 Enter a custom amount ($):\nEx: 350")
    await callback.message.edit_text(prompt)

@dp.message(CashhChangeStates.awaiting_amount)
async def handle_custom_cashh_amount(message: types.Message, state: FSMContext):
    """Handle user-entered custom CASHH and re-render the alert view in-place."""
    text = (message.text or "").strip().replace('$','').replace(',','')
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Montant invalide. Ex: 350" if (_get_user_prefs(message.from_user.id)[1]=='fr') else "❌ Invalid amount. Eg: 350")
        return
    data = await state.get_data()
    eid = data.get('eid')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    
    # Fetch drop
    drop = _get_drop(eid)
    if not drop:
        await message.answer("❌ Drop expiré" if (_get_user_prefs(message.from_user.id)[1]=='fr') else "❌ Drop expired")
        await state.clear()
        return
    
    # Recompute stakes with custom amount and re-render the alert view
    lang = _get_user_prefs(message.from_user.id)[1]
    
    # Detect bet_type and use appropriate formatter
    bet_type = drop.get('bet_type', 'arbitrage')
    
    if bet_type == 'good_ev':
        # Good Odds: use Good Odds formatter
        from utils.oddsjam_formatters import format_good_odds_message
        text_render = format_good_odds_message(drop, amount, lang)
        # For Good Odds, profit is EV-based
        ev_percent = drop.get('ev_percent', 0)
        expected_profit = amount * (ev_percent / 100)
        stakes = [amount]  # Single stake
    elif bet_type == 'middle':
        # Middle: use Middle formatter
        from utils.oddsjam_formatters import format_middle_message
        from utils.middle_calculator import calculate_middle_stakes
        # Calculate middle stakes
        odds_a_raw = drop.get('outcomes', [{}])[0].get('odds', 0)
        odds_b_raw = drop.get('outcomes', [{}])[1].get('odds', 0) if len(drop.get('outcomes', [])) > 1 else 0
        # Convert string odds to int (e.g., "+150" -> 150, "-110" -> -110)
        try:
            odds_a = int(str(odds_a_raw).replace('+', '').replace('−', '-'))
            odds_b = int(str(odds_b_raw).replace('+', '').replace('−', '-'))
        except (ValueError, TypeError):
            odds_a = 0
            odds_b = 0
        user_rounding, user_mode = _get_user_rounding(message.from_user.id)
        middle_calc = calculate_middle_stakes(odds_a, odds_b, amount, user_rounding, user_mode)
        text_render = format_middle_message(drop, middle_calc, amount, lang)
        expected_profit = middle_calc.get('profit_a_only', 0)  # Min guaranteed profit
        stakes = [middle_calc.get('stake_a', 0), middle_calc.get('stake_b', 0)]
    else:
        # Arbitrage: use arbitrage formatter (default)
        user_rounding, user_mode = _get_user_rounding(message.from_user.id)
        text_render, stakes = _format_arbitrage_message(drop, amount, lang, user_rounding, user_mode)
        
        # Calculate expected profit for I BET button
        odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
        calc = ArbitrageCalculator.calculate_safe_stakes(amount, odds_list)
        returns = calc.get('returns', [0, 0])
        expected_profit = float(calc.get('profit', 0) or 0)
    
    # Keyboard rows - mirror original enriched alert layout
    kb = []
    casino_buttons = []
    links = get_links_for_drop(drop, sport_key=drop.get('sport_key'), event_id=drop.get('event_id_api'))
    for out in drop.get('outcomes', [])[:2]:
        c = out.get('casino')
        link = links.get(c) or get_casino_referral_link(c) or get_fallback_url(c)
        if link:
            casino_buttons.append(InlineKeyboardButton(text=f"{get_casino_logo(c)} {c}", url=link))
    if casino_buttons:
        kb.append(casino_buttons)

    # Resolve persistent drop_event_id (DB id) used for I BET tracking
    de_id = drop.get('drop_event_id') or 0
    i_bet_text = (f"💰 JE PARIE (${expected_profit:.2f} profit)" if lang=='fr' else f"💰 I BET (${expected_profit:.2f} profit)")

    # Row 2: JE PARIE only
    kb.append([
        InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{de_id}_{amount}_{expected_profit}")
    ])

    # Row 3: Custom Calculator
    calc_text = "🧮 Calculateur Custom" if lang=='fr' else "🧮 Custom Calculator"
    kb.append([
        InlineKeyboardButton(text=calc_text, callback_data=f"calc_{de_id}|menu")
    ])

    # Row 4: Change CASHH (per-call)
    cashh_text = "💰 Changer CASHH" if lang=='fr' else "💰 Change CASHH"
    kb.append([
        InlineKeyboardButton(text=cashh_text, callback_data=f"change_bankroll_{de_id}")
    ])

    # Row 5: Verify Odds - DISABLED (not working properly)
    # call_id = CALL_IDS_BY_DROP_ID.get(str(de_id))
    # if call_id:
    #     verify_text = "✅ Vérifier les cotes" if lang=='fr' else "✅ Verify Odds"
    #     kb.append([
    #         InlineKeyboardButton(text=verify_text, callback_data=f"verify_odds:{call_id}")
    #     ])
    
    # Edit the original message
    try:
        await message.bot.edit_message_text(
            text_render,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
    except Exception:
        await message.answer(text_render, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    # 🔥 IMPORTANT: Update PENDING_CALLS with new bankroll for custom amounts too
    drop_event_id = str(drop.get('drop_event_id', ''))
    if drop_event_id and drop_event_id in PENDING_CALLS:
        betting_call = PENDING_CALLS[drop_event_id]
        # Update bankroll and recalculate stakes
        betting_call.bankroll = amount
        
        # Recalculate stakes for both sides
        if len(betting_call.sides) == 2:
            for i, side in enumerate(betting_call.sides):
                side.stake = stakes[i]
                side.expected_return = returns[i]
        
        # Recalculate arbitrage analysis
        betting_call = analyze_arbitrage_two_way(betting_call)
        
        # Save back to PENDING_CALLS
        PENDING_CALLS[drop_event_id] = betting_call
        
        # Save to pickle
        try:
            save_pending_calls()
            logger.info(f"Updated bankroll to ${amount} for call {drop_event_id} (custom amount)")
        except Exception as e:
            logger.error(f"Failed to save pending calls after custom bankroll change: {e}")
    
    await state.clear()
    return


@calc_router.callback_query(F.data.startswith("acb_"))
async def quick_amount_callback(callback: types.CallbackQuery):
    """Handle quick amount buttons using tokenized callback data."""
    await safe_callback_answer(callback)
    
    logger.info(f"🔵 quick_amount_callback: data={callback.data}")
    
    try:
        _, token, amt = callback.data.split('_')
        amount = float(amt)
        logger.info(f"  Token: {token}, Amount: {amount}")
    except Exception as e:
        logger.error(f"  Failed to parse callback data: {e}")
        return
    
    eid = CALC_TOKENS.get(token)
    logger.info(f"  Token {token} -> eid: {eid}")
    logger.info(f"  CALC_TOKENS contains: {list(CALC_TOKENS.keys())[:5]}...")  # Show first 5 tokens
    
    if not eid:
        logger.warning(f"  Token {token} not found in CALC_TOKENS!")
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    
    # Try to get drop first, then fallback to PENDING_CALLS
    drop = _get_drop(eid)
    betting_call = PENDING_CALLS.get(str(eid))
    
    if not drop and not betting_call:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    # Build message from drop OR betting_call
    lang = _get_user_prefs(callback.from_user.id)[1]
    
    if drop:
        # Detect bet_type from drop
        bet_type = drop.get('bet_type', 'arbitrage')
        
        # Use appropriate formatter based on bet_type
        if bet_type == 'good_ev':
            # Good Odds: use Good Odds formatter
            from utils.oddsjam_formatters import format_good_odds_message
            text = format_good_odds_message(drop, amount, lang)
            # For Good Odds, profit is EV-based
            ev_percent = drop.get('ev_percent', 0)
            profit = amount * (ev_percent / 100)
            stakes = [amount]  # Single stake
        elif bet_type == 'middle':
            # Middle: use Middle formatter
            from utils.oddsjam_formatters import format_middle_message
            from utils.middle_calculator import calculate_middle_stakes
            # Calculate middle stakes
            odds_a_raw = drop.get('outcomes', [{}])[0].get('odds', 0)
            odds_b_raw = drop.get('outcomes', [{}])[1].get('odds', 0) if len(drop.get('outcomes', [])) > 1 else 0
            # Convert string odds to int (e.g., "+150" -> 150, "-110" -> -110)
            try:
                odds_a = int(str(odds_a_raw).replace('+', '').replace('−', '-'))
                odds_b = int(str(odds_b_raw).replace('+', '').replace('−', '-'))
            except (ValueError, TypeError):
                odds_a = 0
                odds_b = 0
            user_rounding, user_mode = _get_user_rounding(callback.from_user.id)
            middle_calc = calculate_middle_stakes(odds_a, odds_b, amount, user_rounding, user_mode)
            text = format_middle_message(drop, middle_calc, amount, lang)
            profit = middle_calc.get('profit_a_only', 0)  # Min guaranteed profit
            stakes = [middle_calc.get('stake_a', 0), middle_calc.get('stake_b', 0)]
        else:
            # Arbitrage: use arbitrage formatter (default)
            user_rounding, user_mode = _get_user_rounding(callback.from_user.id)
            text, stakes = _format_arbitrage_message(drop, amount, lang, user_rounding, user_mode)
            
            # Calculate profit for I BET button
            odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
            calc = ArbitrageCalculator.calculate_safe_stakes(amount, odds_list)
            returns = calc.get('returns', [0,0])
            profit = float(calc.get('profit', 0) or 0)
        
        # Build casino buttons (use referral/deep links where possible)
        casino_buttons = []
        links = get_links_for_drop(drop, sport_key=drop.get('sport_key'), event_id=drop.get('event_id_api'))
        for out in drop.get('outcomes', [])[:2]:
            c = out.get('casino')
            link = links.get(c) or get_casino_referral_link(c) or get_fallback_url(c)
            if link:
                casino_buttons.append(InlineKeyboardButton(text=f"{get_casino_logo(c)} {c}", url=link))
    else:
        # Use betting_call data (fallback for old alerts)
        betting_call.bankroll = amount
        
        # Convert betting_call to drop format for consistent display
        drop_from_call = {
            'arb_percentage': betting_call.arb_analysis.min_profit / amount * 100 if betting_call.arb_analysis and amount > 0 else 0,
            'match': betting_call.match,
            'league': betting_call.league,
            'market': betting_call.market,
            'time': betting_call.time,
            'formatted_time': betting_call.time,
            'outcomes': [
                {
                    'casino': side.book_name,
                    'outcome': side.outcome,
                    'odds': side.odds_american
                }
                for side in betting_call.sides[:2]
            ]
        }
        
        # Use the consistent formatter
        user_rounding, user_mode = _get_user_rounding(callback.from_user.id)
        text, stakes = _format_arbitrage_message(drop_from_call, amount, lang, user_rounding, user_mode)
        
        # Update betting_call stakes
        if len(betting_call.sides) == 2:
            for i, side in enumerate(betting_call.sides):
                side.stake = stakes[i]
                side.expected_return = stakes[i] * (100 + side.odds_american) / 100 if side.odds_american > 0 else stakes[i] * (100 - 100.0/abs(side.odds_american))
        
        # Recalculate arbitrage and profit
        betting_call = analyze_arbitrage_two_way(betting_call)
        profit = betting_call.arb_analysis.min_profit if betting_call.arb_analysis else 0
        
        # Build casino buttons from sides
        casino_buttons = []
        for side in betting_call.sides:
            link = side.deep_link or side.fallback_link
            if link:
                casino_buttons.append(InlineKeyboardButton(text=f"{get_casino_logo(side.book_name)} {side.book_name}", url=link))
    
    # Build keyboard mirroring original enriched alert layout
    kb = []
    if casino_buttons:
        kb.append(casino_buttons)
    
    # Get persistent id for callbacks (DB id for drop-based flows, fallback otherwise)
    de_id = drop.get('drop_event_id') if drop else eid
    if de_id is None:
        de_id = eid or 0
    
    i_bet_text = (f"💰 JE PARIE (${profit:.2f} profit)" if lang=='fr' else f"💰 I BET (${profit:.2f} profit)")

    # Row 2: JE PARIE only
    kb.append([
        InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{de_id}_{amount}_{profit}"),
    ])

    # Row 3: Custom Calculator
    calc_text = "🧮 Calculateur Custom" if lang=='fr' else "🧮 Custom Calculator"
    # Use de_id so calc/back_to_main can still resolve the DropEvent via _get_drop
    kb.append([
        InlineKeyboardButton(text=calc_text, callback_data=f"calc_{de_id}|menu"),
    ])

    # Row 4: Change CASHH
    cashh_text = "💰 Changer CASHH" if lang=='fr' else "💰 Change CASHH"
    kb.append([
        InlineKeyboardButton(text=cashh_text, callback_data=f"change_bankroll_{de_id}"),
    ])

    # Row 5: Verify Odds - DISABLED (not working properly)
    # call_id = CALL_IDS_BY_DROP_ID.get(str(de_id))
    # if call_id:
    #     verify_text = "✅ Vérifier les cotes" if lang=='fr' else "✅ Verify Odds"
    #     kb.append([
    #         InlineKeyboardButton(text=verify_text, callback_data=f"verify_odds:{call_id}"),
    #     ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    # 🔥 IMPORTANT: Update PENDING_CALLS with new bankroll
    drop_event_id = str(de_id)
    if drop_event_id and drop_event_id in PENDING_CALLS:
        # If we already updated betting_call above (no drop case), it's already saved
        if drop:
            # Need to update PENDING_CALLS from the drop data
            betting_call_to_update = PENDING_CALLS[drop_event_id]
            betting_call_to_update.bankroll = amount
            
            # Recalculate stakes for both sides
            if len(betting_call_to_update.sides) == 2:
                for i, side in enumerate(betting_call_to_update.sides):
                    side.stake = stakes[i]
                    side.expected_return = returns[i]
            
            # Recalculate arbitrage analysis
            betting_call_to_update = analyze_arbitrage_two_way(betting_call_to_update)
            
            # Save back to PENDING_CALLS
            PENDING_CALLS[drop_event_id] = betting_call_to_update
        else:
            # betting_call was already modified above, just save it
            PENDING_CALLS[drop_event_id] = betting_call
        
        # Save to pickle
        try:
            save_pending_calls()
            logger.info(f"Updated bankroll to ${amount} for call {drop_event_id}")
        except Exception as e:
            logger.error(f"Failed to save pending calls after bankroll change: {e}")


@calc_router.callback_query(F.data.startswith("abk_"))
async def back_to_alert_from_cashh(callback: types.CallbackQuery):
    # Return to alert view (SAFE) without mutating aiogram models
    await safe_callback_answer(callback)
    token = (callback.data or "").split('_', 1)[1] if '_' in (callback.data or "") else ""
    eid = CALC_TOKENS.get(token)
    if not eid:
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    drop = _get_drop(eid)
    if not drop:
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    # Recompute SAFE stakes
    odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
    res = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
    profit = float(res.get('profit', 0) or 0)
    stakes = res.get('stakes', [0, 0])
    returns = res.get('returns', [0, 0])
    # Build message
    from utils.sport_emoji import get_sport_emoji
    sport_emoji = get_sport_emoji(drop.get('league',''), drop.get('sport',''))
    header = f"🚨 <b>ARBITRAGE ALERT - {drop.get('arb_percentage',0)}%</b> 🚨\n\n"
    body_top = (
        f"🏟️ <b>{drop.get('match','')}</b>\n"
        f"{sport_emoji} {drop.get('league','')} - {drop.get('market','')}\n\n"
        f"💰 <b>CASHH: {_format_currency(bankroll)}</b>\n"
    )
    lines = []
    for i, out in enumerate(drop.get('outcomes', [])[:2]):
        odds = out.get('odds')
        casino = out.get('casino')
        odds_str = f"+{odds}" if isinstance(odds, int) and odds > 0 else str(odds)
        lines.append(
            f"{get_casino_logo(casino)} <b>[{casino}]</b> {out['outcome']}\n"
            f"💵 Miser: <code>{_format_currency(stakes[i])}</code> ({odds_str}) → Retour: {_format_currency(returns[i])}\n"
        )
    text = header + body_top + ("".join(lines))
    # Keyboard rows (same as alert view)
    kb = []
    casino_buttons = []
    # Deep links if available, else fallbacks
    links = get_links_for_drop(drop, sport_key=drop.get('sport_key'), event_id=drop.get('event_id_api'))
    for out in drop.get('outcomes', [])[:2]:
        c = out.get('casino')
        link = links.get(c) or get_casino_referral_link(c) or get_fallback_url(c)
        if link:
            casino_buttons.append(InlineKeyboardButton(text=f"{get_casino_logo(c)} {c}", url=link))
    if casino_buttons:
        kb.append(casino_buttons)
    expected_profit = profit
    # Use eid (from callback context) instead of drop_event_id (which may be 0)
    i_bet_text = (f"💰 JE PARIE (${expected_profit:.2f} profit)" if lang=='fr' else f"💰 I BET (${expected_profit:.2f} profit)")
    kb.append([
        InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{eid}_{bankroll}_{expected_profit}"),
        InlineKeyboardButton(text=("🔁 Calculatrice" if lang=='fr' else "🔁 Calculator"), callback_data=f"calc_{eid}|menu"),
        InlineKeyboardButton(text=("💰 Changer CASHH" if lang=='fr' else "💰 Change CASHH"), callback_data=f"chg_cashh_{eid}")
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    return

@calc_router.callback_query(F.data.startswith("crs_"))
async def token_risked_start(callback: types.CallbackQuery, state: FSMContext):
    try:
        await safe_callback_answer(callback)
    except Exception:
        pass
    token = (callback.data or "").split("_", 1)[1] if "_" in (callback.data or "") else ""
    eid = CALC_TOKENS.get(token)
    if not eid:
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    drop = _get_drop(eid)
    if not drop:
        await safe_callback_answer(callback, "❌ Drop expiré", show_alert=True)
        return
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    # Allow typed % input by setting FSM state
    try:
        await state.set_state(CalculatorStates.awaiting_risked_percent)
        await state.update_data(eid=eid)
    except Exception:
        pass
    await start_calc_risked(callback, eid, drop, lang)

@calc_router.callback_query(F.data.startswith("chgo_"))
async def token_change_odds(callback: types.CallbackQuery, state: FSMContext):
    try:
        await safe_callback_answer(callback)
    except Exception:
        pass
    token = (callback.data or "").split("_", 1)[1] if "_" in (callback.data or "") else ""
    eid = CALC_TOKENS.get(token)
    if not eid:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    outs = drop.get('outcomes', [])[:2]
    o1 = outs[0] if len(outs) > 0 else {}
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    await state.set_state(CalculatorStates.awaiting_odds_side1)
    await state.update_data(eid=eid, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    
    # Convert odds to int for display (odds might be stored as string)
    try:
        odds1 = int(o1.get('odds', 0))
    except (ValueError, TypeError):
        odds1 = 0
    odds1_str = f"+{odds1}" if odds1 > 0 else str(odds1)
    
    if lang == 'fr':
        msg = (
            f"🔄 <b>CHANGER LES COTES</b>\n\n"
            f"🚨 <b>IMPORTANT:</b> Vérifie SUR LE SITE:\n"
            f"1️⃣ La LIGNE (Over/Under X.5)\n"
            f"2️⃣ Les COTES (+105, -110, etc.)\n\n"
            f"⚠️ Si la LIGNE a changé = Plus d'arbitrage!\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Cote actuelle: {odds1_str}\n"
            f"<b>Nouvelle cote?</b> (ex: +105, -110)"
        )
    else:
        msg = (
            f"🔄 <b>CHANGE ODDS</b>\n\n"
            f"🚨 <b>IMPORTANT:</b> Check ON THE SITE:\n"
            f"1️⃣ The LINE (Over/Under X.5)\n"
            f"2️⃣ The ODDS (+105, -110, etc.)\n\n"
            f"⚠️ If the LINE changed = No more arbitrage!\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Current odds: {odds1_str}\n"
            f"<b>New odds?</b> (eg: +105, -110)"
        )
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML)

@calc_router.callback_query(F.data.startswith("cmenu_"))
async def token_calc_menu(callback: types.CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    token = (callback.data or "").split("_", 1)[1] if "_" in (callback.data or "") else ""
    eid = CALC_TOKENS.get(token)
    if not eid:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    bet_type = drop.get('bet_type', 'arbitrage')
    outcomes = drop.get('outcomes', [])
    match = drop.get('match', '')
    market = drop.get('market', '')
    token2 = _token_for_eid(eid)
    
    # For Good EV (1 outcome)
    if bet_type == 'good_ev':
        if not outcomes:
            await callback.answer("❌ Données incomplètes", show_alert=True)
            return
        o1 = outcomes[0]
        if lang == 'fr':
            msg = (
                f"🧮 <b>CALCULATEUR GOOD ODDS</b>\n\n"
                f"<b>Match actuel:</b>\n{match}\n{market}\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n\n"
                f"<b>Que veux-tu faire?</b>"
            )
            kb = [
                [InlineKeyboardButton(text="✅ Recalculer EV avec mon CASHH", callback_data=f"calc_{eid}|safe")],
                [InlineKeyboardButton(text="💰 Tester différents montants", callback_data=f"chg_cashhT_{token2}")],
                [InlineKeyboardButton(text="◀️ Retour à l'alerte", callback_data=f"back_to_main_{eid}")],
            ]
        else:
            msg = (
                f"🧮 <b>GOOD ODDS CALCULATOR</b>\n\n"
                f"<b>Current match:</b>\n{match}\n{market}\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n\n"
                f"<b>What do you want to do?</b>"
            )
            kb = [
                [InlineKeyboardButton(text="✅ Recalculate EV with my CASHH", callback_data=f"calc_{eid}|safe")],
                [InlineKeyboardButton(text="💰 Test different amounts", callback_data=f"chg_cashhT_{token2}")],
                [InlineKeyboardButton(text="◀️ Back to alert", callback_data=f"back_to_main_{eid}")],
            ]
        await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    # For arbitrage/middle (need 2 outcomes)
    if len(outcomes) < 2:
        await callback.answer("❌ Données incomplètes", show_alert=True)
        return
    o1, o2 = outcomes[:2]
    if lang == 'fr':
        msg = (
            f"🧮 <b>CALCULATEUR CUSTOM</b>\n\n"
            f"Entre les cotes des 2 côtés pour calculer l'arbitrage.\n\n"
            f"<b>Match actuel:</b>\n{match}\n{market}\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n\n"
            f"<b>Que veux-tu faire?</b>"
        )
        kb = [
            [InlineKeyboardButton(text="✅ Recalculer avec mon CASHH", callback_data=f"calc_{eid}|safe")],
            [InlineKeyboardButton(text="💰 Changer le CASHH temporairement", callback_data=f"chg_cashhT_{token2}")],
            [InlineKeyboardButton(text="🔄 Changer les cotes", callback_data=f"chgo_{token2}")],
            [InlineKeyboardButton(text="◀️ Retour à l'alerte", callback_data=f"back_to_main_{eid}")],
        ]
    else:
        msg = (
            f"🧮 <b>CUSTOM CALCULATOR</b>\n\n"
            f"Enter odds for both sides to calculate arbitrage.\n\n"
            f"<b>Current match:</b>\n{match}\n{market}\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n\n"
            f"<b>What do you want to do?</b>"
        )
        kb = [
            [InlineKeyboardButton(text="✅ Recalculate with my CASHH", callback_data=f"calc_{eid}|safe")],
            [InlineKeyboardButton(text="💰 Change CASHH temporarily", callback_data=f"chg_cashhT_{token2}")],
            [InlineKeyboardButton(text="🔄 Change odds", callback_data=f"chgo_{token2}")],
            [InlineKeyboardButton(text="◀️ Back to alert", callback_data=f"back_to_main_{eid}")],
        ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@calc_router.callback_query(F.data.startswith("back_to_main_"))
async def back_to_main_arbitrage(callback: types.CallbackQuery):
    """Return to main alert message with consistent format for all bet types"""
    await safe_callback_answer(callback)
    # Extract eid correctly: back_to_main_1354 -> 1354
    eid = callback.data.replace("back_to_main_", "") if callback.data else ""
    
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    
    # Get user preferences
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    bet_type = drop.get('bet_type', 'arbitrage')
    
    # Format message based on bet_type using rich formatters
    if bet_type == 'good_ev':
        from utils.oddsjam_formatters import format_good_odds_message
        try:
            text = format_good_odds_message(drop, bankroll, lang)
        except Exception as e:
            logger.error(f"Error formatting Good EV back to alert: {e}")
            await callback.answer("❌ Erreur" if lang=='fr' else "❌ Error", show_alert=True)
            return
        # Get outcome for casino button and calculate I BET values
        outcomes = drop.get('outcomes', [])
        if outcomes:
            o1 = outcomes[0]
            casino_lower = (o1.get('casino', '') or '').lower()
            casino_name = o1.get('casino', '')
            
            # Extract the ORIGINAL stake from outcome (includes original bankroll calculation)
            rec_stake = o1.get('stake', 0)
            
            if rec_stake:
                # Calculate EV profit from original stake
                try:
                    odds = int(o1.get('odds', 0))
                    from utils.oddsjam_parser import american_to_decimal
                    decimal_odds = american_to_decimal(odds)
                    true_prob = drop.get('true_probability', 0.5)
                    edge = (decimal_odds * true_prob) - 1
                    rec_ev_profit = rec_stake * edge
                except Exception:
                    rec_ev_profit = 0
            else:
                # Fallback: recalculate with current bankroll
                try:
                    odds = int(o1.get('odds', 0))
                    from utils.oddsjam_parser import american_to_decimal
                    decimal_odds = american_to_decimal(odds)
                    true_prob = drop.get('true_probability', 0.5)
                    
                    # Kelly fraction
                    kelly_fraction = 0.25
                    edge = (decimal_odds * true_prob) - 1
                    if edge > 0:
                        rec_stake = bankroll * (edge / (decimal_odds - 1)) * kelly_fraction
                        rec_stake = min(rec_stake, bankroll * 0.05)  # Max 5%
                    else:
                        rec_stake = bankroll * 0.01
                    
                    rec_ev_profit = rec_stake * edge
                except Exception:
                    rec_stake = bankroll * 0.01
                    rec_ev_profit = 0
            
            kb = [
                [InlineKeyboardButton(text=f"{get_casino_logo(casino_name)} {casino_name}", callback_data=f"open_casino_{casino_lower.replace(' ', '_')}")],
                [InlineKeyboardButton(
                    text=(f"💰 I BET (+${rec_ev_profit:.2f} if win)" if lang=='en' else f"💰 JE PARIE (+${rec_ev_profit:.2f} profit)"),
                    callback_data=f"good_ev_bet_{eid}_{rec_stake:.2f}_{rec_ev_profit:.2f}"
                )],
                [InlineKeyboardButton(text="🧮 Custom Calculator" if lang=='en' else "🧮 Calculateur Custom", callback_data=f"calc_{eid}|menu")],
                [InlineKeyboardButton(text="📊 Simulation & Risk" if lang=='en' else "📊 Simulation & Risque", callback_data=f"sim_{eid}")],
                [InlineKeyboardButton(text="💵 Change CASHH" if lang=='en' else "💵 Changer CASHH", callback_data=f"chg_cashh_{eid}")],
            ]
        else:
            kb = [[InlineKeyboardButton(text="◀️ Back", callback_data=f"calc_{eid}|menu")]]
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    elif bet_type == 'middle':
        from utils.oddsjam_formatters import format_middle_message
        try:
            text = format_middle_message(drop, {}, bankroll, lang, rounding=0)
        except Exception as e:
            logger.error(f"Error formatting Middle back to alert: {e}")
            await callback.answer("❌ Erreur" if lang=='fr' else "❌ Error", show_alert=True)
            return
        # Get outcomes for casino buttons and calculate I BET values
        outcomes = drop.get('outcomes', [])
        casino_buttons = []
        for outcome_data in outcomes[:2]:
            casino_name = outcome_data.get('casino', 'Unknown')
            casino_lower = casino_name.lower()
            casino_buttons.append(InlineKeyboardButton(
                text=f"{get_casino_logo(casino_name)} {casino_name}",
                callback_data=f"open_casino_{casino_lower.replace(' ', '_')}"
            ))

        # Always recompute Middle stakes from CURRENT bankroll and odds
        # to avoid legacy unit-stake artifacts (e.g. 11$ / 0.34 / 11.69).
        try:
            from utils.middle_calculator import calculate_middle_stakes
            odds_a_raw = outcomes[0].get('odds', 0) if len(outcomes) > 0 else 0
            odds_b_raw = outcomes[1].get('odds', 0) if len(outcomes) > 1 else 0
            odds_a = int(str(odds_a_raw).replace('+', '').replace('−', '-'))
            odds_b = int(str(odds_b_raw).replace('+', '').replace('−', '-'))
            rec_calc = calculate_middle_stakes(odds_a, odds_b, bankroll)
            rec_total_stake = rec_calc.get('total_stake', bankroll)
            # MIN profit (guaranteed when only one side wins)
            rec_no_middle_profit = min(rec_calc.get('profit_a_only', 0), rec_calc.get('profit_b_only', 0))
            # JACKPOT profit (if both sides win / win+push middle scenario)
            rec_middle_profit = rec_calc.get('profit_both', 0)
        except Exception:
            rec_total_stake = bankroll
            rec_no_middle_profit = 0
            rec_middle_profit = 0
        
        kb = [
            casino_buttons if len(casino_buttons)==2 else [casino_buttons[0]] if casino_buttons else [],
            [InlineKeyboardButton(
                text=(f"💰 I BET (${rec_no_middle_profit:.2f} profit)" if lang=='en' else f"💰 JE PARIE (${rec_no_middle_profit:.2f} profit)"),
                callback_data=f"middle_bet_{eid}_{rec_total_stake:.2f}_{rec_no_middle_profit:.2f}_{rec_middle_profit:.2f}"
            )],
            [InlineKeyboardButton(text="🧮 Custom Calculator" if lang=='en' else "🧮 Calculateur Custom", callback_data=f"calc_{eid}|menu")],
            [InlineKeyboardButton(text="📊 Simulation & Risk" if lang=='en' else "📊 Simulation & Risque", callback_data=f"sim_{eid}")],
            [InlineKeyboardButton(text="💵 Change CASHH" if lang=='en' else "💵 Changer CASHH", callback_data=f"chg_cashh_{eid}")],
        ]
        kb = [row for row in kb if row]  # Remove empty rows
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    # For Arbitrage: use existing formatter
    user_rounding, user_mode = _get_user_rounding(callback.from_user.id)
    text, stakes = _format_arbitrage_message(drop, bankroll, lang, user_rounding, user_mode)
    
    # Build keyboard for main message
    drop_event_id = drop.get('drop_event_id', eid)
    
    # Calculate profit for I BET button
    odds_list = [int(o.get('odds', 0)) for o in drop.get('outcomes', [])][:2]
    calc = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
    profit = calc.get('profit', 0)
    
    keyboard = []
    
    # Casino buttons
    casino_buttons = []
    for out in drop.get('outcomes', [])[:2]:
        casino_name = out.get('casino')
        link = get_casino_referral_link(casino_name) or get_fallback_url(casino_name)
        if link:
            casino_buttons.append(InlineKeyboardButton(
                text=f"{get_casino_logo(casino_name)} {casino_name}",
                url=link
            ))
    if casino_buttons:
        keyboard.append(casino_buttons)
    
    # Action buttons
    i_bet_text = f"💰 JE PARIE (${profit:.2f} profit)" if lang == 'fr' else f"💰 I BET (${profit:.2f} profit)"
    keyboard.append([
        InlineKeyboardButton(text=i_bet_text, callback_data=f"i_bet_{drop_event_id}_{bankroll:.0f}_{profit:.2f}")
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🧮 Calculateur Custom" if lang == 'fr' else "🧮 Custom Calculator",
            callback_data=f"calc_{eid}|menu"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="💰 Changer CASHH" if lang == 'fr' else "💰 Change CASHH",
            callback_data=f"chg_cashh_{eid}"
        )
    ])
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@calc_router.callback_query(F.data.startswith("chg_cashhT_"))
async def token_change_cashh(callback: types.CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    token = (callback.data or "").split("_", 1)[1] if "_" in (callback.data or "") else ""
    eid = CALC_TOKENS.get(token)
    if not eid:
        await callback.answer("❌ Drop expiré", show_alert=True)
        return
    lang = _get_user_prefs(callback.from_user.id)[1]
    amounts = [100, 200, 300, 500, 1000]
    rows = [[InlineKeyboardButton(text=f"${a}", callback_data=f"acb_{token}_{a}")] for a in amounts]
    rows.append([InlineKeyboardButton(text=("✏️ Montant personnalisé" if lang=='fr' else "✏️ Custom amount"), callback_data=f"cashh_custT_{token}")])
    rows.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data=f"cmenu_{token}")])
    prompt = ("💰 <b>Changer CASHH (par appel)</b>\nChoisis un montant rapide:" if lang=='fr' else "💰 <b>Change CASHH (per-call)</b>\nChoose a quick amount:")
    await callback.message.edit_text(prompt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@calc_router.callback_query(F.data.startswith("calc_risked_start_"))
async def calc_risked_start_handler(callback: types.CallbackQuery):
    """Start RISKED mode - ask for risk % with quick buttons"""
    await callback.answer()
    try:
        eid = callback.data.split('_')[3]
    except Exception:
        return
    if not _get_drop(eid):
        await callback.answer("❌ Drop expiré" if (_get_user_prefs(callback.from_user.id)[1]=='fr') else "❌ Drop expired", show_alert=True)
        return
    lang = _get_user_prefs(callback.from_user.id)[1]
    if lang == 'fr':
        msg = (
            "⚠️ <b>MODE RISKED - AVANCÉ</b>\n\n"
            "Dans ce mode, tu acceptes une PETITE PERTE possible pour un GROS gain potentiel.\n\n"
            "🎯 <b>Quel % es-tu prêt à risquer?</b>"
        )
        back = "◀️ Retour SAFE"
    else:
        msg = (
            "⚠️ <b>RISKED MODE - ADVANCED</b>\n\n"
            "In this mode, you accept a SMALL LOSS for a BIG potential gain.\n\n"
            "🎯 <b>What % are you willing to risk?</b>"
        )
        back = "◀️ Back SAFE"
    kb = [
        [InlineKeyboardButton(text="3%", callback_data=f"calc_risk_set_{eid}|3"), InlineKeyboardButton(text="5%", callback_data=f"calc_risk_set_{eid}|5"), InlineKeyboardButton(text="10%", callback_data=f"calc_risk_set_{eid}|10")],
        [InlineKeyboardButton(text=back, callback_data=f"calc_{eid}|safe")],
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@calc_router.callback_query(F.data.startswith("calc_risk_set_"))
async def calc_risk_set_handler(callback: types.CallbackQuery):
    """User selected risk % → ask which side to favor"""
    await callback.answer()
    try:
        parts = callback.data.split('|')
        eid = parts[0].split('_')[3]
        risk_pct = float(parts[1])
    except Exception:
        return
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré" if (_get_user_prefs(callback.from_user.id)[1]=='fr') else "❌ Drop expired", show_alert=True)
        return
    lang = _get_user_prefs(callback.from_user.id)[1]
    outs = drop.get('outcomes', [])[:2]
    o1, o2 = outs
    if lang == 'fr':
        msg = f"⚠️ <b>RISKED {risk_pct}%</b>\n\n<b>Sur quel côté miser PLUS?</b>"
    else:
        msg = f"⚠️ <b>RISKED {risk_pct}%</b>\n\n<b>Which side to stake MORE?</b>"
    kb = [
        [InlineKeyboardButton(text=f"{get_casino_logo(o1.get('casino',''))} {o1.get('casino','')} - {o1.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|0")],
        [InlineKeyboardButton(text=f"{get_casino_logo(o2.get('casino',''))} {o2.get('casino','')} - {o2.get('outcome','')}", callback_data=f"calc_risk_favor_{eid}|{risk_pct}|1")],
        [InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data=f"calc_risked_start_{eid}")],
    ]
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
@calc_router.callback_query(F.data.startswith("calc_risk_favor_"))
async def calc_risk_favor_handler(callback: types.CallbackQuery):
    """Render RISKED calculation with favor and provide +/- and swap controls"""
    logger.info(f"🎯 RISKED: calc_risk_favor callback received: {callback.data}")
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        parts = (callback.data or "").split('|')
        eid = parts[0].split('_')[3]
        risk_pct = float(parts[1])
        favor = int(parts[2])
        # Clamp to 0.5-99%
        risk_pct = max(0.5, min(99.0, risk_pct))
        logger.info(f"🎯 RISKED: Parsed eid={eid}, risk_pct={risk_pct}, favor={favor}")
    except Exception as e:
        logger.error(f"❌ RISKED: Failed to parse callback data: {e}")
        try:
            await callback.answer("❌ Invalid parameters", show_alert=True)
        except Exception:
            pass
        return
    drop = _get_drop(eid)
    if not drop:
        logger.error(f"❌ RISKED: Drop not found for eid={eid}")
        await callback.answer("❌ Drop expired", show_alert=True)
        return
    logger.info(f"✅ RISKED: Drop found for eid={eid}")
    bankroll, lang, _ = _get_user_prefs(callback.from_user.id)
    outs = drop.get('outcomes', [])[:2]
    if len(outs) < 2:
        await callback.answer("❌ Not enough outcomes", show_alert=True)
        return
    o1, o2 = outs
    def _parse_odds(v):
        try:
            return int(str(v).replace('+','').strip())
        except Exception:
            return 0
    odds = [_parse_odds(o1.get('odds',0)), _parse_odds(o2.get('odds',0))]
    logger.info(f"🎯 RISKED: bankroll={bankroll}, odds={odds}, risk_pct={risk_pct}, favor={favor}")
    try:
        res = ArbitrageCalculator.calculate_risked_stakes(bankroll, odds, risk_percentage=risk_pct, favor_outcome=favor)
        stakes = res.get('stakes', [0,0])
        profits = res.get('profits', [0,0])
        logger.info(f"✅ RISKED: Calculation successful - stakes={stakes}, profits={profits}")
        
        # Calculate RISKED EV
        from utils.risked_ev_calculator import compute_risked_ev
        ev_data = compute_risked_ev(odds[0], stakes[0], odds[1], stakes[1])
        logger.info(f"📊 RISKED EV: {ev_data}")
        
    except Exception as e:
        logger.error(f"❌ RISKED: Failed to compute stakes: {e}")
        await callback.message.edit_text("❌ Failed to compute RISKED stakes.")
        return
    odds1 = f"+{odds[0]}" if odds[0] > 0 else str(odds[0])
    odds2 = f"+{odds[1]}" if odds[1] > 0 else str(odds[1])
    
    # Identify jackpot side (the one with positive profit) and risk side (the one with loss)
    jackpot_idx = 0 if profits[0] > profits[1] else 1
    risk_idx = 1 - jackpot_idx
    
    jackpot_name = o1.get('casino','') if jackpot_idx==0 else o2.get('casino','')
    risk_name = o2.get('casino','') if jackpot_idx==0 else o1.get('casino','')
    
    # Calculate CORRECT break-even for the jackpot side
    # EV = p_jackpot × profit_jackpot + (1 - p_jackpot) × profit_risk = 0
    # Solving: p_jackpot = abs(profit_risk) / (profit_jackpot + abs(profit_risk))
    profit_jackpot = profits[jackpot_idx]
    profit_risk = profits[risk_idx]
    break_even_jackpot = abs(profit_risk) / (profit_jackpot + abs(profit_risk)) if (profit_jackpot + abs(profit_risk)) != 0 else 0
    
    # Get fair probability for jackpot side
    fair_prob_jackpot = ev_data['p_a_fair'] if jackpot_idx == 0 else ev_data['p_b_fair']
    if lang == 'fr':
        msg = (
            f"⚠️ <b>CALCUL RISKED - RISQUE {risk_pct:.1f}%</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"⚠️ Risque accepté: {risk_pct:.1f}% (${abs(profits[risk_idx]):.2f})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Cote: {odds1}\n"
            f"💵 Miser: <b>${stakes[0]:.2f}</b>\n"
            f"📈 Si gagne → Résultat net: <b>${profits[0]:.2f}</b> {'👑' if 0==jackpot_idx else '💣'}\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Cote: {odds2}\n"
            f"💵 Miser: <b>${stakes[1]:.2f}</b>\n"
            f"📈 Si gagne → Résultat net: <b>${profits[1]:.2f}</b> {'👑' if 1==jackpot_idx else '💣'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Résumé RISKED</b>\n"
            f"👑 <b>JACKPOT ({jackpot_name}):</b> NET +${profits[jackpot_idx]:.2f}\n"
            f"💣 <b>RISQUE ({risk_name}):</b> NET ${profits[risk_idx]:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧮 <b>ANALYSE EV (Mathématique pure)</b>\n\n"
            f"📈 <b>EV neutre marché:</b> {ev_data['ev_fair_pct']:+.2f}%\n"
            f"💰 EV en dollars: ${ev_data['ev_fair']:+.2f} sur ${ev_data['total_stake']:.2f}\n\n"
            f"⚖️ <b>Probabilités fair (sans vig):</b>\n"
            f"• {o1.get('outcome', 'A')}: {ev_data['p_a_fair']*100:.1f}%\n"
            f"• {o2.get('outcome', 'B')}: {ev_data['p_b_fair']*100:.1f}%\n\n"
            f"🎯 <b>Break-even côté jackpot ({jackpot_name}):</b>\n"
            f"• Besoin: {break_even_jackpot*100:.1f}% de chances réelles\n"
            f"• Marché: {fair_prob_jackpot*100:.1f}%\n\n"
            f"⚠️ <i>📊 <b>IMPORTANT:</b> Le mode RISKED ne crée pas plus de value.\n"
            f"Il transforme un profit garanti modeste en:\n"
            f"• 👑 Gros gain si ton favori passe\n"
            f"• 💣 Perte contrôlée si l'autre gagne\n\n"
            f"L'EV global reste celui du marché (~4-5% sur ce match).\n"
            f"C'est un choix de variance, pas d'argent gratuit.</i>"
        )
    else:
        msg = (
            f"⚠️ <b>RISKED CALCULATION - RISK {risk_pct:.1f}%</b>\n\n"
            f"💰 CASHH: ${bankroll:.2f}\n"
            f"⚠️ Accepted risk: {risk_pct:.1f}% (${abs(profits[risk_idx]):.2f})\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
            f"Odds: {odds1}\n"
            f"💵 Stake: <b>${stakes[0]:.2f}</b>\n"
            f"📈 If wins → Net result: <b>${profits[0]:.2f}</b> {'👑' if 0==jackpot_idx else '💣'}\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
            f"Odds: {odds2}\n"
            f"💵 Stake: <b>${stakes[1]:.2f}</b>\n"
            f"📈 If wins → Net result: <b>${profits[1]:.2f}</b> {'👑' if 1==jackpot_idx else '💣'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>RISKED Summary</b>\n"
            f"👑 <b>JACKPOT ({jackpot_name}):</b> NET +${profits[jackpot_idx]:.2f}\n"
            f"💣 <b>RISK ({risk_name}):</b> NET ${profits[risk_idx]:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧮 <b>EV ANALYSIS (Pure Math)</b>\n\n"
            f"📈 <b>Market-neutral EV:</b> {ev_data['ev_fair_pct']:+.2f}%\n"
            f"💰 EV in dollars: ${ev_data['ev_fair']:+.2f} on ${ev_data['total_stake']:.2f}\n\n"
            f"⚖️ <b>Fair probabilities (no vig):</b>\n"
            f"• {o1.get('outcome', 'A')}: {ev_data['p_a_fair']*100:.1f}%\n"
            f"• {o2.get('outcome', 'B')}: {ev_data['p_b_fair']*100:.1f}%\n\n"
            f"🎯 <b>Break-even jackpot side ({jackpot_name}):</b>\n"
            f"• Needs: {break_even_jackpot*100:.1f}% real chance\n"
            f"• Market: {fair_prob_jackpot*100:.1f}%\n\n"
            f"⚠️ <i>📊 <b>IMPORTANT:</b> RISKED mode doesn't create more value.\n"
            f"It transforms a small guaranteed profit into:\n"
            f"• 👑 Big gain if your favorite wins\n"
            f"• 💣 Controlled loss if the other wins\n\n"
            f"Global EV stays the same as the market (~4-5% on this match).\n"
            f"It's a variance choice, not free money.</i>"
        )
    kb = [
        [InlineKeyboardButton(text="-1%", callback_data=f"calc_risk_favor_{eid}|{max(risk_pct-1,0.5)}|{favor}"), InlineKeyboardButton(text=f"{risk_pct:.1f}%", callback_data="noop"), InlineKeyboardButton(text="+1%", callback_data=f"calc_risk_favor_{eid}|{min(risk_pct+1,99)}|{favor}")],
        [InlineKeyboardButton(text=("🔄 Inverser favori" if lang=='fr' else "🔄 Swap favor"), callback_data=f"calc_risk_favor_{eid}|{risk_pct}|{1-favor}")],
        [InlineKeyboardButton(text=("✅ Retour SAFE" if lang=='fr' else "✅ Back SAFE"), callback_data=f"calc_{eid}|safe")],
        [InlineKeyboardButton(text=("◀️ Retour menu" if lang=='fr' else "◀️ Back menu"), callback_data=f"calc_{eid}|menu")],
    ]
    try:
        await callback.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        logger.info(f"✅ RISKED: Message edited successfully for eid={eid}")
    except Exception as e:
        logger.error(f"⚠️ RISKED: Failed to edit message, sending new one: {e}")
        # Fallback: send a new message
        try:
            await callback.message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            logger.info(f"✅ RISKED: New message sent for eid={eid}")
        except Exception as e2:
            logger.error(f"❌ RISKED: Failed to send new message: {e2}")


@calc_router.callback_query(F.data.startswith("calc_changeodds_"))
async def calc_changeodds_handler(callback: types.CallbackQuery, state: FSMContext):
    """Start change odds flow: ask first side"""
    await callback.answer()
    try:
        eid = callback.data.split('_')[2]
    except Exception:
        return
    drop = _get_drop(eid)
    if not drop:
        await callback.answer("❌ Drop expiré" if (_get_user_prefs(callback.from_user.id)[1]=='fr') else "❌ Drop expired", show_alert=True)
        return
    outs = drop.get('outcomes', [])[:2]
    o1, o2 = outs
    lang = _get_user_prefs(callback.from_user.id)[1]
    await state.set_state(CalculatorStates.awaiting_odds_side1)
    await state.update_data(eid=eid, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    
    # Convert odds to int for display (might be stored as string)
    try:
        odds1_val = int(o1.get('odds', 0))
    except (ValueError, TypeError):
        odds1_val = 0
    odds1_str = f"+{odds1_val}" if odds1_val > 0 else str(odds1_val)
    
    if lang == 'fr':
        msg = (
            f"🔄 <b>CHANGER LES COTES</b>\n\n"
            f"🚨 <b>IMPORTANT:</b> Vérifie SUR LE SITE:\n"
            f"1️⃣ La LIGNE (Over/Under X.5)\n"
            f"2️⃣ Les COTES (+105, -110, etc.)\n\n"
            f"⚠️ Si la LIGNE a changé = Plus d'arbitrage!\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Cote actuelle: {odds1_str}\n"
            f"<b>Nouvelle cote?</b> (ex: +105, -110)"
        )
    else:
        msg = (
            f"🔄 <b>CHANGE ODDS</b>\n\n"
            f"🚨 <b>IMPORTANT:</b> Check ON THE SITE:\n"
            f"1️⃣ The LINE (Over/Under X.5)\n"
            f"2️⃣ The ODDS (+105, -110, etc.)\n\n"
            f"⚠️ If the LINE changed = No more arbitrage!\n\n"
            f"{get_casino_logo(o1.get('casino',''))} <b>{o1.get('casino','')}</b> - Current odds: {odds1_str}\n"
            f"<b>New odds?</b> (eg: +105, -110)"
        )
    await callback.message.edit_text(msg, parse_mode=ParseMode.HTML)


@dp.message(CalculatorStates.awaiting_odds_side1)
async def handle_odds_side1(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        odds1 = int(text.replace('+','').replace(' ',''))
    except Exception:
        await message.answer("❌ Cote invalide. Ex: +105 ou -110")
        return
    await state.update_data(odds1=odds1)
    data = await state.get_data()
    eid = data.get('eid')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    
    # Get drop and extract o2
    drop = _get_drop(eid)
    if not drop:
        await message.answer("❌ Drop expiré")
        await state.clear()
        return
    outs = drop.get('outcomes', [])[:2]
    o1, o2 = (outs[0] if len(outs)>0 else {}), (outs[1] if len(outs)>1 else {})
    _, lang, _ = _get_user_prefs(message.from_user.id)
    
    await state.set_state(CalculatorStates.awaiting_odds_side2)
    
    # Convert odds2 to int for display (might be stored as string)
    try:
        odds2_val = int(o2.get('odds', 0))
    except (ValueError, TypeError):
        odds2_val = 0
    odds2_str = f"+{odds2_val}" if odds2_val > 0 else str(odds2_val)
    
    if lang == 'fr':
        msg = (
            f"✅ Parfait! {'+' if odds1>0 else ''}{odds1} pour le premier côté.\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>{o2.get('casino','')}</b> - Cote actuelle: {odds2_str}\n"
            f"<b>Nouvelle cote?</b> (ex: +130, -115)"
        )
    else:
        msg = (
            f"✅ Perfect! {'+' if odds1>0 else ''}{odds1} for first side.\n\n"
            f"{get_casino_logo(o2.get('casino',''))} <b>{o2.get('casino','')}</b> - Current odds: {odds2_str}\n"
            f"<b>New odds?</b> (eg: +130, -115)"
        )
    # Send a new message so the user sees the conversation flow naturally
    await message.answer(msg, parse_mode=ParseMode.HTML)

@dp.message(CalculatorStates.awaiting_odds_side2)
async def handle_odds_side2(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        odds2 = int(text.replace('+','').replace(' ',''))
    except Exception:
        await message.answer("❌ Cote invalide. Ex: +130 ou -115")
        return
    data = await state.get_data()
    eid = data.get('eid')
    odds1 = data.get('odds1')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    drop = _get_drop(eid)
    if not drop:
        await message.answer("❌ Drop expiré")
        await state.clear()
        return
    bankroll = _get_user_prefs(message.from_user.id)[0]
    new_odds = [odds1, odds2]
    res = ArbitrageCalculator.calculate_safe_stakes(bankroll, new_odds)
    stakes = res.get('stakes', [0,0])
    returns = res.get('returns', [0,0])
    profit = res.get('profit', 0)
    roi_percent = res.get('roi_percent', 0.0)
    has_arb = bool(res.get('has_arbitrage'))
    inverse_sum = res.get('inverse_sum', 1.0)
    outs = drop.get('outcomes', [])[:2]
    o1, o2 = outs
    odds1_str = f"+{new_odds[0]}" if new_odds[0] > 0 else str(new_odds[0])
    odds2_str = f"+{new_odds[1]}" if new_odds[1] > 0 else str(new_odds[1])
    lang = _get_user_prefs(message.from_user.id)[1]
    # Choose icon based on profit
    icon = "✅" if profit > 0 else "❌"
    
    if lang == 'fr':
        if has_arb:
            # Arbitrage still exists
            msg = (
                f"✅ <b>NOUVEAU CALCUL</b>\n\n"
                f"💰 CASHH: ${bankroll:.2f}\n"
                f"✅ Profit: <b>${profit:.2f}</b> (ROI: {roi_percent:.2f}%)\n"
                f"✅ Il y a TOUJOURS un arbitrage avec ces cotes.\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
                f"Cote: {odds1_str}\n"
                f"💵 Miser: <b>${stakes[0]:.2f}</b> → Retour: <b>${returns[0]:.2f}</b>\n\n"
                f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
                f"Cote: {odds2_str}\n"
                f"💵 Miser: <b>${stakes[1]:.2f}</b> → Retour: <b>${returns[1]:.2f}</b>\n\n"
                f"🚨 <b>ATTENTION CRITIQUE:</b>\n"
                f"⚠️ Vérifie que les LIGNES (Over/Under X.5) sont IDENTIQUES sur les deux sites!\n"
                f"⚠️ Si la ligne a changé (ex: 5.5 → 6.5), ce n'est PLUS un arbitrage!\n"
                f"⚠️ Ceci est une SIMULATION - l'alerte originale n'est pas modifiée.\n"
            )
        else:
            # NO MORE ARBITRAGE - but show optimal stakes for minimal loss
            # Calculate best guaranteed return if forcing the bet
            best_return = bankroll / inverse_sum if inverse_sum > 0 else 0
            min_loss = abs(profit)  # Profit is negative, so abs gives loss
            
            msg = (
                f"❌ <b>NOUVEAU CALCUL (APRÈS CHANGEMENT DE COTES)</b>\n\n"
                f"💰 CASHH: ${bankroll:.2f}\n"
                f"❌ Arbitrage: <b>AUCUN</b> (profit garanti impossible avec ces cotes)\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
                f"Cote: {odds1_str}\n"
                f"💵 Mise calculée: <b>${stakes[0]:.2f}</b> → Retour: <b>${returns[0]:.2f}</b>\n\n"
                f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
                f"Cote: {odds2_str}\n"
                f"💵 Mise calculée: <b>${stakes[1]:.2f}</b> → Retour: <b>${returns[1]:.2f}</b>\n\n"
                f"📊 <b>Analyse avancée:</b>\n"
                f"Même en optimisant les mises pour égaliser les retours:\n\n"
                f"• Retour garanti maximal possible ≈ <b>${best_return:.2f}</b>\n"
                f"• Perte minimale garantie ≈ <b>-${min_loss:.2f}</b>\n\n"
                f"➡️ Conclusion: ces cotes ne permettent PLUS aucun arbitrage mathématique.\n"
                f"➡️ Continuer à bet ce montage reviendrait à accepter une perte certaine.\n\n"
                f"🚨 <b>ATTENTION CRITIQUE:</b>\n"
                f"⚠️ Vérifie que les LIGNES (Over/Under X.5, spread, total, etc.) sont IDENTIQUES sur les deux sites!\n"
                f"⚠️ Si la ligne a changé (ex: 3.5 → 4.5), ce n'est plus un arbitrage même si les cotes semblent belles.\n"
                f"⚠️ Ceci est une SIMULATION sur les nouvelles cotes - l'alerte originale n'est pas modifiée.\n"
            )
    else:
        if has_arb:
            # Arbitrage still exists
            msg = (
                f"✅ <b>NEW CALCULATION</b>\n\n"
                f"💰 CASHH: ${bankroll:.2f}\n"
                f"✅ Profit: <b>${profit:.2f}</b> (ROI: {roi_percent:.2f}%)\n"
                f"✅ There is STILL arbitrage with these odds.\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
                f"Odds: {odds1_str}\n"
                f"💵 Stake: <b>${stakes[0]:.2f}</b> → Return: <b>${returns[0]:.2f}</b>\n\n"
                f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
                f"Odds: {odds2_str}\n"
                f"💵 Stake: <b>${stakes[1]:.2f}</b> → Return: <b>${returns[1]:.2f}</b>\n\n"
                f"🚨 <b>CRITICAL WARNING:</b>\n"
                f"⚠️ Verify that the LINES (Over/Under X.5) are IDENTICAL on both sites!\n"
                f"⚠️ If the line changed (e.g., 5.5 → 6.5), this is NO LONGER an arbitrage!\n"
                f"⚠️ This is a SIMULATION - the original alert is not modified.\n"
            )
        else:
            # NO MORE ARBITRAGE - but show optimal stakes for minimal loss
            best_return = bankroll / inverse_sum if inverse_sum > 0 else 0
            min_loss = abs(profit)
            
            msg = (
                f"❌ <b>NEW RECALCULATION (AFTER ODDS CHANGE)</b>\n\n"
                f"💰 CASHH: ${bankroll:.2f}\n"
                f"❌ Arbitrage: <b>NONE</b> (no guaranteed profit with these odds)\n\n"
                f"{get_casino_logo(o1.get('casino',''))} <b>[{o1.get('casino','')}]</b> {o1.get('outcome','')}\n"
                f"Odds: {odds1_str}\n"
                f"💵 Calculated stake: <b>${stakes[0]:.2f}</b> → Return: <b>${returns[0]:.2f}</b>\n\n"
                f"{get_casino_logo(o2.get('casino',''))} <b>[{o2.get('casino','')}]</b> {o2.get('outcome','')}\n"
                f"Odds: {odds2_str}\n"
                f"💵 Calculated stake: <b>${stakes[1]:.2f}</b> → Return: <b>${returns[1]:.2f}</b>\n\n"
                f"📊 <b>Advanced analysis:</b>\n"
                f"Even by optimizing stakes to equalize returns:\n\n"
                f"• Maximum guaranteed return possible ≈ <b>${best_return:.2f}</b>\n"
                f"• Minimum guaranteed loss ≈ <b>-${min_loss:.2f}</b>\n\n"
                f"➡️ Conclusion: these odds NO LONGER allow any mathematical arbitrage.\n"
                f"➡️ Continuing to bet this setup would mean accepting a certain loss.\n\n"
                f"🚨 <b>CRITICAL WARNING:</b>\n"
                f"⚠️ Always check that the LINES (Over/Under X.5, spread, total, etc.) match on both books!\n"
                f"⚠️ If the line moved (e.g. 3.5 → 4.5), this is no longer arbitrage even if odds look attractive.\n"
                f"⚠️ This is a SIMULATION on updated odds – the original alert is not modified.\n"
            )

    kb = [[InlineKeyboardButton(text=("◀️ Retour à l'alerte originale" if lang=='fr' else "◀️ Back to original alert"), callback_data=f"calc_{eid}|menu")]]

    # Send a new message so the result appears right after the user's typed message
    await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALCULATOR CUSTOM FOR GOOD ODDS AND MIDDLE
# Based on arbitrage calculator but adapted for each type
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Old handlers removed - Middle and Good EV now use the unified calc system via calc_{eid}|menu


@calc_router.callback_query(F.data == "noop")
async def noop_handler(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("verify_odds:"))
async def callback_verify_odds(callback: types.CallbackQuery):
    """Handle odds verification request"""
    logger.info(f"🔍 Verify odds callback triggered by user {callback.from_user.id}")
    await safe_callback_answer(callback, "Vérification en cours...")
    
    try:
        # Extract call ID
        call_id = callback.data.split(":")[1]
        logger.info(f"🔍 Extracted call_id: {call_id}")
        
        # Get the pending call or reconstruct
        betting_call = PENDING_CALLS.get(call_id)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            lang_pref = user.language if user else "en"
            user_bankroll = user.default_bankroll if user else 750.0
        finally:
            db.close()
        if not betting_call:
            logger.warning(f"⚠️ Call {call_id} not found in PENDING_CALLS (might have restarted bot)")
            txt = (callback.message.text or callback.message.caption or "").strip()
            drop_like = _reconstruct_drop_from_message_text(txt)
            if not drop_like:
                await callback.answer("⚠️ Call expiré (bot redémarré). Essaye avec un call récent.", show_alert=True)
                return
            try:
                betting_call = process_call_from_drop(drop_like, user_bankroll)
                if not betting_call:
                    await callback.answer("⚠️ Impossible de reconstruire le call.", show_alert=True)
                    return
                call_id = betting_call.call_id
                PENDING_CALLS[call_id] = betting_call
                save_pending_calls()
            except Exception as e:
                logger.error(f"Failed to reconstruct call: {e}")
                await callback.answer("⚠️ Reconstruction impossible.", show_alert=True)
                return
        
        logger.info(f"✅ Found betting_call for {call_id}: {betting_call.match}")
        
        # Re-enrich with latest data
        previous_checked_at = betting_call.last_checked_at
        betting_call = enrich_call_with_odds_api(betting_call)
        betting_call = analyze_arbitrage_two_way(betting_call)

        # Determine if verification via API actually succeeded
        verified_success = bool(
            betting_call.last_checked_at
            and (previous_checked_at is None or betting_call.last_checked_at != previous_checked_at)
        )

        # Update stored call
        betting_call.last_checked_source = "user"
        PENDING_CALLS[call_id] = betting_call
        save_pending_calls()
        
        # Format updated message (only mark as verified on real success)
        message_text = format_call_message(
            betting_call,
            lang=lang_pref,
            verified=verified_success,
        )
        
        # Build updated keyboard
        keyboard = []
        
        # Casino buttons with updated links
        casino_buttons = []
        for side in betting_call.sides[:2]:
            # Priority: deep link > referral > fallback
            link = side.deep_link or None
            if not link:
                link = get_casino_referral_link(side.book_name)
            if not link:
                link = side.fallback_link
            
            # Always have a link (use generic site URL as last resort)
            if not link:
                link = f"https://{side.book_name.lower().replace(' ', '')}.com"
            
            logger.info(f"🔗 Verify callback - Casino button for {side.book_name}: deep={side.deep_link}, referral={get_casino_referral_link(side.book_name)}, fallback={side.fallback_link}, final={link}")
            
            if link:
                casino_buttons.append(
                    InlineKeyboardButton(
                        text=f"{get_casino_logo(side.book_name)} {side.book_name}",
                        url=link
                    )
                )
        
        if casino_buttons:
            keyboard.append(casino_buttons)
        
        # JE PARIE button with profit
        total_stake = sum(s.stake for s in betting_call.sides)
        expected_profit = betting_call.arb_analysis.min_profit if betting_call.arb_analysis else 0
        drop_id = betting_call.call_id
        
        i_bet_text = f"💰 JE PARIE (${expected_profit:.2f} profit)" if lang_pref == 'fr' else f"💰 I BET (${expected_profit:.2f} profit)"
        keyboard.append([
            InlineKeyboardButton(
                text=i_bet_text,
                callback_data=f"i_bet_{drop_id}_{total_stake:.0f}_{expected_profit:.2f}"
            )
        ])
        
        # Calculator button (check if user tier allows it)
        try:
            db = SessionLocal()
            user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
            if user:
                def _core_tier_from_model(t):
                    try:
                        name = t.name.lower()
                    except Exception:
                        return TierLevel.FREE
                    return TierLevel.PREMIUM if name == 'premium' else TierLevel.FREE
                tier_core = _core_tier_from_model(user.tier)
                features = TierManager.get_features(tier_core)
                if features.get('show_calculator'):
                    keyboard.append([
                        InlineKeyboardButton(
                            text="🧮 Calculateur Custom" if lang_pref == 'fr' else "🧮 Custom Calculator",
                            callback_data=f"calc_{drop_id}|menu"
                        )
                    ])
            db.close()
        except Exception:
            pass
        
        # Change CASHH button
        keyboard.append([
            InlineKeyboardButton(
                text="💰 Changer CASHH" if lang_pref == 'fr' else "💰 Change CASHH",
                callback_data=f"change_bankroll_{drop_id}"
            )
        ])
        
        # Vérifier les cotes button - DISABLED (not working properly)
        # keyboard.append([
        #     InlineKeyboardButton(
        #         text="✅ Vérifier les cotes" if lang_pref == 'fr' else "✅ Verify Odds",
        #         callback_data=f"verify_odds:{call_id}"
        #     )
        # ])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Edit message
        try:
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
            logger.info(f"✅ Updated message for call {call_id}, verified={verified_success}")
        except Exception as edit_err:
            logger.error(f"Failed to edit message: {edit_err}")
            await callback.answer("❌ Impossible de mettre à jour le message", show_alert=True)
            return
        
        # Show alert if arbitrage status changed
        if betting_call.arb_analysis:
            if betting_call.arb_analysis.status == "NO_ARB":
                await callback.answer(
                    "⚠️ L'arbitrage n'est plus disponible!" if lang_pref == 'fr' else "⚠️ Arbitrage no longer available!",
                    show_alert=True
                )
            elif betting_call.arb_analysis.has_changed:
                await callback.answer(
                    "ℹ️ Les cotes ont changé" if lang_pref == 'fr' else "ℹ️ Odds have changed",
                    show_alert=True
                )
        
    except Exception as e:
        logger.error(f"Failed to verify odds: {e}")
        await callback.answer("❌ Erreur lors de la vérification", show_alert=True)

@dp.callback_query(lambda c: c.data and c.data == "show_casinos")
async def callback_show_casinos(callback: types.CallbackQuery):
    """Show Last Calls categories: Arbitrage / Middle / Good EV."""
    await casino_handlers.show_casinos_menu(callback)


@dp.callback_query(F.data == "last_arbi")
async def cb_last_arbitrages(callback: types.CallbackQuery):
    await callback.answer()
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    header = "📈 Arbitrage - 10 derniers" if lang == 'fr' else "📈 Arbitrage - last 10"
    db = SessionLocal()
    try:
        events = (
            db.query(DropEvent)
            .order_by(DropEvent.received_at.desc())
            .limit(10)
            .all()
        )
        if not events:
            empty = "Aucun arbitrage récent." if lang == 'fr' else "No recent arbitrage."
            kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")]]
            await callback.message.edit_text(f"{header}\n\n{empty}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            return
        rows = []
        for ev in events:
            title = ev.match or 'Match'
            if len(title) > 42:
                title = title[:39] + '…'
            pct = ev.arb_percentage if ev.arb_percentage is not None else 0
            btn_text = f"📥 {title} — {pct}%"
            rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"alert_{ev.event_id}|safe")])
        rows.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")])
        await callback.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    finally:
        db.close()


@dp.callback_query(F.data == "last_middle")
async def cb_last_middle(callback: types.CallbackQuery):
    await callback.answer()
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    header = "🎯 Middle - récents" if lang == 'fr' else "🎯 Middle - recent"
    if not LAST_MIDDLES:
        empty = "Aucun middle récent." if lang == 'fr' else "No recent middle."
        kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")]]
        await callback.message.edit_text(empty, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    # Build a list of up to 5 recent middle messages to view
    rows = []
    for idx, item in enumerate(reversed(LAST_MIDDLES[-5:]), start=1):
        first = (item.get('text') or '').splitlines()[0]
        if len(first) > 42:
            first = first[:39] + '…'
        rows.append([InlineKeyboardButton(text=f"#{idx} {first}", callback_data=f"show_middle_{len(LAST_MIDDLES)-idx}")])
    rows.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")])
    await callback.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@dp.callback_query(F.data.startswith("show_middle_"))
async def cb_show_middle(callback: types.CallbackQuery):
    await callback.answer()
    try:
        idx = int(callback.data.split('_', 2)[2])
    except Exception:
        idx = -1
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    if idx < 0 or idx >= len(LAST_MIDDLES):
        text = "Introuvable" if lang == 'fr' else "Not found"
        kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_middle")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    text = LAST_MIDDLES[idx].get('text') or ''
    kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_middle")]]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "last_goodev")
async def cb_last_goodev(callback: types.CallbackQuery):
    await callback.answer()
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    header = "💎 Good EV - récents" if lang == 'fr' else "💎 Good EV - recent"
    if not LAST_GOOD_EV:
        empty = "Aucun Good EV récent." if lang == 'fr' else "No recent Good EV."
        kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")]]
        await callback.message.edit_text(empty, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    # Build list
    rows = []
    for idx, item in enumerate(reversed(LAST_GOOD_EV[-5:]), start=1):
        first = (item.get('text') or '').splitlines()[0]
        if len(first) > 42:
            first = first[:39] + '…'
        rows.append([InlineKeyboardButton(text=f"#{idx} {first}", callback_data=f"show_goodev_{len(LAST_GOOD_EV)-idx}")])
    rows.append([InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_calls")])
    await callback.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@dp.callback_query(F.data.startswith("show_goodev_"))
async def cb_show_goodev(callback: types.CallbackQuery):
    await callback.answer()
    try:
        idx = int(callback.data.split('_', 2)[2])
    except Exception:
        idx = -1
    _, lang, _ = _get_user_prefs(callback.from_user.id)
    if idx < 0 or idx >= len(LAST_GOOD_EV):
        text = "Introuvable" if lang == 'fr' else "Not found"
        kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_goodev")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    text = LAST_GOOD_EV[idx].get('text') or ''
    kb = [[InlineKeyboardButton(text=("◀️ Retour" if lang=='fr' else "◀️ Back"), callback_data="last_goodev")]]
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "/backup")
async def backup_now_command(message: types.Message):
    """Admin command to trigger immediate database backup"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    
    await message.answer("🗄️ Starting manual backup now...")
    
    try:
        from bot.auto_backup import manual_backup_now
        await manual_backup_now(bot, int(ADMIN_CHAT_ID))
    except Exception as e:
        await message.answer(f"❌ Backup failed: {e}")


@dp.message(F.text == "/listevents")
async def list_events_command(message: types.Message):
    """Admin command to list live events from The Odds API"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    
    await message.answer("🔍 Récupération des événements en cours...")
    
    try:
        import requests
        from utils.odds_api_links import ODDS_API_KEY, ODDS_API_BASE
        
        # Liste des sports populaires
        sports_to_check = [
            'soccer_italy_serie_a',
            'soccer_france_ligue_one',
            'soccer_epl',
            'basketball_nba',
            'icehockey_nhl'
        ]
        
        events_found = []
        
        for sport in sports_to_check:
            url = f"{ODDS_API_BASE}/sports/{sport}/odds"
            params = {
                "apiKey": ODDS_API_KEY,
                "regions": "us,us2,eu",
                "markets": "h2h,totals",
                "oddsFormat": "american"
            }
            
            try:
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for event in data[:3]:  # Prendre les 3 premiers
                        events_found.append({
                            'sport': sport,
                            'id': event.get('id'),
                            'home': event.get('home_team'),
                            'away': event.get('away_team'),
                            'bookmakers': len(event.get('bookmakers', []))
                        })
            except Exception:
                continue
        
        if not events_found:
            await message.answer("❌ Aucun événement trouvé. L'API est peut-être limitée.")
            return
        
        msg = "📊 <b>Événements disponibles:</b>\n\n"
        for i, ev in enumerate(events_found[:5], 1):
            msg += f"{i}. <b>{ev['home']} vs {ev['away']}</b>\n"
            msg += f"   Sport: {ev['sport']}\n"
            msg += f"   ID: <code>{ev['id']}</code>\n"
            msg += f"   Bookmakers: {ev['bookmakers']}\n\n"
        
        msg += "\n💡 <b>Pour tester avec deep links:</b>\n"
        msg += "<code>/testcall EVENT_ID</code>\n"
        msg += "\nExemple:\n<code>/testcall " + (events_found[0]['id'] if events_found else 'abc123') + "</code>"
        
        await message.answer(msg, parse_mode='HTML')
        
    except Exception as e:
        await message.answer(f"❌ Erreur: {e}")


@dp.message(F.text.startswith("/testcall"))
async def test_call_command(message: types.Message):
    """Admin command to test sending a call with deep links"""
    if str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    
    # Parse event_id si fourni
    parts = message.text.split()
    event_id_api = parts[1] if len(parts) > 1 else None
    sport_key = parts[2] if len(parts) > 2 else 'soccer_italy_serie_a'
    
    # Test drop: Udinese vs Bologna - Team Total Corners
    test_drop = {
        'event_id': 'test_udinese_bologna_001',
        'event_id_api': event_id_api,  # Utiliser l'event_id fourni!
        'sport_key': sport_key,
        'match': 'Udinese Calcio vs Bologna FC 1909',
        'league': 'Italy - Serie A',
        'market': 'Team Total Corners',
        'arb_percentage': 9.41,
        'time': 'Live',
        'outcomes': [
            {
                'casino': 'Betsson',
                'outcome': 'Udinese Calcio Over 3',
                'odds': -143
            },
            {
                'casino': 'Coolbet',
                'outcome': 'Udinese Calcio Under 3',
                'odds': 215
            }
        ],
        'drop_event_id': 9999
    }
    
    if event_id_api:
        await message.answer(f"📤 Envoi du test call avec VRAIS deep links...\nEvent ID: {event_id_api}")
    else:
        await message.answer("📤 Envoi du test call (fallback URLs)...\n\n💡 Utilise /listevents pour voir les events avec deep links")
    
    try:
        # Envoyer en mode PREMIUM pour avoir tous les boutons
        await send_alert_to_user(message.from_user.id, TierLevel.PREMIUM, test_drop)
        
        if event_id_api:
            await message.answer(
                "✅ Test envoyé avec deep links!\n\n"
                "🔗 Les boutons casino devraient ouvrir directement les paris."
            )
        else:
            await message.answer(
                "✅ Test envoyé!\n\n"
                "⚠️ Sans event_id, les boutons pointent vers les homepages.\n"
                "Utilise: <code>/testcall EVENT_ID</code> pour tester les deep links",
                parse_mode='HTML'
            )
    except Exception as e:
        await message.answer(f"❌ Erreur: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ===== Startup =====

async def on_startup():
    """Initialize database on startup"""
    print("🚀 Initializing database...")
    init_db()
    print("✅ Database initialized")


async def runner():
    """Main runner - starts both FastAPI and Telegram bot"""
    print("✅ ArbitrageBot Canada - Starting...")
    
    # Initialize DB
    await on_startup()
    
    # Configure menu button and commands
    try:
        await setup_menu_button(bot)
        await setup_bot_commands(bot)
    except Exception:
        pass
    
    # Initialize daily confirmation scheduler
    try:
        daily_confirmation.init_daily_confirmation_scheduler(bot)
    except Exception as e:
        print(f"⚠️ Failed to initialize daily confirmation scheduler: {e}")
    
    # Initialize automatic backup system (sends .db files every 2 weeks)
    from bot.auto_backup import AutoBackupManager
    backup_manager = None
    try:
        admin_id = int(ADMIN_CHAT_ID)
        backup_manager = AutoBackupManager(bot, admin_id)
        print(f"✅ Auto-backup system initialized (admin: {admin_id})")
    except Exception as e:
        print(f"⚠️ Failed to initialize auto-backup system: {e}")
    
    # Initialize ML Call Logger (lightweight background worker for data collection)
    from utils.call_logger import get_call_logger
    from utils.safe_call_logger import get_safe_logger
    call_logger = None
    safe_logger = None
    try:
        # Start background worker
        call_logger = get_call_logger()
        await call_logger.start()
        
        # Initialize safe wrapper with admin alerts
        admin_id = int(ADMIN_CHAT_ID)
        safe_logger = get_safe_logger(bot, admin_id)
        
        print("✅ ML Call Logger initialized (background mode - no performance impact)")
        print("✅ Safe logger wrapper active (auto-alerts on errors)")
    except Exception as e:
        print(f"⚠️ Failed to initialize call logger: {e}")
        print("ℹ️ Bot will continue normally without ML logging")
    
    async def serve():
        port = int(os.getenv("PORT") or os.getenv("RISK0_PORT") or "8080")
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    # Run FastAPI, Telegram bot, Auto-backup system, and Middle questionnaire loop
    tasks = [
        serve(),
        dp.start_polling(bot),
    ]
    
    # Add backup loop if initialized
    if backup_manager:
        tasks.append(backup_manager.backup_loop())
    
    # Add Intelligent questionnaire loop (checks every 30 minutes for finished matches)
    # Also checks at midnight for bets without known match dates
    from bot.intelligent_questionnaire import intelligent_questionnaire_loop
    tasks.append(intelligent_questionnaire_loop(bot))
    
    # Add Book Health Monitor cron jobs
    from bot.book_health_cron import schedule_book_health_tasks
    tasks.append(schedule_book_health_tasks(bot))
    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(runner())
