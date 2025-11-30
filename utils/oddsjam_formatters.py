"""
OddsJam Message Formatters
Format Good Odds and Middle alerts for Telegram
"""
from typing import Dict
from utils.odds_api_links import get_fallback_url
from core.casinos import get_casino_logo
from utils.ev_quality import get_ev_quality, get_profile_warning, calculate_bankroll_multiplier
from utils.oddsjam_parser import american_to_decimal
from utils.middle_calculator import (
    classify_middle_type,
    describe_middle_zone,
    get_unit,
    analyze_spread_window,
)
from utils.good_odds_calculator import (
    calculate_true_winrate,
    calculate_good_odds_example,
    calculate_kelly_bankroll,
    get_ev_quality_tag
)
from utils.sport_emoji import get_sport_emoji


def extract_player_name(selection: str) -> str:
    """
    Extract player name from selection string like 'Isiah Pacheco Over 33.5'
    Returns the player name or empty string if not found
    """
    if not selection:
        return ""
    
    # Remove common patterns: Over/Under X.5, +X, -X, etc.
    import re
    # Match everything before Over/Under/O/U followed by a number
    match = re.match(r'^(.+?)\s+(?:Over|Under|O|U)\s+[\d.+-]+', selection, re.IGNORECASE)
    if match:
        player_candidate = match.group(1).strip()
        # Make sure it's not just "Over" or "Under" itself
        if player_candidate.lower() not in ['over', 'under', 'o', 'u']:
            return player_candidate
    
    # If selection starts with Over/Under, it's not a player name
    if selection.lower().startswith(('over', 'under')):
        return ""
    
    # Fallback: return empty if no valid pattern found
    return ""


