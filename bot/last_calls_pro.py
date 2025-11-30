"""
Last Calls Pro - Enhanced with pagination, sorting, and casino filters
"""
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from datetime import date, timedelta
import json

from database import SessionLocal
from models.user import User
from models.drop_event import DropEvent
from sqlalchemy import desc

import logging
logger = logging.getLogger(__name__)

router = Router()

# Cache for filters per user
user_filters = {}  # {user_id: {'sort': 'desc', 'casinos': ['all'], 'page': 1}}


@router.callback_query(F.data == "noop")
async def noop_handler(callback: types.CallbackQuery):
    """No-op callback for display-only buttons"""
    await callback.answer()


def get_user_filters(user_id: int, category: str):
    """Get current filters for user and category"""
    key = f"{user_id}_{category}"
    if key not in user_filters:
        user_filters[key] = {
            'sort': 'time',  # 'time' = latest calls (default), 'desc' = highest %, 'asc' = lowest %
            'casinos': ['all'],
            'sport': 'all',  # 'all', 'basketball', 'soccer', 'tennis', 'hockey', 'football', 'baseball', 'mma'
            'page': 1,
            'days_before': 0,  # 0 = today, 1 = yesterday, etc.
            'use_my_settings': True,  # True = filter by user settings (default), False = show all
            'match_today_only': False  # True = show only calls where match starts TODAY (regardless of call creation date)
        }
    return user_filters[key]


def set_user_filters(user_id: int, category: str, **kwargs):
    """Update filters for user and category"""
    key = f"{user_id}_{category}"
    if key not in user_filters:
        user_filters[key] = {
            'sort': 'time',  # Default: most recent first
            'casinos': ['all'],
            'page': 1,
            'days_before': 0
        }
    user_filters[key].update(kwargs)


@router.callback_query(F.data.startswith("lastcalls_toggle_settings_"))
async def toggle_settings_filter(callback: types.CallbackQuery):
    """Toggle between My Settings filter and All Calls
    
    Expected callback.data format: lastcalls_toggle_settings_{category}
    where category is one of: arbitrage, middle, goodev.
    """
    await callback.answer()  # Answer immediately to avoid timeout
    
    parts = callback.data.split('_')
    # parts[0] = 'lastcalls'
    # parts[1] = 'toggle'
    # parts[2] = 'settings'
    # parts[3] = category
    if len(parts) < 4:
        return
    
    category = parts[3]
    user_id = callback.from_user.id
    
    # Toggle use_my_settings
    filters = get_user_filters(user_id, category)
    current = filters.get('use_my_settings', True)
    set_user_filters(user_id, category, use_my_settings=not current, page=1)
    
    # Manually trigger the page refresh by modifying parts and calling directly
    # We use the original callback but change the parsed data
    callback._data_backup = callback.data  # Backup original
    
    # Call show_last_calls with page 1 directly (skip the answer since we already did it)
    await _show_last_calls_internal(callback, category, 1, skip_answer=True)


def extract_casinos_from_drop(drop: DropEvent):
    """Extract casino names from drop payload"""
    casinos = []
    if drop.payload:
        # Try to extract from payload
        if isinstance(drop.payload, dict):
            # Check for 'outcomes' array (standard format)
            if 'outcomes' in drop.payload:
                for outcome in drop.payload.get('outcomes', []):
                    if 'casino' in outcome:
                        casinos.append(outcome['casino'])
            # Check different possible structures
            elif 'legs' in drop.payload:
                for leg in drop.payload.get('legs', []):
                    if 'casino' in leg:
                        casinos.append(leg['casino'])
            elif 'side_a' in drop.payload:
                if 'casino' in drop.payload['side_a']:
                    casinos.append(drop.payload['side_a']['casino'])
                if 'casino' in drop.payload.get('side_b', {}):
                    casinos.append(drop.payload['side_b']['casino'])
    return list(set(casinos)) if casinos else ['Unknown']


