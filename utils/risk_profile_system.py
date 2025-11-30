"""
Risk Profile System - Classify parlays by risk level
"""
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class RiskProfile(Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"
    LOTTERY = "LOTTERY"


RISK_PROFILES = {
    RiskProfile.CONSERVATIVE: {
        'name': 'Conservative (Safe Money) 🟢',
        'name_fr': 'Conservateur (Argent Sûr) 🟢',
        'description': 'Low variance, steady profits',
        'description_fr': 'Faible variance, profits réguliers',
        
        'criteria': {
            'source_types_allowed': ['plus_ev', 'arbitrage'],  # NO middles!
            'min_edge': 0.08,  # 8%+ only
            'max_variance': 0.15,
            'max_legs': 2,
            'min_confidence': 0.85,
            'min_quality_score': 75
        },
        
        'expected_performance': {
            'win_rate': '50-55%',
            'avg_roi': '8-12%',
            'volatility': 'Low'
        },
        
        'user_personas': ['Beginners', 'Risk-averse', 'Small bankroll']
    },
    
    RiskProfile.BALANCED: {
        'name': 'Balanced (Smart Plays) 🟡',
        'name_fr': 'Équilibré (Jeux Intelligents) 🟡',
        'description': 'Good edge with manageable risk',
        'description_fr': 'Bon avantage avec risque gérable',
        
        'criteria': {
            'source_types_allowed': ['plus_ev', 'arbitrage', 'middle'],
            'min_edge': 0.12,  # 12%+
            'max_variance': 0.22,
            'max_legs': 3,
            'min_confidence': 0.75,
            'min_quality_score': 65,
            'max_middle_legs': 1  # Max 1 middle leg per parlay
        },
        
        'expected_performance': {
            'win_rate': '42-48%',
            'avg_roi': '15-22%',
            'volatility': 'Medium'
        },
        
        'user_personas': ['Intermediate', 'Standard bankroll', 'Most users']
    },
    
    RiskProfile.AGGRESSIVE: {
        'name': 'Aggressive (Moon Shots) 🟠',
        'name_fr': 'Agressif (Gros Gains) 🟠',
        'description': 'High risk, massive upside',
        'description_fr': 'Risque élevé, potentiel énorme',
        
        'criteria': {
            'source_types_allowed': ['plus_ev', 'arbitrage', 'middle'],
            'min_edge': 0.20,  # 20%+
            'max_variance': 0.40,  # High variance OK
            'max_legs': 4,
            'min_confidence': 0.65,
            'min_quality_score': 55,
            'max_middle_legs': 2,  # Allow 2 middle legs
            'allow_correlated': True  # Seek correlations
        },
        
        'expected_performance': {
            'win_rate': '30-38%',
            'avg_roi': '25-40%',
            'volatility': 'High'
        },
        
        'user_personas': ['Advanced', 'Large bankroll', 'Risk-tolerant']
    },
    
    RiskProfile.LOTTERY: {
        'name': 'Lottery Tickets 🔴🎰',
        'name_fr': 'Billets de Loterie 🔴🎰',
        'description': 'Pure middle parlays - small stake, huge win potential',
        'description_fr': 'Parlays middle purs - petite mise, gains énormes',
        
        'criteria': {
            'source_types_allowed': ['middle'],  # ONLY middles!
            'min_middle_legs': 2,  # At least 2 middle legs
            'max_legs': 3,
            'min_combined_odds': 10.0,  # +900 minimum (10x return)
            'min_middle_hit_probability': 0.10  # 10%+ chance of all middles hitting
        },
        
        'expected_performance': {
            'win_rate': '8-15%',
            'avg_roi': '50-150%',  # When it hits, it HITS
            'volatility': 'Extreme'
        },
        
        'stake_recommendation': '$10-20 max (treat as lottery)',
        
        'user_personas': ['Thrill-seekers', 'Want massive wins']
    }
}


class RiskProfileClassifier:
    """
    Classify parlays into risk profiles and add appropriate metadata
    """
    
    def __init__(self):
        self.profiles = RISK_PROFILES
        
    def classify_parlay(self, parlay: Dict[str, Any], legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify a parlay into risk profiles
        Returns list of profiles that match
        """
        profiles = []
        
        for profile_key, profile_data in self.profiles.items():
            if self.meets_profile(parlay, legs, profile_data['criteria']):
                profiles.append({
                    'profile': profile_key.value,
                    'name': profile_data['name'],
                    'name_fr': profile_data['name_fr'],
                    'description': profile_data['description'],
                    'description_fr': profile_data['description_fr'],
                    'expected_performance': profile_data['expected_performance']
                })
        
        return profiles
    
    def meets_profile(self, parlay: Dict[str, Any], legs: List[Dict[str, Any]], criteria: Dict[str, Any]) -> bool:
        """
        Check if parlay meets profile criteria
        """
        # Check source types
        if 'source_types_allowed' in criteria:
            all_allowed = all(
                leg.get('source_type', 'plus_ev') in criteria['source_types_allowed']
                for leg in legs
            )
            if not all_allowed:
                return False
        
        # Check middle legs count
        middle_count = sum(1 for leg in legs if leg.get('source_type') == 'middle')
        
        if 'max_middle_legs' in criteria and middle_count > criteria['max_middle_legs']:
            return False
        
        if 'min_middle_legs' in criteria and middle_count < criteria['min_middle_legs']:
            return False
        
        # Check edge
        if 'min_edge' in criteria and parlay.get('calculated_edge', 0) < criteria['min_edge']:
            return False
        
        # Check variance
        if 'max_variance' in criteria and parlay.get('variance_score', 0) > criteria['max_variance']:
            return False
        
        # Check legs count
        leg_count = len(legs)
        if 'max_legs' in criteria and leg_count > criteria['max_legs']:
            return False
        
        # Check quality score
        if 'min_quality_score' in criteria and parlay.get('quality_score', 0) < criteria['min_quality_score']:
            return False
        
        # Check combined odds (for lottery)
        if 'min_combined_odds' in criteria:
            combined_odds = parlay.get('combined_decimal_odds', 0)
            if combined_odds < criteria['min_combined_odds']:
                return False
        
        return True
    
    def add_risk_profiles(self, parlay: Dict[str, Any], legs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add risk profile information to parlay
        """
        profiles = self.classify_parlay(parlay, legs)
        
        # Find primary profile (most conservative that matches)
        profile_order = [
            RiskProfile.CONSERVATIVE,
            RiskProfile.BALANCED,
            RiskProfile.AGGRESSIVE,
            RiskProfile.LOTTERY
        ]
        
        primary_profile = None
        for profile in profile_order:
            if any(p['profile'] == profile.value for p in profiles):
                primary_profile = profile
                break
        
        if primary_profile is None:
            primary_profile = RiskProfile.BALANCED  # Default
        
        return {
            **parlay,
            'risk_profile': primary_profile.value,
            'risk_profiles_matched': profiles,
            'risk_label': self.get_risk_label(primary_profile),
            'stake_guidance': self.get_stake_guidance(primary_profile)
        }
    
    def get_risk_label(self, profile: RiskProfile) -> str:
        """Get emoji label for risk profile"""
        labels = {
            RiskProfile.CONSERVATIVE: '🟢 Low Risk',
            RiskProfile.BALANCED: '🟡 Medium Risk',
            RiskProfile.AGGRESSIVE: '🟠 High Risk',
            RiskProfile.LOTTERY: '🔴 Lottery Ticket'
        }
        return labels.get(profile, '🟡 Medium Risk')
    
    def get_stake_guidance(self, profile: RiskProfile) -> str:
        """Get stake recommendation for profile"""
        guidance = {
            RiskProfile.CONSERVATIVE: '2-3% of bankroll',
            RiskProfile.BALANCED: '1-2% of bankroll',
            RiskProfile.AGGRESSIVE: '0.5-1% of bankroll',
            RiskProfile.LOTTERY: '$10-20 flat (entertainment only)'
        }
        return guidance.get(profile, '1-2% of bankroll')
    
    def calculate_variance_score(self, legs: List[Dict[str, Any]]) -> float:
        """
        Calculate variance score for parlay
        Higher = more volatile
        """
        if not legs:
            return 0
        
        # Factors that increase variance:
        # - More legs
        # - Middle bets
        # - High odds
        # - Low confidence
        
        variance = 0.0
        
        # Base variance from number of legs
        variance += len(legs) * 0.05
        
        # Middle bets add more variance
        middle_count = sum(1 for leg in legs if leg.get('source_type') == 'middle')
        variance += middle_count * 0.10
        
        # High odds add variance
        for leg in legs:
            odds = leg.get('decimal_odds', 2.0)
            if odds > 3.0:
                variance += 0.05
            if odds > 5.0:
                variance += 0.10
        
        return min(variance, 1.0)  # Cap at 1.0
    
    def filter_parlays_by_profile(self, parlays: List[Dict[str, Any]], 
                                 allowed_profiles: List[str]) -> List[Dict[str, Any]]:
        """
        Filter parlays to only include specified risk profiles
        """
        return [
            p for p in parlays 
            if p.get('risk_profile') in allowed_profiles
        ]
    
    def get_profile_summary(self, parlays: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get count of parlays by risk profile
        """
        summary = {
            RiskProfile.CONSERVATIVE.value: 0,
            RiskProfile.BALANCED.value: 0,
            RiskProfile.AGGRESSIVE.value: 0,
            RiskProfile.LOTTERY.value: 0
        }
        
        for parlay in parlays:
            profile = parlay.get('risk_profile', RiskProfile.BALANCED.value)
            if profile in summary:
                summary[profile] += 1
        
        return summary