def format_good_odds_message(data: Dict, user_cash: float, lang: str = 'en', user_profile: str = 'beginner', total_bets: int = 0) -> str:
    """
    Format Good Odds (Positive EV) message with quality tags and detailed projections
    
    Args:
        data: Parsed good odds data
        user_cash: User's stake amount
        lang: Language ('en' or 'fr')
        user_profile: User's experience level
        total_bets: Total good odds bets placed by user
    """
    
    emoji = get_casino_logo(data['bookmaker'])
    ev_percent = float(data['ev_percent'])
    
    # Parse odds
    try:
        odds_int = int(data['odds'].replace('+', ''))
    except:
        odds_int = 100
    
    # Get CORRECT quality tag
    quality = get_ev_quality_tag(ev_percent, odds_int)
    
    # Calculate projections
    avg_profit_per_bet = user_cash * (ev_percent / 100)
    projection_100 = avg_profit_per_bet * 100
    
    # Calculate TRUE win rate (NOT implied!)
    true_winrate = calculate_true_winrate(odds_int, ev_percent)
    loss_rate = 1 - true_winrate
    
    # CORRECT example over 10 bets
    example = calculate_good_odds_example(odds_int, user_cash, ev_percent, 10)
    
    # CORRECT recommended bankroll using Kelly
    min_bankroll = calculate_kelly_bankroll(user_cash, ev_percent, odds_int, kelly_mult=0.25)
    
    # Get profile warning if applicable
    profile_warning = get_profile_warning(ev_percent, user_profile, lang) if callable(get_profile_warning) else ""
    
    # Check if player field exists in data (from OddsJam parser)
    player_name = data.get('player', '')
    
    # If no player field, try to extract from selection
    if not player_name:
        player_name = extract_player_name(data.get('selection', ''))
    
    # If still no player name found but it's a player prop, try to extract from market
    # Market format examples: 
    # - "Player Rebounds" or "Player Rebounds : Player Name Over 3.5"
    # - "NBA - Player Rebounds"
    if not player_name and 'Player' in data.get('market', ''):
        market_str = data.get('market', '')
        # Try to extract player name from market string after ":"
        import re
        if ':' in market_str:
            # Split on : and extract name from right side
            after_colon = market_str.split(':', 1)[1].strip()
            # Extract name before "Over" or "Under"
            match = re.match(r'^(.+?)\s+(?:Over|Under)\s+[\d.]+', after_colon, re.IGNORECASE)
            if match:
                player_name = match.group(1).strip()
    
    # Get correct sport emoji
    sport_emoji = get_sport_emoji(data.get('league', ''), data.get('sport', ''))
    
    # Build market display with player name if it's a player prop
    is_player_prop = 'Player' in data.get('market', '')
    
    if is_player_prop:
        # For player props, show player name prominently if we have it
        if player_name:
            market_display = f"{data['league']} - {data['market']}"
            player_line = f"👤 <b>{player_name}</b>: {data['selection']}\n"
        else:
            # No player name extracted, show selection only
            market_display = f"{data['league']} - {data['market']}"
            player_line = f"📊 {data['selection']}\n"
    else:
        # Not a player prop
        market_display = f"{data['league']} - {data['market']}"
        player_line = f"📊 {data['selection']}\n"
    
    # Match time from API enrichment
    time_line = ""
    if data.get('formatted_time'):
        time_line = f"🕐 {data['formatted_time']}\n"
    elif data.get('commence_time'):
        time_line = f"🕐 {data['commence_time']}\n"
    
    if lang == 'fr':
        message = (
            f"{quality['tag']}\n\n"
            f"{quality['emoji']} <b>GOOD ODDS ALERT - {ev_percent}% EV</b>\n\n"
            f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
            f"📊 {market_display}\n"
            f"{time_line}"
            f"{player_line}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>MEILLEURE COTE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} <b>[{data['bookmaker']}]</b> {data['selection']}\n"
            f"Cote: <b>{data['odds']}</b>\n"
            f"💵 Stake: <b>${user_cash:.2f}</b>\n\n"
            f"💰 <b>CE PARI:</b>\n"
            f"✅ <b>Si tu GAGNES:</b> +${example['profit_if_win']:.2f} profit (ROI: {example['profit_if_win']/user_cash*100:.1f}%)\n"
            f"❌ <b>Si tu PERDS:</b> -{user_cash:.2f}$ (perte totale)\n\n"
            f"📈 <b>VALUE:</b>\n"
            f"• EV+: {ev_percent}%\n"
            f"• Profit moyen/bet: ${avg_profit_per_bet:.2f}\n"
            f"• Sur 100 bets: ~${projection_100:.0f}\n\n"
            f"💡 <b>Recommandé pour:</b> {quality['recommended_for']}\n"
            f"{quality['advice']}\n\n"
            f"⚠️ <b>Attention: les cotes peuvent changer - toujours vérifier avant de bet!</b>"
        )
    else:
        message = (
            f"{quality['tag']}\n\n"
            f"{quality['emoji']} <b>GOOD ODDS ALERT - {ev_percent}% EV</b>\n\n"
            f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
            f"📊 {market_display}\n"
            f"{time_line}"
            f"{player_line}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>BEST ODDS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} <b>[{data['bookmaker']}]</b> {data['selection']}\n"
            f"Odds: <b>{data['odds']}</b>\n"
            f"💵 Stake: <b>${user_cash:.2f}</b>\n\n"
            f"💰 <b>THIS BET:</b>\n"
            f"✅ <b>If you WIN:</b> +${example['profit_if_win']:.2f} profit (ROI: {example['profit_if_win']/user_cash*100:.1f}%)\n"
            f"❌ <b>If you LOSE:</b> -${user_cash:.2f} (total loss)\n\n"
            f"📈 <b>VALUE:</b>\n"
            f"• EV+: {ev_percent}%\n"
            f"• Avg profit/bet: ${avg_profit_per_bet:.2f}\n"
            f"• Over 100 bets: ~${projection_100:.0f}\n\n"
            f"💡 <b>Recommended for:</b> {quality['recommended_for']}\n"
            f"{quality['advice']}\n\n"
            f"⚠️ <b>Odds can change - always verify before betting!</b>"
        )
    
    return message


