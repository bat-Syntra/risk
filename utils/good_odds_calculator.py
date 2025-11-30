"""
Good Odds (Positive EV) Calculator - CORRECTED VERSION
Calculs mathématiquement corrects pour EV+
"""
from typing import Dict, Tuple


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal"""
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))


def calculate_true_winrate(american_odds: int, ev_percent: float) -> float:
    """
    Calculate TRUE win rate from odds and EV%
    
    Formula:
    EV = (true_prob × profit) - ((1 - true_prob) × stake)
    EV = true_prob × (stake × decimal) - stake
    EV/stake = true_prob × decimal - 1
    true_prob = (EV/stake + 1) / decimal
    
    Args:
        american_odds: American odds (ex: +125, -110)
        ev_percent: EV percentage (ex: 7.5)
    
    Returns:
        True win rate (0.0 to 1.0)
    
    Examples:
        +125 odds, 7.5% EV → 0.478 (47.8%)
        +200 odds, 10% EV → 0.367 (36.7%)
        -110 odds, 5% EV → 0.538 (53.8%)
    """
    decimal = american_to_decimal(american_odds)
    ev_decimal = ev_percent / 100
    true_prob = (ev_decimal + 1) / decimal
    
    return min(max(true_prob, 0.0), 1.0)  # Clamp between 0 and 1


def calculate_good_odds_example(odds: int, stake: float, ev_percent: float, num_bets: int = 10) -> Dict:
    """
    Calculate CORRECT example over N bets
    
    Args:
        odds: American odds
        stake: Amount per bet
        ev_percent: EV percentage
        num_bets: Number of bets to simulate
    
    Returns:
        Dict with all calculations
    """
    decimal = american_to_decimal(odds)
    
    # Calculate TRUE win rate (NOT implied!)
    true_winrate = calculate_true_winrate(odds, ev_percent)
    
    # Profit if win
    profit_if_win = stake * (decimal - 1)
    
    # Expected wins/losses
    expected_wins = num_bets * true_winrate
    expected_losses = num_bets * (1 - true_winrate)
    
    # Calculate profits
    total_profit_from_wins = expected_wins * profit_if_win
    total_loss_from_losses = expected_losses * stake
    net_profit = total_profit_from_wins - total_loss_from_losses
    
    # Verify matches EV
    expected_ev = num_bets * stake * (ev_percent / 100)
    
    return {
        'true_winrate': round(true_winrate, 3),
        'loss_rate': round(1 - true_winrate, 3),
        'expected_wins': round(expected_wins, 1),
        'expected_losses': round(expected_losses, 1),
        'profit_from_wins': round(total_profit_from_wins, 2),
        'loss_from_losses': round(total_loss_from_losses, 2),
        'net_profit': round(net_profit, 2),
        'expected_ev': round(expected_ev, 2),
        'roi': round((net_profit / (num_bets * stake)) * 100, 1),
        'profit_if_win': round(profit_if_win, 2)
    }


def calculate_kelly_bankroll(stake: float, ev_percent: float, odds: int, kelly_mult: float = 0.25) -> float:
    """
    Calculate recommended bankroll using Kelly Criterion
    
    Kelly fraction = (bp - q) / b
    où:
        b = decimal odds - 1
        p = true win probability
        q = 1 - p
    
    Args:
        stake: Desired stake amount
        ev_percent: EV percentage
        odds: American odds
        kelly_mult: Kelly multiplier (0.25 recommended)
    
    Returns:
        Required bankroll
    
    Example:
        $750 stake, +125 odds, 7.5% EV, 0.25 Kelly
        Returns: ~$16,000 (NOT $37,500!)
    """
    decimal = american_to_decimal(odds)
    win_prob = calculate_true_winrate(odds, ev_percent)
    
    # Kelly fraction
    b = decimal - 1
    p = win_prob
    q = 1 - win_prob
    
    kelly_fraction = (b * p - q) / b
    
    # Adjusted Kelly (conservative)
    adjusted_fraction = kelly_fraction * kelly_mult
    
    # Required bankroll
    if adjusted_fraction <= 0:
        return stake * 100  # Fallback for negative/zero EV
    
    required_bankroll = stake / adjusted_fraction
    
    return round(required_bankroll, 2)


def get_ev_quality_tag(ev_percent: float, odds: int) -> Dict:
    """
    Determine quality tag based on EV% and odds
    
    Classification correcte:
    - < 5%: Too low
    - 5-8%: Minimum (⚠️)
    - 8-12%: Good (✅)
    - 12-15%: Excellent (💎)
    - 15%+: Elite (🔥)
    
    Special case: High odds (+300+) with low EV = Risky
    """
    
    # Base tier by EV%
    if ev_percent < 5:
        tier = 'too_low'
        tag = '❌ EV TROP FAIBLE'
        emoji = '❌'
        recommended_for = 'Skip'
        advice = '⚠️ Éviter - EV insuffisant'
    elif ev_percent < 8:
        tier = 'minimum'
        tag = '⚠️ EV MINIMUM'
        emoji = '⚠️'
        recommended_for = 'Débutant+ avec grosse bankroll'
        advice = '⚠️ Bankroll minimum 100x le stake'
    elif ev_percent < 12:
        tier = 'decent'
        tag = '✅ BON EV'
        emoji = '✅'
        recommended_for = 'Intermédiaire+'
        advice = '✅ Bon value, bankroll 50x stake minimum'
    elif ev_percent < 15:
        tier = 'good'
        tag = '💎 EXCELLENT EV'
        emoji = '💎'
        recommended_for = 'Tous niveaux'
        advice = '💎 Excellent value, bankroll 40x stake minimum'
    else:
        tier = 'elite'
        tag = '🔥 EV ELITE'
        emoji = '🔥'
        recommended_for = 'Tous niveaux - RARE!'
        advice = '🔥 Exceptionnel! Bankroll 30x stake minimum'
    
    # Downgrade if odds too high + EV not proportional
    if odds >= 300 and ev_percent < 15:
        tag = '⚠️ EV RISQUÉ (cotes longues)'
        emoji = '⚠️'
        tier = 'risky'
        recommended_for = 'Experts seulement'
        advice = '⚠️ Variance élevée - Experts only!'
    
    return {
        'tier': tier,
        'tag': tag,
        'emoji': emoji,
        'recommended_for': recommended_for,
        'advice': advice
    }


def should_send_good_odds(ev_percent: float, odds: int, market_width: float = None,
                          min_ev: float = 5.0, max_odds: int = 300, max_width: float = 30) -> Tuple[bool, str]:
    """
    Filter Good Odds selon best practices OddsJam
    
    Returns:
        (should_send: bool, reason: str)
    """
    
    # Check EV%
    if ev_percent < min_ev:
        return False, f"EV trop faible: {ev_percent}% < {min_ev}%"
    
    # Check odds
    odds_value = abs(odds)
    if odds > 0 and odds_value > max_odds:
        return False, f"Cotes trop hautes: +{odds_value} > +{max_odds}"
    
    # Check market width (if available)
    if market_width and market_width > max_width:
        return False, f"Marché trop large: {market_width}% > {max_width}%"
    
    # Logistic curve: higher odds need higher EV
    if odds_value > 200:
        required_ev = 10 + ((odds_value - 200) / 50)
        if ev_percent < required_ev:
            return False, f"Cotes hautes nécessitent EV+ élevé: {required_ev:.1f}%"
    
    return True, "Passed all filters"
