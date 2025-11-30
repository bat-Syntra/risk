"""
Professional Dashboard Stats System
Complete redesign of stats display with advanced metrics and beautiful formatting
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import Session
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from database import SessionLocal
from models.user import User, TierLevel
from models.bet import DailyStats, UserBet
from models.drop_event import DropEvent

import logging
logger = logging.getLogger(__name__)


def calculate_win_rate(bets: List[UserBet]) -> Tuple[float, int, int]:
    """
    Calculate win rate and win/loss counts
    
    IMPORTANT: Arbitrage bets are ALWAYS wins (guaranteed profit)
    Middle/Good EV bets require actual settlement
    """
    if not bets:
        return 0.0, 0, 0
    
    wins = 0
    losses = 0
    pending = 0
    
    for b in bets:
        # ARBITRAGE = WIN automatiquement (profit garanti!)
        if b.bet_type == 'arbitrage':
            wins += 1
        # MIDDLE / GOOD EV = attend le résultat
        elif b.bet_type in ['middle', 'good_ev']:
            if b.actual_profit is not None:
                if b.actual_profit > 0:
                    wins += 1
                elif b.actual_profit < 0:
                    losses += 1
                # actual_profit == 0 = push, pas compté
            else:
                # Pas encore settled
                pending += 1
        else:
            # Autres types - use actual_profit
            if b.actual_profit is not None:
                if b.actual_profit > 0:
                    wins += 1
                else:
                    losses += 1
            else:
                pending += 1
    
    # Win rate basé sur bets settled
    settled = wins + losses
    win_rate = (wins / settled * 100) if settled > 0 else 0.0
    return win_rate, wins, losses


def calculate_streak(bets: List[UserBet]) -> str:
    """
    Calculate current streak (wins/losses)
    
    ARBITRAGE = always win
    MIDDLE/EV = check actual_profit
    """
    if not bets:
        return "0"
    
    # Sort bets by date descending
    sorted_bets = sorted(bets, key=lambda x: x.bet_date, reverse=True)
    
    streak_type = None
    streak_count = 0
    
    for bet in sorted_bets:
        # Determine if win/loss
        is_win = None
        
        if bet.bet_type == 'arbitrage':
            # Arbitrage = always win
            is_win = True
        elif bet.bet_type in ['middle', 'good_ev']:
            # Middle/EV = check actual_profit
            if bet.actual_profit is not None:
                is_win = bet.actual_profit > 0
            else:
                # Skip pending bets
                continue
        else:
            # Other types
            if bet.actual_profit is not None:
                is_win = bet.actual_profit > 0
            else:
                continue
        
        if is_win is None:
            continue
            
        if streak_type is None:
            streak_type = 'W' if is_win else 'L'
            streak_count = 1
        elif (is_win and streak_type == 'W') or (not is_win and streak_type == 'L'):
            streak_count += 1
        else:
            break
    
    if streak_count == 0:
        return "0"
    
    emoji = "🔥" if streak_type == 'W' else "❄️"
    return f"{streak_count}{streak_type} {emoji}"


def format_quick_overview(total_profit: float, roi: float, win_rate: float, streak: str, lang: str) -> str:
    """Format the quick overview section"""
    if lang == 'fr':
        text = (
            "🎯 <b>APERÇU RAPIDE</b>\n"
            f"• Profit total: <b>${total_profit:+.2f}</b>\n"
            f"• ROI global: <b>{roi:.1f}%</b>\n"
            f"• Win rate: <b>{win_rate:.0f}%</b> | Streak: <b>{streak}</b>"
        )
    else:
        text = (
            "🎯 <b>QUICK OVERVIEW</b>\n"
            f"• Total profit: <b>${total_profit:+.2f}</b>\n"
            f"• Global ROI: <b>{roi:.1f}%</b>\n"
            f"• Win rate: <b>{win_rate:.0f}%</b> | Streak: <b>{streak}</b>"
        )
    return text


def format_period_stats(title: str, bets: int, staked: float, profit: float, roi: float, extra: str = "") -> str:
    """Format stats for a time period"""
    profit_emoji = "✅" if profit >= 0 else "❌"
    
    lines = [
        f"{title}",
        f"• Bets: {bets} | Misé: ${staked:.2f} | Profit: ${profit:+.2f} {profit_emoji}",
        f"• ROI: {roi:.1f}%",
    ]
    if extra:
        lines.append(f"• {extra}")
    return "\n".join(lines)


def format_bet_type_card(type_name: str, emoji: str, bets: int, wins: int, losses: int, 
                        win_rate: float, profit: float, roi: float, avg_stake: float,
                        lang: str, is_arbitrage: bool = False) -> str:
    """
    Format a bet type statistics card
    
    is_arbitrage: If True, show pending instead of losses (arbs can't lose!)
    """
    if is_arbitrage:
        # Arbitrages don't have losses, only wins
        pending = bets - wins  # Any not marked as win are pending
        lines = [
            f"{emoji} <b>{type_name}</b>",
            f"• Bets: {bets} | ✅ {wins} | ⏳ {pending} | WR: {win_rate:.0f}%",
            f"• Profit: ${profit:+.2f} | ROI: {roi:.1f}%",
        ]
    else:
        lines = [
            f"{emoji} <b>{type_name}</b>",
            f"• Bets: {bets} | ✅ {wins} | ❌ {losses} | WR: {win_rate:.0f}%",
            f"• Profit: ${profit:+.2f} | ROI: {roi:.1f}%",
        ]
    
    if bets > 0:
        label = "Mise moy." if lang == 'fr' else "Avg stake"
        lines.append(f"• {label}: ${avg_stake:.2f}")
    return "\n".join(lines)


def format_bet_history_card(bet: UserBet, db: Session, lang: str) -> str:
    """
    Format a single bet history card
    
    IMPORTANT: Arbitrage bets are ALWAYS wins!
    """
    # Get match info if available
    match_info = ""
    if bet.drop_event_id:
        drop = db.query(DropEvent).filter(DropEvent.id == bet.drop_event_id).first()
        if drop:
            match_info = drop.match or "N/A"
    
    bet_date_str = bet.bet_date.strftime('%Y-%m-%d • %I:%M %p')
    profit_val = bet.actual_profit if bet.actual_profit is not None else bet.expected_profit
    roi = (profit_val / bet.total_stake * 100) if bet.total_stake > 0 else 0
    
    # Determine result emoji based on bet type
    if bet.bet_type == 'arbitrage':
        # Arbitrages are ALWAYS wins!
        result_emoji = "✅"
    elif bet.bet_type in ['middle', 'good_ev']:
        # Middle/EV bets depend on actual result
        if bet.actual_profit is not None:
            result_emoji = "✅" if bet.actual_profit > 0 else "❌" if bet.actual_profit < 0 else "⏳"
        else:
            result_emoji = "⏳"  # Pending
    else:
        # Other types
        result_emoji = "✅" if profit_val > 0 else "❌" if profit_val < 0 else "⏳"
    
    # Determine bet type emoji
    type_emoji = {
        'arbitrage': '⚖️',
        'good_ev': '💎',
        'middle': '🎯'
    }.get(bet.bet_type, '💰')
    
    type_name = {
        'arbitrage': 'Arbitrage',
        'good_ev': 'Good +EV',
        'middle': 'Middle Bet'
    }.get(bet.bet_type, 'Bet')
    
    base = (
        f"{result_emoji} {bet_date_str} – {type_emoji} {type_name} – "
        f"${bet.total_stake:.2f} → ${profit_val:+.2f} ({roi:.1f}% ROI)"
    )
    if match_info:
        short = match_info if len(match_info) <= 40 else match_info[:37] + "..."
        return f"{base} – {short}"
    return base


async def show_dashboard_stats(callback: types.CallbackQuery, filter_month: str = None):
    """
    Show the redesigned professional dashboard
    
    Args:
        callback: Telegram callback query
        filter_month: Optional month filter in format "YYYY_MM" (e.g., "2025_09" for September 2025)
                     If None, shows all-time stats
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Date calculations
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        # Parse filter_month if provided
        if filter_month:
            year, month = map(int, filter_month.split('_'))
            filter_month_start = date(year, month, 1)
            # Last day of month
            if month == 12:
                filter_month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                filter_month_end = date(year, month + 1, 1) - timedelta(days=1)
            filter_label = filter_month_start.strftime("%B %Y").upper()
        else:
            filter_month_start = None
            filter_month_end = None
            filter_label = "ALL TIME" if lang == 'en' else "TOUT TEMPS"
        
        # month_start for current month stats (used in Today/Week/Month sections)
        month_start = today.replace(day=1)
        
        # Get user bets for calculations (filtered if month selected)
        bets_query = db.query(UserBet).filter(UserBet.user_id == user_id)
        if filter_month:
            bets_query = bets_query.filter(
                UserBet.bet_date >= filter_month_start,
                UserBet.bet_date <= filter_month_end
            )
        
        all_user_bets = bets_query.all()
        recent_bets = bets_query.order_by(UserBet.bet_date.desc()).limit(3).all()
        
        # Calculate overall metrics
        total_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in all_user_bets)
        total_staked = sum(b.total_stake for b in all_user_bets)
        overall_roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        
        win_rate, wins, losses = calculate_win_rate(all_user_bets)
        current_streak = calculate_streak(all_user_bets)
        
        # Build dashboard header (compact style)
        if lang == 'fr':
            header = f"📊 <b>VOS STATISTIQUES - {filter_label}</b>\n\n"
        else:
            header = f"📊 <b>YOUR STATISTICS - {filter_label}</b>\n\n"
        
        # Quick overview
        overview = format_quick_overview(total_profit, overall_roi, win_rate, current_streak, lang)
        
        # Today stats
        today_stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today
        ).first()
        
        today_bets = today_stats.total_bets if today_stats else 0
        today_staked = today_stats.total_staked if today_stats else 0.0
        today_profit = today_stats.total_profit if today_stats else 0.0
        today_roi = (today_profit / today_staked * 100) if today_staked > 0 else 0
        
        today_section = format_period_stats(
            "📅 AUJOURD'HUI" if lang == 'fr' else "📅 TODAY",
            today_bets, today_staked, today_profit, today_roi
        )
        
        # Week stats
        week_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= week_ago
        ).first()
        
        week_bets = int(week_stats[0] or 0)
        week_staked = float(week_stats[1] or 0.0)
        week_profit = float(week_stats[2] or 0.0)
        week_roi = (week_profit / week_staked * 100) if week_staked > 0 else 0
        
        # Find best day
        best_day = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= week_ago
        ).order_by(DailyStats.total_profit.desc()).first()
        
        best_day_str = ""
        if best_day:
            best_day_str = f"{'Meilleur' if lang == 'fr' else 'Best'}: {best_day.date.strftime('%b %d')} 📈"
        
        week_section = format_period_stats(
            "📊 7 DERNIERS JOURS" if lang == 'fr' else "📊 LAST 7 DAYS",
            week_bets, week_staked, week_profit, week_roi, best_day_str
        )
        
        # Month stats
        month_stats = db.query(
            func.sum(DailyStats.total_bets),
            func.sum(DailyStats.total_staked),
            func.sum(DailyStats.total_profit)
        ).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= month_start
        ).first()
        
        month_bets = int(month_stats[0] or 0)
        month_staked = float(month_stats[1] or 0.0)
        month_profit = float(month_stats[2] or 0.0)
        month_roi = (month_profit / month_staked * 100) if month_staked > 0 else 0
        
        # Count active days
        active_days = db.query(func.count(DailyStats.date)).filter(
            DailyStats.user_id == user_id,
            DailyStats.date >= month_start
        ).scalar() or 0
        
        days_in_month = today.day
        active_str = f"{'Jours actifs' if lang == 'fr' else 'Active days'}: {active_days}/{days_in_month} 📅"
        
        month_section = format_period_stats(
            "📆 CE MOIS" if lang == 'fr' else "📆 THIS MONTH",
            month_bets, month_staked, month_profit, month_roi, active_str
        )
        
        # Stats by type
        arb_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit)),
            func.sum(UserBet.total_stake)
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'arbitrage'
        ).first()
        
        arb_bets = int(arb_stats[0] or 0)
        arb_profit = float(arb_stats[1] or 0.0)
        arb_staked = float(arb_stats[2] or 0.0)
        arb_roi = (arb_profit / arb_staked * 100) if arb_staked > 0 else 0
        arb_avg_stake = (arb_staked / arb_bets) if arb_bets > 0 else 0
        
        # ARBITRAGE = tous les bets sont des WINS (profit garanti!)
        arb_wins = arb_bets  # Tous les arbitrages sont des wins!
        arb_losses = 0  # Arbitrage ne peut pas perdre
        arb_pending = 0  # On pourrait ajouter un compteur pour les pending si nécessaire
        arb_wr = 100.0 if arb_bets > 0 else 0
        
        arb_card = format_bet_type_card(
            "ARBITRAGE", "⚖️", arb_bets, arb_wins, arb_losses,
            arb_wr, arb_profit, arb_roi, arb_avg_stake, lang, is_arbitrage=True
        )
        
        # Good EV stats
        ev_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit)),
            func.sum(UserBet.total_stake)
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev'
        ).first()
        
        ev_bets = int(ev_stats[0] or 0)
        ev_profit = float(ev_stats[1] or 0.0)
        ev_staked = float(ev_stats[2] or 0.0)
        ev_roi = (ev_profit / ev_staked * 100) if ev_staked > 0 else 0
        ev_avg_stake = (ev_staked / ev_bets) if ev_bets > 0 else 0
        
        # Good EV: Count wins and losses from settled bets only
        ev_wins = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev',
            UserBet.actual_profit != None,
            UserBet.actual_profit > 0
        ).scalar() or 0
        
        ev_losses = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'good_ev',
            UserBet.actual_profit != None,
            UserBet.actual_profit < 0
        ).scalar() or 0
        
        ev_settled = ev_wins + ev_losses
        ev_wr = (ev_wins / ev_settled * 100) if ev_settled > 0 else 0
        
        ev_card = format_bet_type_card(
            "GOOD +EV", "💎", ev_bets, ev_wins, ev_losses,
            ev_wr, ev_profit, ev_roi, ev_avg_stake, lang
        )
        
        # Middle stats
        middle_stats = db.query(
            func.count(UserBet.id),
            func.sum(case((UserBet.actual_profit != None, UserBet.actual_profit), else_=UserBet.expected_profit)),
            func.sum(UserBet.total_stake)
        ).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle'
        ).first()
        
        middle_bets = int(middle_stats[0] or 0)
        middle_profit = float(middle_stats[1] or 0.0)
        middle_staked = float(middle_stats[2] or 0.0)
        middle_roi = (middle_profit / middle_staked * 100) if middle_staked > 0 else 0
        middle_avg_stake = (middle_staked / middle_bets) if middle_bets > 0 else 0
        
        # Middle bets: Count wins (actual_profit > 0) and losses (actual_profit < 0)
        # Anything with actual_profit = NULL is pending
        middle_wins = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle',
            UserBet.actual_profit != None,
            UserBet.actual_profit > 0
        ).scalar() or 0
        
        middle_losses = db.query(func.count(UserBet.id)).filter(
            UserBet.user_id == user_id,
            UserBet.bet_type == 'middle',
            UserBet.actual_profit != None,
            UserBet.actual_profit < 0
        ).scalar() or 0
        
        middle_settled = middle_wins + middle_losses
        middle_wr = (middle_wins / middle_settled * 100) if middle_settled > 0 else 0
        
        middle_card = format_bet_type_card(
            "MIDDLE BETS", "🎯", middle_bets, middle_wins, middle_losses,
            middle_wr, middle_profit, middle_roi, middle_avg_stake, lang
        )
        
        # Bet history - Show last 10 bets (removed useless Load More)
        history_section = ""
        if all_user_bets:
            history_title = "📋 <b>HISTORIQUE DES BETS</b>" if lang == 'fr' else "📋 <b>BET HISTORY</b>"
            history_section = f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{history_title}\n\n"
            
            # Show last 10 bets
            last_10_bets = db.query(UserBet).filter(
                UserBet.user_id == user_id
            ).order_by(UserBet.bet_date.desc()).limit(10).all()
            
            for bet in last_10_bets:
                history_section += format_bet_history_card(bet, db, lang) + "\n"
        
        # Build complete message (removed STATS BY BET TYPE section)
        stats_text = (
            f"{header}"
            f"{overview}\n\n"
            f"{today_section}\n\n"
            f"{week_section}\n\n"
            f"{month_section}\n"
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Navigation buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Stats Complètes" if lang == 'fr' else "📊 Full Stats",
                    callback_data=f"view_full_stats_{filter_month}" if filter_month else "view_full_stats"
                ),
                InlineKeyboardButton(
                    text="📈 Graphiques" if lang == 'fr' else "📈 Charts",
                    callback_data=f"view_charts_{filter_month}" if filter_month else "view_charts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Mois" if lang == 'fr' else "📅 Month",
                    callback_data="month_filter"
                ),
                InlineKeyboardButton(
                    text="🗓️ Reset" if filter_month else "🗓️ All Time",
                    callback_data="my_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Mes Bets" if lang == 'fr' else "📋 My Bets",
                    callback_data="my_bets"
                ),
                InlineKeyboardButton(
                    text="➕ Nouveau Bet" if lang == 'fr' else "➕ New Bet",
                    callback_data="add_bet"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏥 Book Health Monitor",
                    callback_data="book_health_dashboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Actualiser" if lang == 'fr' else "🔄 Refresh",
                    callback_data=f"my_stats_{filter_month}" if filter_month else "my_stats"
                ),
                InlineKeyboardButton(
                    text="⚙️ Menu" if lang == 'fr' else "⚙️ Menu",
                    callback_data="main_menu"
                )
            ]
        ]
        
        await callback.message.edit_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_dashboard_stats: {e}")
        await callback.answer("❌ Error loading dashboard", show_alert=True)
    finally:
        db.close()


