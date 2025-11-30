def american_to_decimal(american: float) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))


def compute_allocations(odds_over: float, odds_under: float, bankroll: float):
    dA, dB = american_to_decimal(odds_over), american_to_decimal(odds_under)
    s = (1 / dA + 1 / dB)

    # Safe = arbitrage payout égalisé
    xA = bankroll * (1 / dA) / s
    xB = bankroll * (1 / dB) / s
    payout = xA * dA
    profit = payout - bankroll

    # Balanced = 50/50
    bal_xA = bal_xB = bankroll / 2
    bal_profit_winA = bal_xA * (dA - 1) - bal_xB
    bal_profit_winB = bal_xB * (dB - 1) - bal_xA

    # Aggressive = 70/30
    agg_xA, agg_xB = bankroll * 0.7, bankroll * 0.3
    agg_profit_winA = agg_xA * (dA - 1) - agg_xB
    agg_profit_winB = agg_xB * (dB - 1) - agg_xA

    return {
        "safe": {"over": xA, "under": xB, "profit": profit},
        "balanced": {
            "over": bal_xA, "under": bal_xB,
            "win_over": bal_profit_winA, "win_under": bal_profit_winB,
        },
        "aggressive": {
            "over": agg_xA, "under": agg_xB,
            "win_over": agg_profit_winA, "win_under": agg_profit_winB,
        },
    }
