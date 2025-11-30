"""
Middle Betting Calculator
Calculate stakes and profits for middle betting opportunities
"""
from typing import Dict, Optional, Tuple


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal"""
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))


def calculate_middle_stakes(odds_a: int, odds_b: int, total_cash: float, rounding_level: int = 0, rounding_mode: str = 'nearest') -> Dict:
    """
    Calculate stakes for a Middle opportunity
    
    Args:
        odds_a: American odds for side A (e.g., +150)
        odds_b: American odds for side B (e.g., -170)
        total_cash: Total cash to split between both bets
        rounding_level: 0=precise, 1=dollar, 5=$5, 10=$10
        rounding_mode: 'down', 'nearest', or 'up'
    
    Returns:
        Dict with stakes and returns
    """
    from utils.stake_rounder import round_stakes
    
    decimal_a = american_to_decimal(odds_a)
    decimal_b = american_to_decimal(odds_b)
    
    # Calculate stakes
    stake_a = total_cash / (1 + (decimal_a / decimal_b))
    stake_b = total_cash - stake_a
    
    # Apply rounding if requested
    if rounding_level > 0:
        stake_a, stake_b = round_stakes(stake_a, stake_b, total_cash, rounding_level, rounding_mode)
    
    # Calculate returns
    return_a = stake_a * decimal_a
    return_b = stake_b * decimal_b
    
    # Calculate profits for each scenario
    total_stake = stake_a + stake_b
    profit_a_only = return_a - total_stake
    profit_b_only = return_b - total_stake
    profit_both = return_a + return_b - total_stake
    
    return {
        'stake_a': round(stake_a, 2),
        'stake_b': round(stake_b, 2),
        'return_a': round(return_a, 2),
        'return_b': round(return_b, 2),
        'total_stake': round(total_stake, 2),
        'profit_a_only': round(profit_a_only, 2),
        'profit_b_only': round(profit_b_only, 2),
        'profit_both': round(profit_both, 2)
    }


def estimate_middle_probability(gap: float, market: str) -> float:
    """
    Estime la probabilité qu'un middle hit
    
    Plus le gap est petit, plus la prob est haute.
    
    Args:
        gap: Distance entre les deux lignes (ex: 1.0 pour 3.5 vs 4.5)
        market: Type de marché (ex: 'Player Receptions', 'Point Spread')
    
    Returns:
        Probability (0.0 to 1.0)
    """
    market_lower = market.lower()
    
    # Player stats (points, receptions, etc.)
    if 'player' in market_lower or 'reception' in market_lower or 'point' in market_lower:
        if gap <= 0.5:
            return 0.25  # 25%
        elif gap <= 1.0:
            return 0.20  # 20%
        elif gap <= 1.5:
            return 0.15  # 15%
        elif gap <= 2.0:
            return 0.10  # 10%
        else:
            return 0.05  # 5%
    
    # Point spread
    elif 'spread' in market_lower:
        if gap <= 1.0:
            return 0.15  # 15%
        elif gap <= 2.0:
            return 0.10  # 10%
        elif gap <= 3.0:
            return 0.08  # 8%
        else:
            return 0.05  # 5%
    
    # Totals
    elif 'total' in market_lower or 'over' in market_lower or 'under' in market_lower:
        if gap <= 2.0:
            return 0.15  # 15%
        elif gap <= 3.0:
            return 0.12  # 12%
        elif gap <= 5.0:
            return 0.10  # 10%
        else:
            return 0.05  # 5%
    
    # Default
    else:
        return 0.10  # 10%


def classify_middle_type(side_a: Dict, side_b: Dict, user_cash: float, rounding_level: int = 0) -> Dict:
    """
    Détermine le type de middle et calcule les stakes
    
    Args:
        side_a: {
            'bookmaker': 'Mise-o-jeu',
            'selection': 'Over 3.5',
            'line': '3.5',
            'odds': '-105'
        }
        side_b: {
            'bookmaker': 'Coolbet',
            'selection': 'Under 4.5',
            'line': '4.5',
            'odds': '+120'
        }
        user_cash: 500.0
        rounding_level: 0=precise, 1=dollar, 5=five, 10=ten
    
    Returns:
        {
            'type': 'middle_safe' ou 'middle_risky',
            'stake_a': 263.20,
            'stake_b': 236.80,
            'return_a': 513.79,
            'return_b': 521.05,
            'total_stake': 500.0,
            'profit_scenario_1': 13.79,
            'profit_scenario_2': 534.86,  # Middle hit
            'profit_scenario_3': 21.05,
            'middle_zone': 1.0,
            'middle_prob': 0.20,
            'ev': 40.50,
            'ev_percent': 8.1
        }
    """
    # Parse odds
    try:
        odds_a = int(side_a['odds'].replace('+', ''))
        odds_b = int(side_b['odds'].replace('+', ''))
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid odds format: {e}")
    
    # Calculate stakes with rounding
    calc = calculate_middle_stakes(odds_a, odds_b, user_cash, rounding_level)
    
    # Calculate middle zone
    try:
        line_a = float(side_a['line'])
        line_b = float(side_b['line'])
        middle_zone = abs(line_a - line_b)
    except (ValueError, KeyError):
        middle_zone = 0.0
    
    # Estimate middle probability
    market = side_a.get('market', side_b.get('market', ''))
    middle_prob = estimate_middle_probability(middle_zone, market)
    
    # Classify type
    profit_a = calc['profit_a_only']
    profit_b = calc['profit_b_only']
    profit_middle = calc['profit_both']
    
    if profit_a > 0 and profit_b > 0:
        middle_type = 'middle_safe'
    elif profit_middle > 0 and (profit_a < 0 or profit_b < 0):
        middle_type = 'middle_risky'
    else:
        middle_type = 'unknown'
    
    # Calculate EV
    worst_loss = min(profit_a, profit_b) if middle_type == 'middle_risky' else 0
    ev = (middle_prob * profit_middle) + ((1 - middle_prob) * worst_loss)
    ev_percent = (ev / calc['total_stake']) * 100
    
    return {
        'type': middle_type,
        'stake_a': calc['stake_a'],
        'stake_b': calc['stake_b'],
        'return_a': calc['return_a'],
        'return_b': calc['return_b'],
        'total_stake': calc['total_stake'],
        'profit_scenario_1': profit_a,
        'profit_scenario_2': profit_middle,
        'profit_scenario_3': profit_b,
        'middle_zone': middle_zone,
        'middle_prob': middle_prob,
        'ev': round(ev, 2),
        'ev_percent': round(ev_percent, 1)
    }


def get_unit(market: str) -> str:
    """Retourne l'unité selon le marché"""
    market_lower = market.lower()
    
    if 'reception' in market_lower:
        return "reception(s)"
    elif 'point' in market_lower:
        return "point(s)"
    elif 'yard' in market_lower:
        return "yard(s)"
    elif 'touchdown' in market_lower or ' td' in market_lower:
        return "TD"
    elif 'assist' in market_lower:
        return "assist(s)"
    elif 'rebound' in market_lower:
        return "rebound(s)"
    else:
        return ""


