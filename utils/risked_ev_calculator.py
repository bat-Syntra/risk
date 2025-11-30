"""
RISKED EV Calculator
Calculate Expected Value for RISKED mode bets
"""

def american_to_decimal(odds: float) -> float:
    """Convert American odds to decimal odds"""
    if odds > 0:
        return 1 + odds / 100.0
    else:
        return 1 + 100.0 / abs(odds)


def implied_prob_from_american(odds: float) -> float:
    """Calculate implied probability from American odds"""
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return abs(odds) / (abs(odds) + 100.0)


def compute_risked_ev(odds_a: int, stake_a: float, odds_b: int, stake_b: float) -> dict:
    """
    Calculate Expected Value for a RISKED bet configuration
    
    Args:
        odds_a: American odds for side A (e.g., -315)
        stake_a: Stake amount for side A
        odds_b: American odds for side B (e.g., +400)
        stake_b: Stake amount for side B
    
    Returns:
        Dictionary containing:
        - total_stake: Total amount wagered
        - profit_if_a: Profit if side A wins
        - profit_if_b: Profit if side B wins (usually the "jackpot")
        - p_a_fair: Fair probability of A winning (no vig)
        - p_b_fair: Fair probability of B winning (no vig)
        - ev_fair: Expected value in dollars (market-neutral assumption)
        - ev_fair_pct: Expected value as percentage of total stake
        - break_even_p_b: Minimum probability B needs to have +EV
    """
    # 1) Calculate profits for both scenarios
    dec_a = american_to_decimal(odds_a)
    dec_b = american_to_decimal(odds_b)

    total_stake = stake_a + stake_b
    ret_a = stake_a * dec_a
    ret_b = stake_b * dec_b

    profit_a = ret_a - total_stake  # Scenario A wins
    profit_b = ret_b - total_stake  # Scenario B wins (jackpot)

    # 2) Implied probabilities from odds (with vig)
    p_a_raw = implied_prob_from_american(odds_a)
    p_b_raw = implied_prob_from_american(odds_b)

    # 3) Fair probabilities (remove vig by normalizing)
    norm = p_a_raw + p_b_raw
    p_a = p_a_raw / norm
    p_b = p_b_raw / norm

    # 4) Market-neutral Expected Value
    ev = p_a * profit_a + p_b * profit_b
    ev_pct = (ev / total_stake * 100.0) if total_stake > 0 else 0

    # 5) Break-even probability for the "jackpot" side (B)
    # Find minimum p_b where EV = 0
    # EV = p_b × profit_b + (1 - p_b) × profit_a = 0
    # p_b × (profit_b - profit_a) = -profit_a
    # p_b = -profit_a / (profit_b - profit_a)
    be_p_b = None
    if profit_b != profit_a:
        be_p_b = -profit_a / (profit_b - profit_a)
        # Clamp between 0 and 1
        be_p_b = max(0.0, min(1.0, be_p_b))

    return {
        "total_stake": total_stake,
        "profit_if_a": profit_a,
        "profit_if_b": profit_b,
        "p_a_fair": p_a,
        "p_b_fair": p_b,
        "ev_fair": ev,
        "ev_fair_pct": ev_pct,
        "break_even_p_b": be_p_b,
    }