def format_middle_message(data: Dict, calc: Dict, user_cash: float, lang: str = 'en', rounding: int = 0) -> str:
    """Format Middle message with API enriched data"""
    """
    Format Middle opportunity message
    
    A middle bet = overlapping lines with:
    - Small loss if one wins (80-85% of time)
    - BIG profit if both win (15-20% of time)
    - EV+ long term
    
    Args:
        data: Parsed middle data
        calc: Calculation dict (deprecated, recomputed)
        user_cash: User's bankroll
        lang: Language ('en' or 'fr')
        rounding_level: 0=precise, 1=dollar, 5=five, 10=ten
    """
    
    # Normalize structure: older payloads loaded from DB may not have side_a/side_b,
    # only an outcomes[] array. Rebuild minimal side dicts in that case so the
    # middle classifier and formatter still work.
    side_a = data.get('side_a')
    side_b = data.get('side_b')
    if not side_a or not side_b:
        outcomes = data.get('outcomes') or []
        if len(outcomes) >= 2:
            o1, o2 = outcomes[0], outcomes[1]

            def _extract_line(sel: str) -> str:
                if not sel:
                    return "0"
                parts = str(sel).split()
                for p in reversed(parts):
                    try:
                        float(p.replace('+', '').replace('−', '-'))
                        return p
                    except Exception:
                        continue
                return "0"

            side_a = {
                'bookmaker': o1.get('casino') or o1.get('bookmaker', ''),
                'selection': o1.get('outcome', ''),
                'line': _extract_line(o1.get('outcome', '')),
                'odds': str(o1.get('odds', '0')),
            }
            side_b = {
                'bookmaker': o2.get('casino') or o2.get('bookmaker', ''),
                'selection': o2.get('outcome', ''),
                'line': _extract_line(o2.get('outcome', '')),
                'odds': str(o2.get('odds', '0')),
            }
        else:
            # Fallback: not enough data to reconstruct, return simple error message
            return "❌ Middle data incomplete (missing side_a/side_b)"

    # Ensure market context inside sides for probability estimation
    side_a = dict(side_a)
    side_b = dict(side_b)
    side_a.setdefault('market', data.get('market', ''))
    side_b.setdefault('market', data.get('market', ''))

    # Reinject normalized sides into data so all later code using
    # data['side_a']/data['side_b'] works safely even for old payloads.
    try:
        data['side_a'] = side_a
        data['side_b'] = side_b
    except Exception:
        # In case data is not a mutable mapping, we just skip; the
        # function below still uses side_a/side_b directly where needed.
        pass

    # Normalize team names for older payloads that may only have `match`
    match_str = data.get('match') or ''
    team1 = data.get('team1')
    team2 = data.get('team2')
    if not team1 or not team2:
        if ' vs ' in match_str:
            parts = match_str.split(' vs ', 1)
            if not team1:
                team1 = parts[0].strip()
            if not team2:
                team2 = parts[1].strip()
        else:
            # Fallback generic names
            team1 = team1 or 'Team A'
            team2 = team2 or 'Team B'
    try:
        data['team1'] = team1
        data['team2'] = team2
    except Exception:
        pass

    emoji_a = get_casino_logo(side_a.get('bookmaker', ''))
    emoji_b = get_casino_logo(side_b.get('bookmaker', ''))
    
    # Get correct sport emoji
    sport_emoji = get_sport_emoji(data.get('league', ''), data.get('sport', ''))
    
    # For player props Middle, the player name is usually in side_a['team']
    # Check if this is a player prop first
    is_player_prop = 'Player' in data.get('market', '')
    
    player_name = ''
    if is_player_prop:
        # Try to get player name from side_a team field (for Middle player props)
        team_field = side_a.get('team', '')
        # If team field doesn't look like a team name, it's probably a player name
        if team_field and not any(word in team_field.lower() for word in ['vs', 'at', 'state', 'city', 'united', 'fc']):
            player_name = team_field
        
        # If still no player name, try to extract from selection
        if not player_name:
            player_name = extract_player_name(side_a.get('selection', ''))
        
        # If still no player name, try to extract from market
        # Market format: "Player Rushing Yards : Thomas Castellanos Over 49.5/..."
        if not player_name:
            market_str = data.get('market', '')
            import re
            if ':' in market_str:
                # Split on : and extract name from right side
                after_colon = market_str.split(':', 1)[1].strip()
                # Extract name before "Over" or "Under"
                match = re.match(r'^(.+?)\s+(?:Over|Under)\s+[\d.]+', after_colon, re.IGNORECASE)
                if match:
                    player_name = match.group(1).strip()

    # Classify middle and recompute calc from classification (authoritative) with rounding
    cls = classify_middle_type(side_a, side_b, user_cash, rounding)

    total_stake = cls['total_stake']
    profit_a_only = cls['profit_scenario_1']
    profit_b_only = cls['profit_scenario_3']
    profit_middle = cls['profit_scenario_2']
    middle_prob = cls['middle_prob']
    ev_percent = cls['ev_percent']
    middle_type = cls['type']

    # Build zone description and gap / spread window
    market_lower = (data.get('market','') or '').lower()
    is_spread = ('spread' in market_lower)
    try:
        gap = abs(float(side_a['line']) - float(side_b['line']))
    except Exception:
        gap = 0.0
    # Match time from API enrichment
    time_line = ""
    if data.get('formatted_time'):
        time_line = f"🕐 {data['formatted_time']}\n"
    elif data.get('commence_time'):
        time_line = f"🕐 {data['commence_time']}\n"
    
    zone_desc = describe_middle_zone({
        'market': data.get('market',''),
        'side_a': side_a,
        'side_b': side_b,
    })
    window = analyze_spread_window(side_a, side_b) if is_spread else {}

    # Determine if BOTH bets can win (true middle with integer landing zone)
    # is_push_middle = True means structure is WIN + PUSH (one side wins, the other is refunded)
    both_win_possible = False
    is_push_middle = False
    try:
        sa_sel = (side_a.get('selection') or '').lower()
        sb_sel = (side_b.get('selection') or '').lower()
        
        # Try to parse lines as floats
        try:
            line_a = float(side_a['line'])
            line_b = float(side_b['line'])
        except:
            line_a = None
            line_b = None
        
        # Identify over and under lines
        over_line = None
        under_line = None
        if 'over' in sa_sel:
            over_line = float(side_a['line'])
        if 'over' in sb_sel:
            over_line = float(side_b['line']) if over_line is None else over_line
        if 'under' in sa_sel:
            under_line = float(side_a['line'])
        if 'under' in sb_sel:
            under_line = float(side_b['line']) if under_line is None else under_line
        
        # CASE A: Generic lines (71 vs 71.5) without Over/Under keywords
        # This handles "1st Half Total Points" type markets
        if over_line is None and under_line is None and line_a is not None and line_b is not None:
            # Sort lines to determine which is lower/higher
            low_line = min(line_a, line_b)
            high_line = max(line_a, line_b)
            
            def is_half(x: float) -> bool:
                return abs((x - int(x)) - 0.5) < 1e-6
            def is_integer(x: float) -> bool:
                return abs(x - round(x)) < 1e-6
            
            # Case: 71 (integer) vs 71.5 (X.5) → jackpot at 71
            # For a middle_safe, this MUST be a jackpot scenario (otherwise not "safe")
            # Interpretation: 71 = "at least 71", 71.5 = "at most 71"
            # At total = 71: BOTH win! 🎰
            if is_integer(low_line) and is_half(high_line) and abs(high_line - low_line - 0.5) < 1e-6:
                both_win_possible = True
                jackpot_value = int(round(low_line))
                zone_desc = f"Total = {jackpot_value}"
                # Both bets win at the integer value
                profit_middle = cls['return_a'] + cls['return_b'] - total_stake
            
            # Case: Both X.5 lines with gap >= 1.0
            elif is_half(low_line) and is_half(high_line) and (high_line - low_line) >= 1.0:
                both_win_possible = True
                import math
                sweet_spot_start = int(math.ceil(low_line))
                sweet_spot_end = int(math.floor(high_line))
                if sweet_spot_start == sweet_spot_end:
                    zone_desc = f"Total = {sweet_spot_start}"
                else:
                    zone_desc = f"{sweet_spot_start} ≤ Total ≤ {sweet_spot_end}"
        
        # CASE B: Explicit Over/Under lines
        if over_line is not None and under_line is not None:
            # Check for jackpot zone (push + win scenario)
            def is_half(x: float) -> bool:
                return abs((x - int(x)) - 0.5) < 1e-6
            def is_integer(x: float) -> bool:
                return abs(x - round(x)) < 1e-6
            
            import math
            
            # Case 1: Both X.5 lines with gap >= 1.0 (both win possible)
            if is_half(over_line) and is_half(under_line) and (under_line - over_line) >= 1.0:
                both_win_possible = True
                sweet_spot_start = int(math.ceil(over_line))
                sweet_spot_end = int(math.floor(under_line))
                if sweet_spot_start == sweet_spot_end:
                    zone_desc = f"Total = {sweet_spot_start}"
                else:
                    zone_desc = f"{sweet_spot_start} ≤ Total ≤ {sweet_spot_end}"
            
            # Case 2: Over integer + Under (integer+0.5) → jackpot when total = integer
            # Ex: Over 3 + Under 3.5 → jackpot at 3 (Over pushes, Under wins)
            elif is_integer(over_line) and is_half(under_line) and abs(under_line - over_line - 0.5) < 1e-6:
                both_win_possible = True
                is_push_middle = True
                jackpot_value = int(round(over_line))
                zone_desc = f"Total = {jackpot_value}"
                # Recalculate jackpot profit: push (refund stake_a) + win (return_b) - total_stake
                # Over is side_a or side_b?
                if 'over' in sa_sel:
                    # Over is side_a → push stake_a, win return_b
                    profit_middle = cls['stake_a'] + cls['return_b'] - total_stake
                else:
                    # Over is side_b → push stake_b, win return_a
                    profit_middle = cls['stake_b'] + cls['return_a'] - total_stake
            
            # Case 3: Under integer + Over (integer-0.5) → jackpot when total = integer
            # Ex: Under 4 + Over 3.5 → jackpot at 4 (Under pushes, Over wins)
            elif is_integer(under_line) and is_half(over_line) and abs(under_line - over_line - 0.5) < 1e-6:
                both_win_possible = True
                is_push_middle = True
                jackpot_value = int(round(under_line))
                zone_desc = f"Total = {jackpot_value}"
                # Recalculate jackpot profit: push (refund) + win (return) - total_stake
                # Under is side_a or side_b?
                if 'under' in sa_sel:
                    # Under is side_a → push stake_a, win return_b
                    profit_middle = cls['stake_a'] + cls['return_b'] - total_stake
                else:
                    # Under is side_b → push stake_b, win return_a
                    profit_middle = cls['stake_b'] + cls['return_a'] - total_stake
    except Exception:
        both_win_possible = False
    # Spreads: rely on spread window analyzer
    if is_spread and window.get('is_spread') and window.get('double_exists'):
        both_win_possible = True
        zone_desc = f"{window['double_start']} ≤ M ≤ {window['double_end']}"

    times_middle = int(round(middle_prob * 100))
    times_no_middle = 100 - times_middle
    # Worst-case loss when no middle hits (for risky type)
    worst_loss = min(profit_a_only, profit_b_only)
    # Expected profit per bet
    ev_profit = (middle_prob * profit_middle) + ((1 - middle_prob) * (worst_loss if worst_loss < 0 else min(profit_a_only, profit_b_only)))
    net_100 = times_middle * profit_middle + times_no_middle * (worst_loss if worst_loss < 0 else min(profit_a_only, profit_b_only))
    
    # Precompute labels and push scenarios for spreads
    sel_a = side_a.get('selection', side_a.get('line', 'Side A'))
    sel_b = side_b.get('selection', side_b.get('line', 'Side B'))
    push_lines_fr = []
    push_lines_en = []
    if is_spread and window.get('is_spread'):
        # Profit for push when the other side wins
        stake_a = cls['stake_a']; stake_b = cls['stake_b']
        ret_a = cls['return_a']; ret_b = cls['return_b']
        for p in sorted(window.get('push_points', []), key=lambda x: x['m']):
            m = p['m']; winner = p.get('winner')
            if winner == window.get('pos_side'):
                # Dog wins, fav pushes
                profit_push = (ret_a if window.get('pos_side')=='a' else ret_b) - (stake_a if window.get('pos_side')=='a' else stake_b)
                line_fr = f"M = {m}\n→ {sel_a if window.get('pos_side')=='a' else sel_b} gagne, {(sel_b if window.get('pos_side')=='a' else sel_a)} push\n→ Profit: ≈ ${profit_push:.2f}"
                line_en = f"M = {m}\n→ {sel_a if window.get('pos_side')=='a' else sel_b} wins, {(sel_b if window.get('pos_side')=='a' else sel_a)} pushes\n→ Profit: ≈ ${profit_push:.2f}"
                push_lines_fr.append(line_fr)
                push_lines_en.append(line_en)
            elif winner == window.get('neg_side'):
                # Fav wins, dog pushes
                profit_push = (ret_b if window.get('neg_side')=='b' else ret_a) - (stake_b if window.get('neg_side')=='b' else stake_a)
                line_fr = f"M = {m}\n→ {sel_b if window.get('neg_side')=='b' else sel_a} gagne, {(sel_a if window.get('neg_side')=='b' else sel_b)} push\n→ Profit: ≈ ${profit_push:.2f}"
                line_en = f"M = {m}\n→ {sel_b if window.get('neg_side')=='b' else sel_a} wins, {(sel_a if window.get('neg_side')=='b' else sel_b)} pushes\n→ Profit: ≈ ${profit_push:.2f}"
                push_lines_fr.append(line_fr)
                push_lines_en.append(line_en)

    if lang == 'fr':
        if middle_type == 'middle_safe' and both_win_possible:
            min_profit = min(profit_a_only, profit_b_only)
            jackpot_roi = (profit_middle / total_stake) * 100 if total_stake else 0
            
            # Build player line if player prop
            if is_player_prop and player_name:
                player_line = f"👤 <b>{player_name}</b>\n"
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # For scenarios, include player name
                scenario_1_label = f"{player_name} {data['side_a'].get('selection','Side A')} seul"
                scenario_3_label = f"{player_name} {data['side_b'].get('selection','Side B')} seul"
            else:
                player_line = ""
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # Without player name
                scenario_1_label = f"{data['side_a'].get('selection','Side A')} seul"
                scenario_3_label = f"{data['side_b'].get('selection','Side B')} seul"
            
            # Use guaranteed ROI (minimum profit / total stake) instead of EV
            guaranteed_roi = (min_profit / total_stake) * 100 if total_stake else 0
            
            message = f"✅🎰 <b>{guaranteed_roi:.1f}% MIDDLE SAFE - PROFIT GARANTI + JACKPOT!</b> 🎰✅\n\n"
            message += f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
            message += f"{market_line}"
            message += f"{player_line}"
            message += f"{time_line}"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💰 <b>CONFIGURATION</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
            message += f"💵 Mise: ${cls['stake_a']:.2f} ({data['side_a']['odds']})\n"
            message += f"📈 Retour: ${cls['return_a']:.2f}\n\n"
            message += f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
            message += f"💵 Mise: ${cls['stake_b']:.2f} ({data['side_b']['odds']})\n"
            message += f"📈 Retour: ${cls['return_b']:.2f}\n\n"
            message += f"💰 <b>Total: ${total_stake:.2f}</b>\n\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"🎯 <b>SCÉNARIOS</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"1. {scenario_1_label}\n"
            message += f"✅ Profit: ${profit_a_only:+.2f} ({(profit_a_only/total_stake*100):.1f}%)\n\n"
            message += f"2. <b>MIDDLE HIT!</b> 🎰\n"
            message += f"🚀 Zone magique: {zone_desc}\n"
            message += (f"🚀 WIN + PUSH (1 pari gagne, l'autre push)\n" if is_push_middle else f"🚀 LES DEUX PARIS GAGNENT!\n")
            message += f"🚀 Profit: ${profit_middle:+.2f} ({jackpot_roi:.0f}% ROI!)\n\n"
            message += f"3. {scenario_3_label}\n"
            message += f"✅ Profit: ${profit_b_only:+.2f} ({(profit_b_only/total_stake*100):.1f}%)\n\n"
            message += ("\n".join(push_lines_fr) + "\n\n" if push_lines_fr else "")
            message += (f"💡 Gap: {gap} {get_unit(data.get('market',''))}\n" if not is_spread else "")
            message += f"🎲 Prob middle: ~{int(middle_prob*100)}%\n\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💎 <b>POURQUOI C'EST INCROYABLE</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"✅ Profit MIN garanti: ${min_profit:+.2f}\n"
            message += f"🛡️ Risque: ZÉRO (arbitrage!)\n"
            message += f"🎰 Chance jackpot: ~{int(middle_prob*100)}%\n"
            message += f"🚀 Jackpot si hit: ${profit_middle:+.2f}\n\n"
            message += (f"⚡ Gap de {gap:.1f} = excellent middle! ⚡\n" if not is_spread else "")
        elif middle_type == 'middle_safe':
            min_profit = min(profit_a_only, profit_b_only)
            
            # Build player line if player prop
            if is_player_prop and player_name:
                player_line = f"👤 <b>{player_name}</b>\n"
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # For scenarios, include player name
                scenario_1_label = f"{player_name} {data['side_a'].get('selection','Side A')} seul"
                scenario_2_label = f"{player_name} {data['side_b'].get('selection','Side B')} seul"
            else:
                player_line = ""
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # Without player name
                scenario_1_label = f"{data['side_a'].get('selection','Side A')} seul"
                scenario_2_label = f"{data['side_b'].get('selection','Side B')} seul"
            
            # Use guaranteed ROI (minimum profit / total stake) instead of EV
            guaranteed_roi = (min_profit / total_stake) * 100
            message = (
                f"✅🎰 <b>{guaranteed_roi:.1f}% MIDDLE SAFE - PROFIT GARANTI</b> ✅\n\n"
                f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
                f"{market_line}"
                f"{player_line}"
                f"{time_line}"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>CONFIGURATION</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
                f"💵 Mise: ${cls['stake_a']:.2f} ({data['side_a']['odds']})\n"
                f"📈 Retour: ${cls['return_a']:.2f}\n\n"
                f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
                f"💵 Mise: ${cls['stake_b']:.2f} ({data['side_b']['odds']})\n"
                f"📈 Retour: ${cls['return_b']:.2f}\n\n"
                f"💰 <b>Total: ${total_stake:.2f}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>SCÉNARIOS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1. {scenario_1_label}\n"
                f"✅ Profit: ${profit_a_only:+.2f}\n\n"
                f"2. {scenario_2_label}\n"
                f"✅ Profit: ${profit_b_only:+.2f}\n\n"
                + ("\n".join(push_lines_fr) + "\n\n" if push_lines_fr else "")
                + (f"💡 Gap: {gap} {get_unit(data.get('market',''))}\n" if gap else "")
                + f"💎 <b>PROFIT GARANTI</b> peu importe l'issue.\n\n"
                + f"⚠️ <b>Middle:</b> petit gain fréquent, GROS gain rare"
            )
        else:
            # Risky middle format (opportunity)
            extra_gap = ""
            if not is_spread:
                extra_gap = f"   → Distance: {gap} {get_unit(data.get('market',''))}\n"
            message = (
                f"🎯 <b>MIDDLE OPPORTUNITY - {ev_percent:.1f}% EV</b> 🎯\n\n"
                f"🏀 <b>{data['team1']} vs {data['team2']}</b>\n"
                f"📊 {data['league']} - {data['market']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>SETUP</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
                f"💵 Miser: <b>${cls['stake_a']:.2f}</b> ({data['side_a']['odds']})\n"
                f"📈 Si gagne → Retour: ${cls['return_a']:.2f}\n\n"
                f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
                f"💵 Miser: <b>${cls['stake_b']:.2f}</b> ({data['side_b']['odds']})\n"
                f"📈 Si gagne → Retour: ${cls['return_b']:.2f}\n\n"
                f"💰 <b>Total misé: ${total_stake:.2f}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>SCÉNARIOS POSSIBLES</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1️⃣ <b>Un seul pari gagne</b> (~{100-int(middle_prob*100)}% du temps)\n"
                f"   → Profit: <b>${min(profit_a_only, profit_b_only):+.2f}</b> ❌\n\n"
                f"2️⃣ <b>MIDDLE HIT!</b> (~{int(middle_prob*100)}% du temps)\n"
                f"   → Les DEUX gagnent! 🎯\n"
                f"   → Profit: <b>${profit_middle:+.2f}</b> 🚀🚀\n\n"
                f"💡 <b>Zone middle:</b> {zone_desc}\n"
                f"{extra_gap}"
                f"   → Probabilité: ~{int(middle_prob*100)}%\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 <b>EXPECTED VALUE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>EV moyen: +{ev_percent:.1f}%</b>\n"
                f"<b>Profit moyen/bet: ${ev_profit:+.2f}</b>\n"
                f"<b>Sur 100 middles: ${net_100:+.0f}</b>\n\n"
                f"⚠️ Ceci N'EST PAS un arbitrage. Variance élevée.\n"
            )
    else:
        if middle_type == 'middle_safe' and both_win_possible:
            min_profit = min(profit_a_only, profit_b_only)
            jackpot_roi = (profit_middle / total_stake) * 100 if total_stake else 0
            
            # Build player line if player prop
            if is_player_prop and player_name:
                player_line = f"👤 <b>{player_name}</b>\n"
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # For scenarios, include player name
                scenario_1_label = f"{player_name} {data['side_a'].get('selection','Side A')} only"
                scenario_3_label = f"{player_name} {data['side_b'].get('selection','Side B')} only"
            else:
                player_line = ""
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # Without player name
                scenario_1_label = f"{data['side_a'].get('selection','Side A')} only"
                scenario_3_label = f"{data['side_b'].get('selection','Side B')} only"
            
            # Use guaranteed ROI (minimum profit / total stake) instead of EV
            guaranteed_roi = (min_profit / total_stake) * 100 if total_stake else 0
            
            message = f"✅🎰 <b>{guaranteed_roi:.1f}% MIDDLE SAFE - GUARANTEED PROFIT + JACKPOT!</b> 🎰✅\n\n"
            message += f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
            message += f"{market_line}"
            message += f"{player_line}"
            message += f"{time_line}"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💰 <b>CONFIGURATION</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
            message += f"💵 Stake: ${cls['stake_a']:.2f} ({data['side_a']['odds']})\n"
            message += f"📈 Return: ${cls['return_a']:.2f}\n\n"
            message += f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
            message += f"💵 Stake: ${cls['stake_b']:.2f} ({data['side_b']['odds']})\n"
            message += f"📈 Return: ${cls['return_b']:.2f}\n\n"
            message += f"💰 <b>Total: ${total_stake:.2f}</b>\n\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"🎯 <b>SCENARIOS</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"1. {scenario_1_label}\n"
            message += f"✅ Profit: ${profit_a_only:+.2f} ({(profit_a_only/total_stake*100):.1f}%)\n\n"
            message += f"2. <b>MIDDLE HIT!</b> 🎰\n"
            message += f"🚀 Magic zone: {zone_desc}\n"
            message += (f"🚀 WIN + PUSH (one bet wins, the other pushes)\n" if is_push_middle else f"🚀 BOTH BETS WIN!\n")
            message += f"🚀 Profit: ${profit_middle:+.2f} ({jackpot_roi:.0f}% ROI!)\n\n"
            message += f"3. {scenario_3_label}\n"
            message += f"✅ Profit: ${profit_b_only:+.2f} ({(profit_b_only/total_stake*100):.1f}%)\n\n"
            message += ("\n".join(push_lines_en) + "\n\n" if push_lines_en else "")
            message += (f"💡 Gap: {gap} {get_unit(data.get('market',''))}\n" if not is_spread else "")
            message += f"🎲 Middle prob: ~{int(middle_prob*100)}%\n\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💎 <b>WHY IT'S GREAT</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"✅ MIN guaranteed profit: ${min_profit:+.2f}\n"
            message += f"🛡️ Risk: ZERO (arbitrage)\n"
            message += f"🎰 Jackpot chance: ~{int(middle_prob*100)}%\n"
            message += f"🚀 Jackpot if hits: ${profit_middle:+.2f}\n\n"
            message += (f"⚡ Gap {gap:.1f} = excellent middle! ⚡\n" if not is_spread else "")
        elif middle_type == 'middle_safe':
            min_profit = min(profit_a_only, profit_b_only)
            
            # Build player line if player prop
            if is_player_prop and player_name:
                player_line = f"👤 <b>{player_name}</b>\n"
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # For scenarios, include player name
                scenario_1_label = f"{player_name} {data['side_a'].get('selection','Side A')} only"
                scenario_2_label = f"{player_name} {data['side_b'].get('selection','Side B')} only"
            else:
                player_line = ""
                market_line = f"📊 {data['league']} - {data.get('market','')}\n"
                # Without player name
                scenario_1_label = f"{data['side_a'].get('selection','Side A')} only"
                scenario_2_label = f"{data['side_b'].get('selection','Side B')} only"
            
            # Use guaranteed ROI (minimum profit / total stake) instead of EV
            guaranteed_roi = (min_profit / total_stake) * 100
            message = (
                f"✅🎰 <b>{guaranteed_roi:.1f}% MIDDLE SAFE - GUARANTEED PROFIT</b> ✅\n\n"
                f"{sport_emoji} <b>{data['team1']} vs {data['team2']}</b>\n"
                f"{market_line}"
                f"{player_line}"
                f"{time_line}"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>CONFIGURATION</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
                f"💵 Stake: ${cls['stake_a']:.2f} ({data['side_a']['odds']})\n"
                f"📈 Return: ${cls['return_a']:.2f}\n\n"
                f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
                f"💵 Stake: ${cls['stake_b']:.2f} ({data['side_b']['odds']})\n"
                f"📈 Return: ${cls['return_b']:.2f}\n\n"
                f"💰 <b>Total: ${total_stake:.2f}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>SCENARIOS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1. {scenario_1_label}\n"
                f"✅ Profit: ${profit_a_only:+.2f}\n\n"
                f"2. {scenario_2_label}\n"
                f"✅ Profit: ${profit_b_only:+.2f}\n\n"
                + ("\n".join(push_lines_en) + "\n\n" if push_lines_en else "")
                + (f"💡 Gap: {gap} {get_unit(data.get('market',''))}\n" if gap else "")
                + f"💎 <b>GUARANTEED PROFIT</b> regardless of outcome.\n\n"
                + f"⚠️ <b>Middle:</b> small frequent gain, BIG rare gain"
            )
        else:
            # Extract player name from selection if it's a player prop
            player_name = extract_player_name(data['side_a'].get('selection', ''))
            market_display = f"{player_name} - {data.get('market','')}" if player_name and 'Player' in data.get('market','') else data.get('market','')
            
            message = (
                f"🎯 <b>MIDDLE OPPORTUNITY - {ev_percent:.1f}% EV</b> 🎯\n\n"
                f"🏀 <b>{data['team1']} vs {data['team2']}</b>\n"
                f"📊 {data['league']}\n"
                f"👤 {market_display}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>SETUP</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a'].get('selection', data['side_a']['line'])}\n"
                f"💵 Stake: <b>${cls['stake_a']:.2f}</b> ({data['side_a']['odds']})\n"
                f"📈 If wins → Return: ${cls['return_a']:.2f}\n\n"
                f"{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b'].get('selection', data['side_b']['line'])}\n"
                f"💵 Stake: <b>${cls['stake_b']:.2f}</b> ({data['side_b']['odds']})\n"
                f"📈 If wins → Return: ${cls['return_b']:.2f}\n\n"
                f"💰 <b>Total staked: ${total_stake:.2f}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>POSSIBLE SCENARIOS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1️⃣ <b>Only one bet wins</b> (~{100-int(middle_prob*100)}% of time)\n"
                f"   → Profit: <b>${min(profit_a_only, profit_b_only):+.2f}</b> ❌\n\n"
                f"2️⃣ <b>MIDDLE HIT!</b> (~{int(middle_prob*100)}% of time)\n"
                f"   → BOTH win! 🎯\n"
                f"   → Profit: <b>${profit_middle:+.2f}</b> 🚀🚀\n\n"
                f"💡 <b>Middle zone:</b> {zone_desc}\n"
                + (f"   → Gap: {gap} {get_unit(data.get('market',''))}\n" if not is_spread else "")
                + f"   → Probability: ~{int(middle_prob*100)}%\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 <b>EXPECTED VALUE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Average EV: +{ev_percent:.1f}%</b>\n"
                f"<b>Avg profit/bet: ${ev_profit:+.2f}</b>\n"
                f"<b>Over 100 middles: ${net_100:+.0f}</b>\n\n"
                f"⚠️ This is NOT arbitrage. Variance applies.\n"
            )
    
    return message