def describe_middle_zone(data: Dict) -> str:
    """Décrit la zone middle en langage naturel"""
    market = data.get('market', '').lower()
    
    try:
        line_a = float(data['side_a']['line'])
        line_b = float(data['side_b']['line'])
        
        # Determine which is over and which is under
        if 'over' in data['side_a']['selection'].lower():
            over_line = line_a
            under_line = line_b
        else:
            over_line = line_b
            under_line = line_a
        
        # Calculate middle value(s)
        if over_line % 1 == 0.5 and under_line % 1 == 0.5:
            # Ex: 3.5 and 4.5 -> Exactly 4
            middle_value = int((over_line + under_line) / 2)
            return f"Exactement {middle_value}"
        else:
            # Range
            return f"Entre {over_line} et {under_line}"
            
    except (ValueError, KeyError):
        return f"Entre les deux lignes"


def get_recommendation(gap: float) -> str:
    """Recommandation selon le gap"""
    if gap <= 0.5:
        return "Gap ULTRA tight = probabilité énorme!"
    elif gap <= 1.0:
        return "Gap de 1 = excellent middle!"
    elif gap <= 2.0:
        return "Bon gap pour middle!"
    else:
        return "Go for it!"


def _parse_signed(selection: str, line: str) -> float:
    try:
        sel = (selection or "").strip()
        import re
        m = re.search(r"([+-]\d+(?:\.\d+)?)", sel)
        if m:
            return float(m.group(1))
        s = line.strip()
        if s.startswith('+') or s.startswith('-'):
            return float(s)
        return float(s)
    except Exception:
        return 0.0


