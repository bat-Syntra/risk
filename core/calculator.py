"""
Arbitrage calculator with SAFE and RISKED modes
Handles American odds format
"""
import enum
from typing import List, Dict, Tuple


class BetMode(enum.Enum):
    """Betting calculation modes"""
    SAFE = "safe"          # Guaranteed profit arbitrage
    RISKED = "risked"      # Intentional imbalance for higher profit potential
    BALANCED = "balanced"  # 50/50 split
    AGGRESSIVE = "aggressive"  # 70/30 split


class ArbitrageCalculator:
    """
    Calculator for arbitrage betting scenarios
    Supports SAFE (guaranteed profit) and RISKED (high risk/reward) modes
    """
    
    @staticmethod
    def american_to_decimal(american_odds: float) -> float:
        """
        Convert American odds to decimal odds
        
        Args:
            american_odds: American format odds (e.g., +250 or -200)
            
        Returns:
            Decimal odds (e.g., 3.50)
        """
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """
        Convert decimal odds to American odds
        
        Args:
            decimal_odds: Decimal format odds (e.g., 3.50)
            
        Returns:
            American odds (e.g., +250 or -200)
        """
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
    
    @staticmethod
    def calculate_implied_probability(american_odds: float) -> float:
        """
        Calculate implied probability from American odds
        
        Args:
            american_odds: American format odds
            
        Returns:
            Implied probability (0-1)
        """
        decimal = ArbitrageCalculator.american_to_decimal(american_odds)
        return 1 / decimal
    
    @staticmethod
    def compute_roi(cashh: float, profit: float) -> Dict[str, float]:
        """
        Compute ROI from total cash engaged and guaranteed profit.
        Returns roi_decimal and roi_percent (rounded to 2 decimals for percent).
        """
        try:
            cash = float(cashh or 0)
            prof = float(profit or 0)
        except Exception:
            return {"roi_decimal": 0.0, "roi_percent": 0.0}
        if cash <= 0:
            return {"roi_decimal": 0.0, "roi_percent": 0.0}
        roi_dec = prof / cash
        return {"roi_decimal": round(roi_dec, 6), "roi_percent": round(roi_dec * 100.0, 2)}
    
    @staticmethod
    def has_arbitrage_opportunity(odds_list: List[float]) -> bool:
        """
        Check if odds provide arbitrage opportunity
        
        Args:
            odds_list: List of American odds
            
        Returns:
            True if arbitrage exists
        """
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        inverse_sum = sum(1 / odd for odd in decimal_odds)
        return inverse_sum < 1.0
    
    @staticmethod
    def calculate_arbitrage_percentage(odds_list: List[float]) -> float:
        """
        Calculate arbitrage percentage
        
        Args:
            odds_list: List of American odds
            
        Returns:
            Arbitrage percentage (e.g., 5.16 for 5.16%)
        """
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        inverse_sum = sum(1 / odd for odd in decimal_odds)
        
        if inverse_sum >= 1.0:
            return 0.0
        
        return ((1 - inverse_sum) / inverse_sum) * 100
    
    @staticmethod
    def calculate_safe_stakes(bankroll: float, odds_list: List[float]) -> Dict:
        """
        Calculate SAFE mode stakes (guaranteed profit arbitrage)
        
        Args:
            bankroll: Total amount to bet
            odds_list: List of American odds for each outcome
            
        Returns:
            Dictionary with stakes, returns, profit, etc.
        """
        # Convert to decimal
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        
        # Calculate inverse sum
        inverse_sum = sum(1 / odd for odd in decimal_odds)
        
        # Check if arbitrage exists
        has_arb = inverse_sum < 1.0
        
        # ALWAYS calculate stakes (even if loss), to show how to minimize loss
        # Calculate stakes for equal profit/loss on all outcomes
        stakes = [(bankroll / inverse_sum) * (1 / decimal_odd) for decimal_odd in decimal_odds]
        
        # Calculate returns for each outcome
        returns = [stakes[i] * decimal_odds[i] for i in range(len(stakes))]
        
        # Profit/Loss is the same for all outcomes
        profit = min(returns) - bankroll
        profit_percentage = (profit / bankroll) * 100 if bankroll > 0 else 0
        roi = ArbitrageCalculator.compute_roi(bankroll, profit)
        arb_percentage = ((1 - inverse_sum) / inverse_sum) * 100
        
        return {
            "mode": "SAFE",
            "has_arbitrage": has_arb,
            "stakes": [round(s, 2) for s in stakes],
            "returns": [round(r, 2) for r in returns],
            "profit": round(profit, 2),
            "profit_percentage": round(profit_percentage, 2),
            "roi_decimal": roi.get("roi_decimal", 0.0),
            "roi_percent": roi.get("roi_percent", 0.0),
            "arb_percentage": round(arb_percentage, 2),
            "risk": 0,
            "guaranteed": True if has_arb else False,
            "inverse_sum": round(inverse_sum, 4),
        }
    
    @staticmethod
    def calculate_risked_stakes(
        bankroll: float,
        odds_list: List[float],
        risk_amount: float = None,
        risk_percentage: float = 5.0,
        favor_outcome: int = 0
    ) -> Dict:
        """
        Calculate RISKED mode stakes (intentional imbalance for higher profit)
        
        Args:
            bankroll: Total amount to bet
            odds_list: List of American odds
            risk_amount: Fixed amount willing to risk (overrides risk_percentage)
            risk_percentage: Percentage of bankroll willing to risk (default 5%)
            favor_outcome: Index of outcome to favor (0 or 1)
            
        Returns:
            Dictionary with stakes, returns, profits for each outcome
        """
        if len(odds_list) != 2:
            return {
                "mode": "RISKED",
                "error": "RISKED mode currently supports only 2-way bets",
            }
        
        # Determine risk amount
        if risk_amount is None:
            risk_amount = bankroll * (risk_percentage / 100)
        
        # Convert to decimal
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        
        # Unfavored outcome should produce loss equal to risk_amount
        unfavored_idx = 1 - favor_outcome
        
        # Calculate stake for unfavored outcome
        # stake_unfavored * odd_unfavored - bankroll = -risk_amount
        # stake_unfavored * odd_unfavored = bankroll - risk_amount
        # stake_unfavored = (bankroll - risk_amount) / odd_unfavored
        stake_unfavored = (bankroll - risk_amount) / decimal_odds[unfavored_idx]
        
        # Rest of bankroll goes to favored outcome
        stake_favored = bankroll - stake_unfavored
        
        # Calculate returns
        stakes = [0, 0]
        stakes[favor_outcome] = stake_favored
        stakes[unfavored_idx] = stake_unfavored
        
        returns = [stakes[i] * decimal_odds[i] for i in range(2)]
        
        # Calculate profits for each outcome
        profits = [returns[i] - bankroll for i in range(2)]
        
        # Max profit and risk
        max_profit = max(profits)
        risk_loss = abs(min(profits))
        
        # Risk/reward ratio
        risk_reward_ratio = max_profit / risk_loss if risk_loss > 0 else 0
        
        return {
            "mode": "RISKED",
            "stakes": [round(s, 2) for s in stakes],
            "returns": [round(r, 2) for r in returns],
            "profits": [round(p, 2) for p in profits],
            "max_profit": round(max_profit, 2),
            "risk_loss": round(risk_loss, 2),
            "favored_outcome": favor_outcome,
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "guaranteed": False,
            "bankroll": bankroll,
        }
    
    @staticmethod
    def calculate_optimal_risk(
        bankroll: float,
        odds_list: List[float],
        max_risk_percentage: float = 5.0
    ) -> Dict:
        """
        Calculate optimal RISKED bet by testing both outcomes
        Returns the one with better risk/reward ratio
        
        Args:
            bankroll: Total bankroll
            odds_list: List of American odds
            max_risk_percentage: Maximum risk as percentage of bankroll
            
        Returns:
            Best RISKED calculation result
        """
        risk_amount = bankroll * (max_risk_percentage / 100)
        
        # Test favoring outcome 0
        result_0 = ArbitrageCalculator.calculate_risked_stakes(
            bankroll, odds_list, risk_amount=risk_amount, favor_outcome=0
        )
        
        # Test favoring outcome 1
        result_1 = ArbitrageCalculator.calculate_risked_stakes(
            bankroll, odds_list, risk_amount=risk_amount, favor_outcome=1
        )
        
        # Return the one with better risk/reward ratio
        if result_0.get("risk_reward_ratio", 0) > result_1.get("risk_reward_ratio", 0):
            result_0["optimal_choice"] = "outcome_0"
            return result_0
        else:
            result_1["optimal_choice"] = "outcome_1"
            return result_1
    
    @staticmethod
    def calculate_balanced(bankroll: float, odds_list: List[float]) -> Dict:
        """
        Calculate balanced 50/50 stake split
        
        Args:
            bankroll: Total bankroll
            odds_list: List of American odds
            
        Returns:
            Balanced calculation result
        """
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        
        stake_per_outcome = bankroll / len(odds_list)
        stakes = [stake_per_outcome] * len(odds_list)
        returns = [stakes[i] * decimal_odds[i] for i in range(len(stakes))]
        profits = [returns[i] - bankroll for i in range(len(returns))]
        
        return {
            "mode": "BALANCED",
            "stakes": [round(s, 2) for s in stakes],
            "returns": [round(r, 2) for r in returns],
            "profits": [round(p, 2) for p in profits],
            "max_profit": round(max(profits), 2),
            "max_loss": round(min(profits), 2),
        }
    
    @staticmethod
    def calculate_aggressive(
        bankroll: float,
        odds_list: List[float],
        favor_percentage: float = 70.0,
        favor_outcome: int = 0
    ) -> Dict:
        """
        Calculate aggressive stake split (e.g., 70/30)
        
        Args:
            bankroll: Total bankroll
            odds_list: List of American odds
            favor_percentage: Percentage to put on favored outcome
            favor_outcome: Which outcome to favor
            
        Returns:
            Aggressive calculation result
        """
        if len(odds_list) != 2:
            return {"mode": "AGGRESSIVE", "error": "Only supports 2-way bets"}
        
        decimal_odds = [ArbitrageCalculator.american_to_decimal(o) for o in odds_list]
        
        stake_favored = bankroll * (favor_percentage / 100)
        stake_unfavored = bankroll - stake_favored
        
        stakes = [0, 0]
        stakes[favor_outcome] = stake_favored
        stakes[1 - favor_outcome] = stake_unfavored
        
        returns = [stakes[i] * decimal_odds[i] for i in range(2)]
        profits = [returns[i] - bankroll for i in range(2)]
        
        return {
            "mode": "AGGRESSIVE",
            "favor_percentage": favor_percentage,
            "favored_outcome": favor_outcome,
            "stakes": [round(s, 2) for s in stakes],
            "returns": [round(r, 2) for r in returns],
            "profits": [round(p, 2) for p in profits],
            "max_profit": round(max(profits), 2),
            "max_loss": round(min(profits), 2),
        }