async def _show_last_calls_internal(callback: types.CallbackQuery, category: str, page: int, skip_answer: bool = False):
    """Internal function to show last calls - shared logic"""
    if not skip_answer:
        await callback.answer()
    
    user_id = callback.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get filters
        filters = get_user_filters(user_id, category)
        filters['page'] = page
        
        # Map category to bet_type
        category_to_type = {
            'arbitrage': 'arbitrage',
            'middle': 'middle',
            'goodev': 'good_ev'
        }
        bet_type = category_to_type.get(category, 'arbitrage')
        
        # Get drops filtered by bet_type
        match_today_only = filters.get('match_today_only', False)
        
        if match_today_only:
            # MATCH TODAY MODE: Get calls from last 5 days but filter by match date later
            days_back = 5  # Look back 5 days
            start_date = date.today() - timedelta(days=days_back)
            
            query = db.query(DropEvent).filter(
                DropEvent.received_at >= start_date,
                DropEvent.bet_type == bet_type  # Filter by category!
            )
        else:
            # NORMAL MODE: Get drops from specific day
            days_before = filters.get('days_before', 0)
            target_date = date.today() - timedelta(days=days_before)
            next_date = target_date + timedelta(days=1)
            
            query = db.query(DropEvent).filter(
                DropEvent.received_at >= target_date,
                DropEvent.received_at < next_date,
                DropEvent.bet_type == bet_type  # Filter by category!
            )
        
        # Apply sorting
        if filters['sort'] == 'desc':
            # Highest % first
            query = query.order_by(desc(DropEvent.arb_percentage))
        elif filters['sort'] == 'asc':
            # Lowest % first
            query = query.order_by(DropEvent.arb_percentage)
        else:
            # 'time' = latest calls first (most recent received_at)
            query = query.order_by(desc(DropEvent.received_at))
        
        all_drops = query.all()
        
        # Filter by match date if "Match Today" mode is active
        if match_today_only:
            from datetime import datetime, timezone
            today_date = date.today()
            filtered_by_match_date = []
            
            for drop in all_drops:
                # Extract commence_time from payload
                if drop.payload and isinstance(drop.payload, dict):
                    commence_time_iso = drop.payload.get('commence_time')
                    if commence_time_iso:
                        try:
                            # Parse ISO timestamp and get date
                            dt = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
                            match_date = dt.date()
                            
                            # Only include if match is TODAY
                            if match_date == today_date:
                                filtered_by_match_date.append(drop)
                        except Exception as e:
                            logger.debug(f"Could not parse commence_time for drop {drop.id}: {e}")
                            continue
            
            all_drops = filtered_by_match_date
        
        # Apply sport filter if not 'all'
        sport_filter = filters.get('sport', 'all')
        if sport_filter != 'all':
            filtered_by_sport = []
            sport_keywords = {
                'basketball': ['nba', 'ncaa basketball', 'wnba', 'basketball'],
                'soccer': ['soccer', 'football', 'mls', 'premier league', 'la liga', 'serie a', 'bundesliga', 'ligue 1'],
                'tennis': ['tennis', 'atp', 'wta'],
                'hockey': ['nhl', 'hockey'],
                'football': ['nfl', 'ncaa football', 'american football'],
                'baseball': ['mlb', 'baseball'],
                'mma': ['ufc', 'mma', 'bellator']
            }
            
            keywords = sport_keywords.get(sport_filter, [])
            for drop in all_drops:
                # Check league field
                league = (drop.league or '').lower()
                # Also check payload for sport info
                sport_name = ''
                if drop.payload and isinstance(drop.payload, dict):
                    sport_name = (drop.payload.get('sport_key') or '').lower()
                
                # Match if any keyword is in league or sport_name
                if any(kw in league or kw in sport_name for kw in keywords):
                    filtered_by_sport.append(drop)
            
            all_drops = filtered_by_sport
        
        # Apply filters based on use_my_settings
        if filters.get('use_my_settings', True) and user:
            # USE MY SETTINGS: Filter by user's configured % and casinos
            filtered_drops = []
            for drop in all_drops:
                pct = drop.arb_percentage or 0
                
                # Get user's min/max % for this bet type
                if bet_type == 'arbitrage':
                    min_pct = user.min_arb_percent or 0.5
                    max_pct = user.max_arb_percent or 100.0
                elif bet_type == 'middle':
                    min_pct = user.min_middle_percent or 0.5
                    max_pct = user.max_middle_percent or 100.0
                elif bet_type == 'good_ev':
                    min_pct = user.min_good_ev_percent or 0.5
                    max_pct = user.max_good_ev_percent or 100.0
                else:
                    min_pct = 0.5
                    max_pct = 100.0
                
                # Check if % is in user's range
                if not (min_pct <= pct <= max_pct):
                    continue
                
                # Check if casinos match user's selected casinos
                if user.selected_casinos:
                    try:
                        user_selected = json.loads(user.selected_casinos)
                        if user_selected:  # Only filter if user has selected specific casinos
                            drop_casinos = extract_casinos_from_drop(drop)
                            if not any(c in user_selected for c in drop_casinos):
                                continue
                    except:
                        pass  # If JSON parsing fails, don't filter by casino
                
                filtered_drops.append(drop)
            
            all_drops = filtered_drops
        else:
            # ALL CALLS MODE: Use manual casino filter from buttons (if not 'all')
            if 'all' not in filters['casinos']:
                filtered_drops = []
                for drop in all_drops:
                    drop_casinos = extract_casinos_from_drop(drop)
                    if any(c in filters['casinos'] for c in drop_casinos):
                        filtered_drops.append(drop)
                all_drops = filtered_drops
        
        # Pagination: 10 per page
        per_page = 10
        total_drops = len(all_drops)
        total_pages = (total_drops + per_page - 1) // per_page
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_drops = all_drops[start_idx:end_idx]
        
        # Build message
        category_names = {
            'arbitrage': ('ARBITRAGE', '⚖️'),
            'middle': ('MIDDLE', '🎯'),
            'goodev': ('GOOD +EV', '💎')
        }
        cat_name, cat_emoji = category_names.get(category, ('CALLS', '📞'))
        
        # Describe current sort mode in header
        if filters['sort'] == 'time':
            sort_text = "⏱ Derniers calls" if lang == 'fr' else "⏱ Latest calls"
        elif filters['sort'] == 'desc':
            sort_text = "📉 Plus haut %" if lang == 'fr' else "📉 Highest %"
        else:  # asc
            sort_text = "📈 Plus bas %" if lang == 'fr' else "📈 Lowest %"
        casino_text = "🎰 Tous" if 'all' in filters['casinos'] else f"🎰 {len(filters['casinos'])} casino(s)"
        
        # Show filter status
        if filters.get('use_my_settings', True):
            filter_text = "🎯 My Settings" if lang == 'en' else "🎯 Mes Filtres"
        else:
            filter_text = "📊 All Calls" if lang == 'en' else "📊 Tous les Calls"
        
        # Date text
        if match_today_only:
            date_text = "🎮 Match Aujourd'hui" if lang == 'fr' else "🎮 Match Today"
        elif days_before == 0:
            date_text = "📅 Aujourd'hui" if lang == 'fr' else "📅 Today"
        elif days_before == 1:
            date_text = "📅 Hier" if lang == 'fr' else "📅 Yesterday"
        else:
            date_text = f"📅 Il y a {days_before} jours" if lang == 'fr' else f"📅 {days_before} days ago"
        
        if lang == 'fr':
            text = (
                f"{cat_emoji} <b>LAST CALLS - {cat_name}</b>\n\n"
                f"📄 Page {page}/{total_pages} ({total_drops} calls)\n"
                f"{date_text}\n"
                f"{filter_text} • {sort_text} • {casino_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
        else:
            text = (
                f"{cat_emoji} <b>LAST CALLS - {cat_name}</b>\n\n"
                f"📄 Page {page}/{total_pages} ({total_drops} calls)\n"
                f"{date_text}\n"
                f"{filter_text} • {sort_text} • {casino_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
        
        # Build keyboard with clickable calls
        keyboard = []
        
        if page_drops:
            text += "Clique sur un call pour voir les détails:\n\n" if lang == 'fr' else "Click on a call to view details:\n\n"
            
            for i, drop in enumerate(page_drops, start=start_idx + 1):
                pct = drop.arb_percentage or 0
                match = drop.match or "Unknown"
                
                # Truncate match if too long for button
                button_text = match
                if len(button_text) > 45:
                    button_text = button_text[:42] + "..."
                
                # Add clickable button for each call
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{i}. {pct:.2f}% • {button_text}",
                        callback_data=f"viewcall_{drop.id}"
                    )
                ])
        else:
            text += "Aucun call trouvé.\n\n" if lang == 'fr' else "No calls found.\n\n"
        
        # Pagination buttons
        if total_pages > 1:
            page_row = []
            if page > 1:
                page_row.append(InlineKeyboardButton(
                    text="◀️",
                    callback_data=f"lastcalls_{category}_page_{page - 1}"
                ))
            page_row.append(InlineKeyboardButton(
                text=f"{page}/{total_pages}",
                callback_data="noop"
            ))
            if page < total_pages:
                page_row.append(InlineKeyboardButton(
                    text="▶️",
                    callback_data=f"lastcalls_{category}_page_{page + 1}"
                ))
            keyboard.append(page_row)
        
        # Filter buttons (3 rows)
        # Row 1: My Settings toggle button (full width)
        if filters.get('use_my_settings', True):
            toggle_text = "📊 All Calls" if lang == 'en' else "📊 Tous les Calls"
        else:
            toggle_text = "🎯 My Settings" if lang == 'en' else "🎯 Mes Filtres"
        
        keyboard.append([
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"lastcalls_toggle_settings_{category}"
            )
        ])
        
        # Row 2: Sort, Sport, and Casinos
        # Get sport emoji
        sport_emojis = {
            'all': '🏅',
            'basketball': '🏀',
            'soccer': '⚽',
            'tennis': '🎾',
            'hockey': '🏒',
            'football': '🏈',
            'baseball': '⚾',
            'mma': '🥊'
        }
        current_sport = filters.get('sport', 'all')
        sport_emoji = sport_emojis.get(current_sport, '🏅')
        
        keyboard.append([
            InlineKeyboardButton(
                text="📊 Trier %" if lang == 'fr' else "📊 Sort %",
                callback_data=f"lastcalls_sort_{category}"
            ),
            InlineKeyboardButton(
                text=f"{sport_emoji} Sport",
                callback_data=f"lastcalls_sport_{category}"
            ),
            InlineKeyboardButton(
                text="🎰 Casinos" if lang == 'fr' else "🎰 Casinos",
                callback_data=f"lastcalls_casinos_{category}"
            )
        ])
        
        # Row 3: Match Today toggle and Days
        match_today_btn_text = "✅ Match Today" if match_today_only else "⬜ Match Today"
        if lang == 'fr':
            match_today_btn_text = "✅ Match Auj." if match_today_only else "⬜ Match Auj."
        
        keyboard.append([
            InlineKeyboardButton(
                text=match_today_btn_text,
                callback_data=f"lastcalls_toggle_matchtoday_{category}"
            ),
            InlineKeyboardButton(
                text="📅 Jours" if lang == 'fr' else "📅 Days",
                callback_data=f"lastcalls_days_{category}"
            )
        ])
        
        # Back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data="last_calls"
            )
        ])
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as edit_error:
            # Ignore "message is not modified" errors
            if "message is not modified" not in str(edit_error).lower():
                raise
        
    except Exception as e:
        logger.error(f"Error in show_last_calls_category: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.regexp(r"^lastcalls_(arbitrage|middle|goodev)_page_"))
async def show_last_calls_category(callback: types.CallbackQuery):
    """Show last calls for a category with pagination and filters.
    Expected format: lastcalls_{category}_page_{page}
    where category is one of: arbitrage, middle, goodev.
    """
    parts = callback.data.split('_')
    # parts[0] = 'lastcalls'
    # parts[1] = category (arbitrage|middle|goodev)
    # parts[2] = 'page'
    # parts[3] = page number
    if len(parts) < 4 or parts[2] != 'page':
        await callback.answer()
        return
    
    category = parts[1]
    
    # Parse page if present
    page = 1
    try:
        page = int(parts[3])
    except ValueError:
        page = 1
    
    # Call internal function
    await _show_last_calls_internal(callback, category, page, skip_answer=False)


@router.callback_query(F.data.startswith("lastcalls_sort_"))
async def toggle_sort(callback: types.CallbackQuery):
    """Toggle sort order for a category.

    Expected callback.data format: lastcalls_sort_{category}
    where category is one of: arbitrage, middle, goodev.
    """

    parts = callback.data.split('_')
    # parts[0] = 'lastcalls'
    # parts[1] = 'sort'
    # parts[2] = category
    if len(parts) < 3:
        await callback.answer()
        return

    category = parts[2]
    user_id = callback.from_user.id
    
    # Toggle sort: time -> desc -> asc -> time
    filters = get_user_filters(user_id, category)
    current = filters.get('sort', 'time')
    if current == 'time':
        new_sort = 'desc'
        sort_emoji = "📉"
        sort_text = "Plus haut %"
    elif current == 'desc':
        new_sort = 'asc'
        sort_emoji = "📈"
        sort_text = "Plus bas %"
    else:  # asc
        new_sort = 'time'
        sort_emoji = "⏱"
        sort_text = "Derniers calls"

    set_user_filters(user_id, category, sort=new_sort, page=1)  # Reset to page 1
    await callback.answer(f"{sort_emoji} {sort_text}")
    
    # Refresh display with proper callback data (matches show_last_calls_category regex)
    new_callback = type('obj', (object,), {
        'data': f'lastcalls_{category}_page_1',
        'message': callback.message,
        'from_user': callback.from_user,
        'answer': callback.answer,
    })()
    await show_last_calls_category(new_callback)


@router.callback_query(F.data.startswith("lastcalls_toggle_matchtoday_"))
async def toggle_match_today(callback: types.CallbackQuery):
    """Toggle Match Today filter - shows only calls where match starts TODAY (from last 5 days)"""
    await callback.answer()
    
    parts = callback.data.split('_')
    # lastcalls_toggle_matchtoday_{category}
    if len(parts) < 4:
        return
    
    category = parts[3]
    user_id = callback.from_user.id
    
    # Toggle match_today_only
    filters = get_user_filters(user_id, category)
    current = filters.get('match_today_only', False)
    set_user_filters(user_id, category, match_today_only=not current, page=1)
    
    # Refresh the page
    callback._data_backup = callback.data
    await _show_last_calls_internal(callback, category, 1, skip_answer=True)


@router.callback_query(F.data.startswith("lastcalls_days_"))
async def show_days_filter(callback: types.CallbackQuery):
    """Show days filter menu to select which day to view"""
    await callback.answer()
    
    category = callback.data.split('_')[2]
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        filters = get_user_filters(user_id, category)
        current_days = filters.get('days_before', 0)
        
        if lang == 'fr':
            text = "📅 <b>Sélectionne le jour</b>\n\nChoisis quel jour tu veux voir:"
        else:
            text = "📅 <b>Select Day</b>\n\nChoose which day to view:"
        
        # Build keyboard with day options
        keyboard = []
        
        # Days 0-6 (today to 6 days ago)
        day_options = [
            (0, "📅 Aujourd'hui" if lang == 'fr' else "📅 Today"),
            (1, "📅 Hier" if lang == 'fr' else "📅 Yesterday"),
            (2, f"📅 Il y a 2 jours" if lang == 'fr' else "📅 2 days ago"),
            (3, f"📅 Il y a 3 jours" if lang == 'fr' else "📅 3 days ago"),
            (4, f"📅 Il y a 4 jours" if lang == 'fr' else "📅 4 days ago"),
            (5, f"📅 Il y a 5 jours" if lang == 'fr' else "📅 5 days ago"),
            (6, f"📅 Il y a 6 jours" if lang == 'fr' else "📅 6 days ago"),
        ]
        
        for days, text_btn in day_options:
            # Add checkmark if currently selected
            if days == current_days:
                text_btn = f"✅ {text_btn}"
            keyboard.append([
                InlineKeyboardButton(
                    text=text_btn,
                    callback_data=f"lastcalls_setday_{category}_{days}"
                )
            ])
        
        # Back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"lastcalls_{category}_page_1"
            )
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("lastcalls_setday_"))
async def set_day_filter(callback: types.CallbackQuery):
    """Set the day filter"""
    parts = callback.data.split('_')
    # parts[0] = 'lastcalls'
    # parts[1] = 'setday'
    # parts[2] = category
    # parts[3] = days_before
    
    if len(parts) < 4:
        await callback.answer()
        return
    
    category = parts[2]
    days_before = int(parts[3])
    user_id = callback.from_user.id
    
    # Update filter
    set_user_filters(user_id, category, days_before=days_before, page=1)
    
    # Determine day text for answer
    if days_before == 0:
        day_text = "Aujourd'hui"
    elif days_before == 1:
        day_text = "Hier"
    else:
        day_text = f"Il y a {days_before} jours"
    
    await callback.answer(f"📅 {day_text}")
    
    # Refresh display
    new_callback = type('obj', (object,), {
        'data': f'lastcalls_{category}_page_1',
        'message': callback.message,
        'from_user': callback.from_user,
        'answer': callback.answer,
    })()
    await show_last_calls_category(new_callback)