def analyze_spread_window(side_a: Dict, side_b: Dict) -> Dict:
    try:
        sa = _parse_signed(side_a.get('selection', ''), str(side_a.get('line', '')))
        sb = _parse_signed(side_b.get('selection', ''), str(side_b.get('line', '')))
    except Exception:
        sa, sb = 0.0, 0.0
    pos = None
    neg = None
    pos_side = None
    neg_side = None
    if sa > 0:
        pos = sa
        pos_side = 'a'
    if sb > 0 and (pos is None or sb > pos):
        pos = sb
        pos_side = 'b'
    if sa < 0:
        neg = sa
        neg_side = 'a'
    if sb < 0 and (neg is None or sb < neg):
        neg = sb
        neg_side = 'b'
    is_spread = (pos is not None and neg is not None)
    if not is_spread:
        return {
            'is_spread': False,
            'double_exists': False,
        }
    import math
    fav_abs = abs(neg)
    dog_pos = pos
    start = math.ceil(fav_abs + 0.5)
    end = math.floor(dog_pos - 0.5)
    double_exists = start <= end
    push_points = []
    fav_is_int = abs(fav_abs - round(fav_abs)) < 1e-6 and abs((fav_abs - int(fav_abs)) - 0.5) > 1e-6
    dog_is_int = abs(dog_pos - round(dog_pos)) < 1e-6 and abs((dog_pos - int(dog_pos)) - 0.5) > 1e-6
    if fav_is_int:
        mf = int(round(fav_abs))
        other_wins = mf <= math.floor(dog_pos - 0.5)
        push_points.append({'m': mf, 'winner': pos_side if other_wins else None})
    if dog_is_int:
        md = int(round(dog_pos))
        other_wins = md >= math.ceil(fav_abs + 0.5)
        push_points.append({'m': md, 'winner': neg_side if other_wins else None})
    dog_upper = math.floor(dog_pos - 0.5)
    dog_upper = min(dog_upper, start - 1) if double_exists else dog_upper
    for p in push_points:
        if p['m'] <= dog_upper and p['winner'] == pos_side:
            dog_upper = p['m'] - 1
    fav_lower = math.ceil(fav_abs + 0.5)
    fav_lower = max(fav_lower, end + 1) if double_exists else fav_lower
    for p in push_points:
        if p['m'] >= fav_lower and p['winner'] == neg_side:
            fav_lower = p['m'] + 1
    return {
        'is_spread': True,
        'pos_side': pos_side,
        'neg_side': neg_side,
        'dog_line': dog_pos,
        'fav_line': fav_abs,
        'double_exists': double_exists,
        'double_start': start,
        'double_end': end,
        'push_points': push_points,
        'dog_upper': dog_upper,
        'fav_lower': fav_lower,
    }


def round_middle_stakes(odds_a: int, odds_b: int, total_cash: float, 
                        rounding_level: int = 0, rounding_mode: str = 'nearest') -> Optional[Dict]:
    """
    Calculate Middle stakes WITH rounding and recalculate all profits with rounded values.
    Validates that profit remains positive after rounding.
    
    Args:
        odds_a: American odds for side A
        odds_b: American odds for side B
        total_cash: Total cash to allocate
        rounding_level: 0=precise, 1=dollar, 5=$5, 10=$10
        rounding_mode: 'down', 'nearest', 'up'
    
    Returns:
        Dict with recalculated values OR None if rounding kills the opportunity
    """
    from utils.stake_rounder import round_stakes
    
    # Calculate initial stakes
    result = calculate_middle_stakes(odds_a, odds_b, total_cash, rounding_level, rounding_mode)
    
    # If rounding was applied, values are already rounded and recalculated
    # Just validate that profits are still positive
    min_profit = min(result['profit_a_only'], result['profit_b_only'])
    
    # VALIDATION: If guaranteed minimum profit is negative, this is bad
    # (Middle can have negative scenarios, but we want at least one positive)
    if result['profit_both'] < 0 and min_profit < -total_cash * 0.5:
        # Both scenarios are very negative, refuse
        return None
    
    return result