async def show_complete_stats(callback: types.CallbackQuery):
    """Show complete stats - Level 1: Compact overview"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get all user bets
        all_bets = db.query(UserBet).filter(UserBet.user_id == user_id).all()
        
        # Calculate global metrics
        total_bets = len(all_bets)
        total_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in all_bets)
        total_staked = sum(b.total_stake for b in all_bets)
        overall_roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        
        win_rate, wins, losses = calculate_win_rate(all_bets)
        current_streak = calculate_streak(all_bets)
        
        # Period stats
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_start = today.replace(day=1)
        
        periods = {
            "Aujourd'hui" if lang == 'fr' else "Today": today,
            "7 jours" if lang == 'fr' else "7 days": week_ago,
            "30 jours" if lang == 'fr' else "30 days": month_start,
            "All-time": None
        }
        
        period_stats = {}
        for period_name, period_date in periods.items():
            if period_date:
                period_bets = [b for b in all_bets if b.bet_date >= period_date]
            else:
                period_bets = all_bets
            
            p_count = len(period_bets)
            p_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in period_bets)
            p_staked = sum(b.total_stake for b in period_bets)
            p_roi = (p_profit / p_staked * 100) if p_staked > 0 else 0
            p_wr, p_wins, p_losses = calculate_win_rate(period_bets)
            
            period_stats[period_name] = {
                'bets': p_count,
                'wr': f"{p_wr:.0f}%",
                'profit': p_profit,
                'roi': p_roi
            }
        
        # Category stats
        cat_stats = []
        for cat_type, cat_emoji, cat_name in [('arbitrage', '⚖️', 'Arbitrage'), ('good_ev', '💎', 'Good +EV'), ('middle', '🎯', 'Middle')]:
            cat_bets = [b for b in all_bets if b.bet_type == cat_type]
            c_count = len(cat_bets)
            c_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in cat_bets)
            c_wr, _, _ = calculate_win_rate(cat_bets)
            cat_stats.append((cat_emoji, cat_name, {
                'bets': c_count,
                'wr': f"{c_wr:.0f}%" if c_count > 0 else 'N/A',
                'profit': c_profit
            }))
        
        # Build message
        if lang == 'fr':
            text = (
                "📊 <b>STATISTIQUES COMPLÈTES</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🎯 <b>RÉSUMÉ GLOBAL</b>\n"
                f"• Total Bets: {total_bets}\n"
                f"• Win Rate: {win_rate:.0f}% ({wins}-{losses})\n"
                f"• Profit Total: ${total_profit:+.2f}\n"
                f"• ROI Moyen: {overall_roi:.1f}%\n"
                f"• Streak: {current_streak}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📅 <b>PAR PÉRIODE</b>\n\n"
            )
        else:
            text = (
                "📊 <b>COMPLETE STATISTICS</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🎯 <b>GLOBAL SUMMARY</b>\n"
                f"• Total Bets: {total_bets}\n"
                f"• Win Rate: {win_rate:.0f}% ({wins}-{losses})\n"
                f"• Total Profit: ${total_profit:+.2f}\n"
                f"• Avg ROI: {overall_roi:.1f}%\n"
                f"• Streak: {current_streak}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📅 <b>BY PERIOD</b>\n\n"
            )
        
        # Period table
        for period_name, pdata in period_stats.items():
            text += f"{period_name:<14} {pdata['bets']:>2} bets | {pdata['wr']:>4} | ${pdata['profit']:>+7.2f} | {pdata['roi']:>4.1f}%\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if lang == 'fr':
            text += "🎲 <b>PAR CATÉGORIE</b>\n\n"
        else:
            text += "🎲 <b>BY CATEGORY</b>\n\n"
        
        for cat_emoji, cat_name, cdata in cat_stats:
            text += f"{cat_emoji} {cat_name:<12} {cdata['bets']:>2} bets | {cdata['wr']:>4} | ${cdata['profit']:>+7.2f}\n"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔬 Stats Avancées" if lang == 'fr' else "🔬 Advanced Stats",
                    callback_data="advanced_stats_menu"
                ),
                InlineKeyboardButton(
                    text="📊 Graphiques" if lang == 'fr' else "📊 Charts",
                    callback_data="view_charts"
                )
            ],
            [InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="my_stats"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_complete_stats: {e}")
        await callback.answer("❌ Error loading stats", show_alert=True)
    finally:
        db.close()


async def show_advanced_stats_menu(callback: types.CallbackQuery):
    """Show advanced stats menu - Level 2"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        if lang == 'fr':
            text = (
                "🔬 <b>STATISTIQUES AVANCÉES</b>\n\n"
                "Choisis une catégorie d'analyse:\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            text = (
                "🔬 <b>ADVANCED STATISTICS</b>\n\n"
                "Choose an analysis category:\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="📊 Performance Détaillée" if lang == 'fr' else "📊 Detailed Performance",
                callback_data="adv_performance"
            )],
            [InlineKeyboardButton(
                text="🏢 Analyse par Bookmaker" if lang == 'fr' else "🏢 Bookmaker Analysis",
                callback_data="adv_bookmakers"
            )],
            [InlineKeyboardButton(
                text="🏀 Analyse par Sport" if lang == 'fr' else "🏀 Sport Analysis",
                callback_data="adv_sports"
            )],
            [InlineKeyboardButton(
                text="🏥 Book Health Monitor" if lang == 'fr' else "🏥 Book Health Monitor",
                callback_data="book_health_dashboard"
            )],
            [InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="view_full_stats"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_advanced_stats_menu: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


async def show_advanced_performance(callback: types.CallbackQuery):
    """Show detailed performance analysis"""
    await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        all_bets = db.query(UserBet).filter(UserBet.user_id == user_id).all()
        
        total_bets = len(all_bets)
        total_profit = sum(b.actual_profit if b.actual_profit is not None else b.expected_profit for b in all_bets)
        total_staked = sum(b.total_stake for b in all_bets)
        overall_roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        
        win_rate, wins, losses = calculate_win_rate(all_bets)
        avg_profit = total_profit / total_bets if total_bets > 0 else 0
        avg_stake = total_staked / total_bets if total_bets > 0 else 0
        
        # Best/worst bets
        profits = [b.actual_profit if b.actual_profit is not None else b.expected_profit for b in all_bets]
        best_bet = max(profits) if profits else 0
        worst_bet = min(profits) if profits else 0
        
        if lang == 'fr':
            text = (
                "📊 <b>PERFORMANCE DÉTAILLÉE</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📅 <b>ALL-TIME</b>\n\n"
                "<b>Performance Globale:</b>\n"
                f"• Total Bets: {total_bets}\n"
                f"• Wins: {wins} ✅ | Losses: {losses} ❌\n"
                f"• Win Rate: {win_rate:.1f}%\n"
                f"• Profit Total: ${total_profit:+.2f}\n"
                f"• ROI Global: {overall_roi:.1f}%\n"
                f"• Montant Misé: ${total_staked:.2f}\n\n"
                "<b>Moyennes:</b>\n"
                f"• Profit Moyen/Bet: ${avg_profit:+.2f}\n"
                f"• Stake Moyen/Bet: ${avg_stake:.2f}\n"
                f"• ROI Moyen: {overall_roi:.1f}%\n\n"
                "<b>Records:</b>\n"
                f"• Meilleur Bet: ${best_bet:+.2f}\n"
                f"• Pire Bet: ${worst_bet:+.2f}\n"
            )
        else:
            text = (
                "📊 <b>DETAILED PERFORMANCE</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📅 <b>ALL-TIME</b>\n\n"
                "<b>Global Performance:</b>\n"
                f"• Total Bets: {total_bets}\n"
                f"• Wins: {wins} ✅ | Losses: {losses} ❌\n"
                f"• Win Rate: {win_rate:.1f}%\n"
                f"• Total Profit: ${total_profit:+.2f}\n"
                f"• Global ROI: {overall_roi:.1f}%\n"
                f"• Total Staked: ${total_staked:.2f}\n\n"
                "<b>Averages:</b>\n"
                f"• Avg Profit/Bet: ${avg_profit:+.2f}\n"
                f"• Avg Stake/Bet: ${avg_stake:.2f}\n"
                f"• Avg ROI: {overall_roi:.1f}%\n\n"
                "<b>Records:</b>\n"
                f"• Best Bet: ${best_bet:+.2f}\n"
                f"• Worst Bet: ${worst_bet:+.2f}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton(
                text="◀️ Menu Avancé" if lang == 'fr' else "◀️ Advanced Menu",
                callback_data="advanced_stats_menu"
            )]
        ]
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in show_advanced_performance: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()