@router.callback_query(F.data.startswith("lastcalls_sport_"))
async def show_sport_filter(callback: types.CallbackQuery):
    """Show sport filter menu"""
    await callback.answer()
    
    category = callback.data.split('_')[2]
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Get current selected sport
        filters = get_user_filters(user_id, category)
        selected_sport = filters.get('sport', 'all')
        
        if lang == 'fr':
            text = (
                f"🏅 <b>FILTRER PAR SPORT</b>\n\n"
                f"Sélectionne un sport à afficher:\n\n"
            )
        else:
            text = (
                f"🏅 <b>FILTER BY SPORT</b>\n\n"
                f"Select a sport to display:\n\n"
            )
        
        # Sport options
        sports = [
            ('all', '🏅', 'Tous les sports', 'All sports'),
            ('basketball', '🏀', 'Basketball (NBA, NCCA)', 'Basketball (NBA, NCAA)'),
            ('soccer', '⚽', 'Soccer', 'Soccer'),
            ('tennis', '🎾', 'Tennis', 'Tennis'),
            ('hockey', '🏒', 'Hockey (NHL)', 'Hockey (NHL)'),
            ('football', '🏈', 'Football (NFL)', 'Football (NFL)'),
            ('baseball', '⚾', 'Baseball (MLB)', 'Baseball (MLB)'),
            ('mma', '🥊', 'MMA (UFC)', 'MMA (UFC)')
        ]
        
        # Build keyboard
        keyboard = []
        for sport_key, emoji, name_fr, name_en in sports:
            checked = "✅" if sport_key == selected_sport else "⬜"
            sport_name = name_fr if lang == 'fr' else name_en
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{checked} {emoji} {sport_name}",
                    callback_data=f"lastcalls_selectsport_{category}_{sport_key}"
                )
            ])
        
        # Back button
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"lastcalls_{category}_page_1"
            )
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("lastcalls_selectsport_"))
async def select_sport_filter(callback: types.CallbackQuery):
    """Handle sport selection"""
    parts = callback.data.split('_')
    category = parts[2]
    sport = parts[3]
    
    user_id = callback.from_user.id
    
    # Update filter
    set_user_filters(user_id, category, sport=sport, page=1)
    
    # Sport names for feedback
    sport_names = {
        'all': ('Tous les sports', 'All sports'),
        'basketball': ('Basketball', 'Basketball'),
        'soccer': ('Soccer', 'Soccer'),
        'tennis': ('Tennis', 'Tennis'),
        'hockey': ('Hockey', 'Hockey'),
        'football': ('Football', 'Football'),
        'baseball': ('Baseball', 'Baseball'),
        'mma': ('MMA', 'MMA')
    }
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        sport_name_fr, sport_name_en = sport_names.get(sport, ('Sport', 'Sport'))
        sport_name = sport_name_fr if lang == 'fr' else sport_name_en
        
        await callback.answer(f"🏅 {sport_name}")
    finally:
        db.close()
    
    # Refresh display
    new_callback = type('obj', (object,), {
        'data': f'lastcalls_{category}_page_1',
        'message': callback.message,
        'from_user': callback.from_user,
        'answer': callback.answer,
    })()
    await show_last_calls_category(new_callback)


