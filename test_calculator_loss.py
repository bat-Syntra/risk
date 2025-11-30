#!/usr/bin/env python3
"""
Test script pour vérifier que le calculateur affiche les stakes même en cas de perte.
"""

import sys
sys.path.insert(0, '/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot')

from core.calculator import ArbitrageCalculator

# Test case 1: Arbitrage exists (+104 / -123)
print("=" * 60)
print("TEST 1: Arbitrage exists")
print("=" * 60)
odds1 = [-104, -123]
bankroll = 550.0
result = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds1)

print(f"Odds: {odds1}")
print(f"Bankroll: ${bankroll}")
print(f"Has arbitrage: {result['has_arbitrage']}")
print(f"Stakes: ${result['stakes'][0]:.2f} / ${result['stakes'][1]:.2f}")
print(f"Returns: ${result['returns'][0]:.2f} / ${result['returns'][1]:.2f}")
print(f"Profit: ${result['profit']:.2f}")
print(f"ROI: {result['roi_percent']:.2f}%")
print(f"Inverse sum: {result['inverse_sum']}")
print()

# Test case 2: NO arbitrage (+110 / -130) - should still calculate stakes
print("=" * 60)
print("TEST 2: NO arbitrage - but stakes should still be calculated")
print("=" * 60)
odds2 = [110, -130]
result2 = ArbitrageCalculator.calculate_safe_stakes(bankroll, odds2)

print(f"Odds: {odds2}")
print(f"Bankroll: ${bankroll}")
print(f"Has arbitrage: {result2['has_arbitrage']}")
print(f"Stakes: ${result2['stakes'][0]:.2f} / ${result2['stakes'][1]:.2f}")
print(f"Returns: ${result2['returns'][0]:.2f} / ${result2['returns'][1]:.2f}")
print(f"Profit/Loss: ${result2['profit']:.2f}")
print(f"ROI: {result2['roi_percent']:.2f}%")
print(f"Inverse sum: {result2['inverse_sum']}")
print()

# Calculate best return and min loss
if not result2['has_arbitrage']:
    inverse_sum = result2['inverse_sum']
    best_return = bankroll / inverse_sum
    min_loss = abs(result2['profit'])
    print(f"Best guaranteed return: ${best_return:.2f}")
    print(f"Minimum loss: -${min_loss:.2f}")
print()

print("=" * 60)
print("✅ TEST COMPLETED")
print("=" * 60)