@router.callback_query(F.data.startswith("lastcalls_casinos_"))
async def show_casino_filter(callback: types.CallbackQuery):
    """Show casino filter menu"""
    await callback.answer()
    
    category = callback.data.split('_')[2]
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Map category to bet_type
        category_to_type = {
            'arbitrage': 'arbitrage',
            'middle': 'middle',
            'goodev': 'good_ev'
        }
        bet_type = category_to_type.get(category, 'arbitrage')
        
        # Get all unique casinos from today's drops for this category
        today = date.today()
        all_drops = db.query(DropEvent).filter(
            DropEvent.received_at >= today,
            DropEvent.bet_type == bet_type  # Filter by category!
        ).all()
        
        casinos_set = set()
        for drop in all_drops:
            drop_casinos = extract_casinos_from_drop(drop)
            casinos_set.update(drop_casinos)
        
        casinos_list = sorted(list(casinos_set))
        
        # Get current filters
        filters = get_user_filters(user_id, category)
        selected_casinos = filters['casinos']
        
        if lang == 'fr':
            text = (
                f"🎰 <b>FILTRER PAR CASINO</b>\n\n"
                f"Sélectionne les casinos à afficher:\n\n"
            )
        else:
            text = (
                f"🎰 <b>FILTER BY CASINO</b>\n\n"
                f"Select casinos to display:\n\n"
            )
        
        # Build keyboard with casino checkboxes
        keyboard = []
        
        # "All" button
        all_checked = "✅" if 'all' in selected_casinos else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{all_checked} Tous les casinos" if lang == 'fr' else f"{all_checked} All casinos",
                callback_data=f"lastcalls_togglecasino_{category}_all"
            )
        ])
        
        # Individual casinos (2 per row)
        for i in range(0, len(casinos_list), 2):
            row = []
            for j in range(2):
                if i + j < len(casinos_list):
                    casino = casinos_list[i + j]
                    checked = "✅" if casino in selected_casinos or 'all' in selected_casinos else "⬜"
                    row.append(InlineKeyboardButton(
                        text=f"{checked} {casino}",
                        callback_data=f"lastcalls_togglecasino_{category}_{casino}"
                    ))
            keyboard.append(row)
        
        # Apply & Back buttons
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Appliquer" if lang == 'fr' else "✅ Apply",
                callback_data=f"lastcalls_{category}_page_1"
            ),
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"lastcalls_{category}_page_1"
            )
        ])
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as edit_error:
            # Ignore "message is not modified" errors
            if "message is not modified" not in str(edit_error).lower():
                raise
        
    except Exception as e:
        logger.error(f"Error in show_casino_filter: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("lastcalls_togglecasino_"))
async def toggle_casino(callback: types.CallbackQuery):
    """Toggle casino selection"""
    
    parts = callback.data.split('_')
    # Handle toggle callback: lastcalls_togglecasino_{category}_{casino}
    # But category might be in parts[2] OR if casino name has underscores it's more complex
    # Let's find where category ends and casino starts by looking for known categories
    known_categories = ['arbitrage', 'middle', 'goodev']
    
    category = None
    casino_parts = []
    
    for i, part in enumerate(parts[2:], start=2):
        if part in known_categories and category is None:
            category = part
        elif category is not None:
            casino_parts.append(part)
    
    # If no category found, assume parts[2] is category
    if category is None:
        category = parts[2]
        casino_parts = parts[3:]
    
    casino = '_'.join(casino_parts)
    
    user_id = callback.from_user.id
    filters = get_user_filters(user_id, category)
    selected_casinos = filters['casinos'].copy()
    
    if casino == 'all':
        # Toggle "all"
        if 'all' in selected_casinos:
            selected_casinos = []
        else:
            selected_casinos = ['all']
    else:
        # Remove 'all' if present
        if 'all' in selected_casinos:
            selected_casinos = [casino]
        else:
            # Toggle individual casino
            if casino in selected_casinos:
                selected_casinos.remove(casino)
            else:
                selected_casinos.append(casino)
        
        # If none selected, default to 'all'
        if not selected_casinos:
            selected_casinos = ['all']
    
    set_user_filters(user_id, category, casinos=selected_casinos, page=1)
    
    # Show feedback
    is_selected = casino in selected_casinos or (casino == 'all' and 'all' in selected_casinos)
    await callback.answer("✅ Sélectionné" if is_selected else "⬜ Désélectionné")
    
    # Rebuild the casino filter display
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        
        # Map category to bet_type
        category_to_type = {
            'arbitrage': 'arbitrage',
            'middle': 'middle',
            'goodev': 'good_ev'
        }
        bet_type = category_to_type.get(category, 'arbitrage')
        
        # Get all unique casinos from today's drops for this category
        today = date.today()
        all_drops = db.query(DropEvent).filter(
            DropEvent.received_at >= today,
            DropEvent.bet_type == bet_type
        ).all()
        
        casinos_set = set()
        for drop in all_drops:
            drop_casinos = extract_casinos_from_drop(drop)
            casinos_set.update(drop_casinos)
        
        casinos_list = sorted(list(casinos_set))
        
        # Get current filters
        filters = get_user_filters(user_id, category)
        selected_casinos = filters['casinos']
        
        if lang == 'fr':
            text = (
                f"🎰 <b>FILTRER PAR CASINO</b>\n\n"
                f"Sélectionne les casinos à afficher:\n\n"
            )
        else:
            text = (
                f"🎰 <b>FILTER BY CASINO</b>\n\n"
                f"Select casinos to display:\n\n"
            )
        
        # Build keyboard with casino checkboxes
        keyboard = []
        
        # "All" button
        all_checked = "✅" if 'all' in selected_casinos else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{all_checked} Tous les casinos" if lang == 'fr' else f"{all_checked} All casinos",
                callback_data=f"lastcalls_togglecasino_{category}_all"
            )
        ])
        
        # Individual casinos (2 per row)
        for i in range(0, len(casinos_list), 2):
            row = []
            for j in range(2):
                if i + j < len(casinos_list):
                    casino_name = casinos_list[i + j]
                    checked = "✅" if casino_name in selected_casinos or 'all' in selected_casinos else "⬜"
                    row.append(InlineKeyboardButton(
                        text=f"{checked} {casino_name}",
                        callback_data=f"lastcalls_togglecasino_{category}_{casino_name}"
                    ))
            keyboard.append(row)
        
        # Apply & Back buttons
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Appliquer" if lang == 'fr' else "✅ Apply",
                callback_data=f"lastcalls_{category}_page_1"
            ),
            InlineKeyboardButton(
                text="◀️ Retour" if lang == 'fr' else "◀️ Back",
                callback_data=f"lastcalls_{category}_page_1"
            )
        ])
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as edit_error:
            # Ignore "message is not modified" errors
            if "message is not modified" not in str(edit_error).lower():
                raise
                
    except Exception as e:
        logger.error(f"Error in toggle_casino: {e}")
    finally:
        db.close()


@router.callback_query(F.data.startswith("viewcall_"))
async def view_call_details(callback: types.CallbackQuery):
    """Display full call details like original alert - using Calculator like old system"""
    await callback.answer()
    
    drop_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = user.language if user else 'en'
        # Get user's rounding preferences
        user_rounding = user.stake_rounding if user else 0
        user_mode = getattr(user, 'rounding_mode', 'nearest') if user else 'nearest'
        
        drop = db.query(DropEvent).filter(DropEvent.id == drop_id).first()
        
        if not drop or not drop.payload:
            await callback.answer("❌ Call non trouvé" if lang == 'fr' else "❌ Call not found", show_alert=True)
            return
        
        # Use payload like old system
        arb_data = drop.payload
        bet_type = drop.bet_type or 'arbitrage'  # Detect bet type
        
        # Import calculator
        from core.calculator import ArbitrageCalculator
        from core.casinos import get_casino_logo
        from utils.oddsjam_formatters import format_good_odds_message, format_middle_message
        from utils.stake_rounder import round_arbitrage_stakes
        
        bankroll = user.default_bankroll or 750.0
        
        # Extract data from payload
        arb_pct = arb_data.get('arb_percentage', 0)
        match = arb_data.get('match', 'Unknown')
        league = arb_data.get('league', '')
        market = arb_data.get('market', '')
        outcomes = arb_data.get('outcomes', [])
        
        # Calculate stakes and profit using Calculator (static method)
        # Convert odds to int to avoid type errors (odds might be stored as strings)
        odds_list = []
        for outcome in outcomes:
            odds_raw = outcome.get('odds', 0)
            try:
                odds_list.append(int(odds_raw))
            except (ValueError, TypeError):
                odds_list.append(0)
        safe_calc = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds_list)
        
        cashh = bankroll
        stakes = safe_calc.get('stakes', [])  # Get original stakes
        profit = safe_calc.get('profit', 0)
        roi = (profit / cashh * 100) if cashh > 0 else 0
        
        # Apply user's rounding preference with CORRECT recalculation
        rounded_applied = False
        if user_rounding > 0 and len(stakes) >= 2 and len(odds_list) >= 2:
            rounded_result = round_arbitrage_stakes(
                stakes[0], stakes[1],
                odds_list[0], odds_list[1],
                cashh, user_rounding, user_mode
            )
            
            if rounded_result:
                # Use ALL recalculated values
                stakes = [rounded_result['stake_a'], rounded_result['stake_b']]
                profit = rounded_result['profit_guaranteed']
                roi = rounded_result['roi_percent']
                arb_pct = roi  # Update arb % to match rounded stakes
                rounded_applied = True
            # Si rounded_result est None, garder valeurs originales
        
        # Map casino names to emojis (like in original alert)
        casino_emojis = {
            'betsson': '🔶',
            'pinny': '⛰️',
            'pinnacle': '⛰️',
            'coolbet': '❄️',
            'ibet': '🎲',
            'bet99': '🔷',
            'sports interaction': '🟢',
            'bet365': '🟩'
        }
        
        # Build message based on bet_type - use SAME formatters as live alerts!
        if bet_type == 'good_ev':
            # Use the same rich formatter as live Good EV alerts
            try:
                text = format_good_odds_message(arb_data, cashh, lang)
            except Exception as e:
                logger.error(f"Error formatting Good EV message: {e}")
                # Fallback to simple format
                ev_percent = arb_data.get('ev_percent', 0)
                text = f"💎 <b>GOOD ODDS ALERT - {ev_percent}% EV</b>\n\n"
                text += f"🏀 <b>{match}</b>\n📊 {league} - {market}\n"
            
        elif bet_type == 'middle':
            # Use the same rich formatter as live Middle alerts
            try:
                # format_middle_message(data, calc, user_cash, lang, rounding)
                text = format_middle_message(arb_data, {}, cashh, lang, rounding=0)
            except Exception as e:
                logger.error(f"Error formatting Middle message: {e}")
                # Fallback to simple format
                text = f"🎯 <b>MIDDLE ALERT - {arb_pct:.2f}%</b> 🎯\n\n"
                text += f"🏀 <b>{match}</b>\n📊 {league} - {market}\n"
            
        else:
            # Arbitrage format (default)
            # Use roi (recalculated) instead of arb_pct (original) for title if rounding was applied
            display_pct = roi if rounded_applied else arb_pct
            if lang == 'fr':
                text = f"🚨 <b>ALERTE ARBITRAGE - {display_pct:.2f}%</b> 🚨\n\n"
            else:
                text = f"🚨 <b>ARBITRAGE ALERT - {display_pct:.2f}%</b> 🚨\n\n"
            
            text += f"🏟️ <b>{match}</b>\n"
            text += f"🏅 {league} - {market}\n"
            # Use formatted_time or commence_time from payload
            time_str = arb_data.get('formatted_time') or arb_data.get('commence_time') or arb_data.get('time', '')
            if time_str and time_str != 'TBD':
                text += f"🕐 {time_str}\n"
            text += "\n"
            text += f"💰 <b>CASHH: ${cashh:.1f}</b>\n"
            
            if lang == 'fr':
                text += f"✅ <b>Profit Garanti: ${profit:.2f} (ROI: {roi:.2f}%)</b>\n\n"
            else:
                text += f"✅ <b>Guaranteed Profit: ${profit:.2f} (ROI: {roi:.2f}%)</b>\n\n"
            
            # Add outcome details with stakes
            for i, outcome_data in enumerate(outcomes[:2]):
                casino_name = outcome_data.get('casino', 'Unknown')
                casino_lower = casino_name.lower()
                emoji = casino_emojis.get(casino_lower, '🎰')
                outcome_name = outcome_data.get('outcome', 'Unknown')
                odds_val = outcome_data.get('odds', 0)
                try:
                    odds_int = int(odds_val)
                    odds_str = f"+{odds_int}" if odds_int > 0 else str(odds_int)
                except (ValueError, TypeError):
                    odds_str = str(odds_val)
                
                # Calculate return for this stake
                if i < len(stakes):
                    stake = stakes[i]
                    if odds_int > 0:
                        return_val = stake * (1 + odds_int / 100)
                    else:
                        return_val = stake * (1 + 100 / abs(odds_int))
                    
                    stake_label = "Miser" if lang == 'fr' else "Stake"
                    return_label = "Retour" if lang == 'fr' else "Return"
                    
                    text += f"{emoji} <b>[{casino_name}]</b> {outcome_name}\n"
                    text += f"💵 {stake_label}: <code>${stake:.2f}</code> ({odds_str}) → {return_label}: ${return_val:.2f}\n\n"
            
            # Add warning
            warning = "⚠️ <b>Attention: les cotes peuvent changer - toujours vérifier avant de bet!</b>\n" if lang == 'fr' else "⚠️ <b>Odds can change - always verify before betting!</b>\n"
            text += warning
        
        # Add posted date/time at the bottom
        if drop.received_at:
            from datetime import datetime, timezone, timedelta
            # Convert to ET timezone
            et_tz = timezone(timedelta(hours=-5))
            dt_et = drop.received_at.replace(tzinfo=timezone.utc).astimezone(et_tz)
            
            # Format: "Nov 27, 2025 at 12:34 PM ET"
            posted_date = dt_et.strftime('%b %d, %Y')
            posted_time = dt_et.strftime('%I:%M %p')
            
            if lang == 'fr':
                text += f"\n📮 <i>Posté: {posted_date} à {posted_time} ET</i>\n"
            else:
                text += f"\n📮 <i>Posted: {posted_date} at {posted_time} ET</i>\n"
        
        # Build casino buttons for quick links
        casino_buttons = []
        from utils.odds_api_links import get_fallback_url
        
        # Extract casino names from outcomes to build buttons
        for outcome_data in outcomes[:2]:  # Max 2 casinos for arb/middle, 1 for good_ev
            casino_name = outcome_data.get('casino', 'Unknown')
            casino_lower = casino_name.lower()
            emoji = casino_emojis.get(casino_lower, '🎰')
            casino_url = get_fallback_url(casino_name)
            
            casino_buttons.append(InlineKeyboardButton(
                text=f"{emoji} {casino_name}",
                url=casino_url  # 🎯 FIX: Use url instead of callback_data
            ))
        
        # Build keyboard with NEW ORDER
        keyboard = []
        
        # 1. Casino links row (TOP)
        if len(casino_buttons) == 2:
            keyboard.append(casino_buttons)
        elif len(casino_buttons) == 1:
            keyboard.append([casino_buttons[0]])
        
        # Calculate total stake based on bet type
        if bet_type == 'good_ev':
            total_stake = cashh  # For Good EV, stake entire bankroll on single bet
        else:
            # For arbitrage/middle, sum of both stakes
            total_stake = sum(stakes)
        
        # 2. I BET with profit in button text
        keyboard.append([
            InlineKeyboardButton(
                text=f"💰 I BET (${profit:.2f} profit)" if lang == 'en' else f"💰 J'AI PARIÉ (${profit:.2f} profit)",
                callback_data=f"i_bet_{drop_id}_{total_stake:.2f}_{profit:.2f}"
            )
        ])
        
        # 3. Custom Calculator - use calc_ prefix which is handled
        keyboard.append([
            InlineKeyboardButton(
                text="🧮 Custom Calculator" if lang == 'en' else "🧮 Calculateur Personnalisé",
                callback_data=f"calc_{drop_id}|menu"
            )
        ])
        
        # 4. Simulation & Risk (only for Middle and Good EV)
        if bet_type in ['middle', 'good_ev']:
            keyboard.append([
                InlineKeyboardButton(
                    text="📊 Simulation & Risk" if lang == 'en' else "📊 Simulation & Risque",
                    callback_data=f"sim_{drop_id}"
                )
            ])
        
        # 5. Change CASHH - use chg_cashh_ prefix which is handled  
        keyboard.append([
            InlineKeyboardButton(
                text="💵 Change CASHH" if lang == 'en' else "💵 Changer CASHH",
                callback_data=f"chg_cashh_{drop_id}"
            )
        ])
        
        # 5. Verify Odds - note: this requires a valid call_id in PENDING_CALLS
        # For Last Calls, we might not have the original call_id, so skip for now
        # TODO: Store call_id in DropEvent for verify functionality
        # keyboard.append([
        #     InlineKeyboardButton(
        #         text="✅ Verify Odds" if lang == 'en' else "✅ Vérifier Odds",
        #         callback_data=f"verify_odds:{some_call_id}"
        #     )
        # ])
        
        # 6. Back to Last Calls (BOTTOM) - Return to specific category
        # Map bet_type to callback category format
        category_map = {
            'arbitrage': 'arbitrage',
            'middle': 'middle',
            'good_ev': 'goodev',
            'goodev': 'goodev'
        }
        callback_category = category_map.get(bet_type, 'arbitrage')
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Last Calls",
                callback_data=f"lastcalls_{callback_category}_page_1"
            )
        ])
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as edit_error:
            # Ignore "message is not modified" errors
            if "message is not modified" not in str(edit_error).lower():
                raise
        
    except Exception as e:
        logger.error(f"Error in view_call_details: {e}")
        await callback.answer("❌ Error", show_alert=True)
    finally:
        db.close()
