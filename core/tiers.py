"""
Tier management system
FREE and PREMIUM tiers
"""
import enum
from typing import Dict, Any
from datetime import datetime, timedelta


class TierLevel(enum.Enum):
    """User subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"


# Tier pricing (monthly, in CAD)
TIER_PRICING = {
    TierLevel.FREE: 0,
    TierLevel.PREMIUM: 200,
}


# Feature configuration for each tier
TIER_FEATURES = {
    TierLevel.FREE: {
        "delay_minutes": 15,              # 15 minutes initial delay after /start
        "max_alerts_per_day": 5,          # 5 calls per day MAX
        "max_arb_percentage": 2.5,        # Only 2.5% or below (NEVER above)
        "min_spacing_minutes": 105,       # 1h45 (105 minutes) between calls
        "show_risked_bets": False,        # No RISKED mode
        "show_calculator": False,         # No custom calculator
        "referral_links": False,          # No referral links to casinos
        "show_stats": False,              # No detailed stats
        "priority_alerts": False,         # No priority
        "custom_risk_settings": False,    # No custom risk
        "support_priority": "low",        # Low priority support
        "can_receive_middle": False,      # NEVER receive Middle alerts
        "can_receive_good_ev": False,     # NEVER receive Good EV alerts
    },
    TierLevel.PREMIUM: {
        "delay_minutes": 0,               # Real-time alerts
        "max_alerts_per_day": 999,        # Unlimited alerts
        "min_arb_percentage": 0,          # See ALL arbs (no minimum)
        "show_risked_bets": True,         # RISKED mode available
        "show_calculator": True,          # Custom calculator
        "referral_links": True,           # Referral links included
        "show_stats": True,               # Advanced stats
        "priority_alerts": True,          # Priority alerts
        "custom_risk_settings": True,     # Custom risk settings
        "support_priority": "vip",        # VIP support
        "historical_data": True,          # Historical data
        "webhook_notifications": True,    # Webhook notifications
        "referral_bonus": 2.0,            # 2x referral commission
        "can_receive_middle": True,       # Can receive Middle alerts
        "can_receive_good_ev": True,      # Can receive Good EV alerts
    },
}


class TierManager:
    """Manages tier features and permissions"""
    
    @staticmethod
    def get_features(tier: TierLevel) -> Dict[str, Any]:
        """
        Get all features for a given tier
        
        Args:
            tier: TierLevel enum
            
        Returns:
            Dictionary of features
        """
        return TIER_FEATURES.get(tier, TIER_FEATURES[TierLevel.FREE])
    
    @staticmethod
    def get_price(tier: TierLevel) -> float:
        """
        Get monthly price for a tier
        
        Args:
            tier: TierLevel enum
            
        Returns:
            Monthly price in USD
        """
        return TIER_PRICING.get(tier, 0)
    
    @staticmethod
    def can_view_alert(tier: TierLevel, arb_percentage: float) -> bool:
        """
        Check if user can view an alert based on tier and arb percentage
        
        Args:
            tier: User's tier level
            arb_percentage: Arbitrage percentage of the alert
            
        Returns:
            True if user can view this alert
        """
        features = TierManager.get_features(tier)
        # Support either a max threshold (e.g., FREE <= 2.5%) or a min threshold (e.g., PREMIUM >= 0.5%)
        max_arb = features.get("max_arb_percentage")
        min_arb = features.get("min_arb_percentage")
        if max_arb is not None:
            return arb_percentage <= float(max_arb)
        if min_arb is not None:
            return arb_percentage >= float(min_arb)
        # Default: allow all positive arbitrage
        return arb_percentage > 0
    
    @staticmethod
    def get_alert_delay(tier: TierLevel) -> int:
        """
        Get alert delay in minutes for a tier
        
        Args:
            tier: TierLevel enum
            
        Returns:
            Delay in minutes
        """
        features = TierManager.get_features(tier)
        return features.get("delay_minutes", 30)
    
    @staticmethod
    def can_receive_alert_today(tier: TierLevel, alerts_today: int) -> bool:
        """
        Check if user can receive another alert today
        
        Args:
            tier: User's tier
            alerts_today: Number of alerts already received today
            
        Returns:
            True if can receive more alerts
        """
        features = TierManager.get_features(tier)
        max_alerts = features.get("max_alerts_per_day", 5)
        return alerts_today < max_alerts
    
    @staticmethod
    def has_feature(tier: TierLevel, feature_name: str) -> bool:
        """
        Check if tier has a specific feature
        
        Args:
            tier: User's tier
            feature_name: Name of the feature to check
            
        Returns:
            True if feature is available
        """
        features = TierManager.get_features(tier)
        return features.get(feature_name, False)
    
    @staticmethod
    def get_tier_description(tier: TierLevel) -> str:
        """
        Get human-readable description of tier
        
        Args:
            tier: TierLevel enum
            
        Returns:
            Description string
        """
        descriptions = {
            TierLevel.FREE: "🆓 FREE - 2 alertes/jour avec arbitrages &lt; 2.5%",
            TierLevel.PREMIUM: "🔥 PREMIUM - Alertes illimitées + toutes les fonctionnalités",
        }
        return descriptions.get(tier, "Unknown tier")
    
    @staticmethod
    def get_upgrade_benefits(current_tier: TierLevel, target_tier: TierLevel) -> list:
        """
        Get list of benefits when upgrading from current to target tier
        
        Args:
            current_tier: Current tier
            target_tier: Target tier
            
        Returns:
            List of new benefits
        """
        current_features = TierManager.get_features(current_tier)
        target_features = TierManager.get_features(target_tier)
        
        benefits = []
        
        # Check delay improvement
        if target_features["delay_minutes"] < current_features["delay_minutes"]:
            benefits.append("⚡ Alertes temps réel (0 délai)")
        
        # Check alerts limit
        if target_features["max_alerts_per_day"] > current_features["max_alerts_per_day"]:
            benefits.append("♾️ Alertes illimitées")
        
        # Check arb percentage
        if target_features["min_arb_percentage"] < current_features["min_arb_percentage"]:
            benefits.append(f"📊 Arbitrages à partir de {target_features['min_arb_percentage']}%")
        
        # Check new features
        for feature, enabled in target_features.items():
            if enabled and not current_features.get(feature, False):
                feature_names = {
                    "show_risked_bets": "⚠️ Mode RISKED (high risk/reward)",
                    "show_calculator": "🧮 Calculateur de stakes",
                    "referral_links": "🔗 Liens referral casinos",
                    "show_stats": "📈 Statistiques détaillées",
                    "priority_alerts": "🚀 Alertes prioritaires",
                    "custom_risk_settings": "⚙️ Settings de risk custom",
                    "api_access": "🔌 Accès API",
                    "historical_data": "📚 Données historiques",
                    "webhook_notifications": "🔔 Notifications webhook",
                }
                if feature in feature_names:
                    benefits.append(feature_names[feature])
        
        return benefits
    
    @staticmethod
    def calculate_subscription_end(tier: TierLevel, months: int = 1) -> datetime:
        """
        Calculate subscription end date
        
        Args:
            tier: Tier being subscribed to
            months: Number of months (default 1)
            
        Returns:
            Subscription end datetime
        """
        if tier == TierLevel.FREE:
            return None
        
        return datetime.now() + timedelta(days=30 * months)
    
    @staticmethod
    def is_upgrade(current_tier: TierLevel, new_tier: TierLevel) -> bool:
        """
        Check if changing to new tier is an upgrade
        
        Args:
            current_tier: Current tier
            new_tier: New tier
            
        Returns:
            True if it's an upgrade
        """
        tier_order = [TierLevel.FREE, TierLevel.PREMIUM]
        current_idx = tier_order.index(current_tier)
        new_idx = tier_order.index(new_tier)
        return new_idx > current_idx
    
    @staticmethod
    def format_tier_comparison() -> str:
        """
        Generate comparison table of all tiers
        
        Returns:
            Formatted comparison string
        """
        comparison = "💎 <b>PLANS DISPONIBLES</b>\n\n"
        
        comparison += "<b>🆓 FREE</b> - Gratuit\n"
        comparison += "  • 2 alertes/jour\n"
        comparison += "  • Arbitrages &lt; 2.5%\n"
        comparison += "  • Temps réel\n\n"
        
        comparison += "<b>🔥 PREMIUM</b> - 200 CAD/mois\n"
        comparison += "  • Alertes illimitées\n"
        comparison += "  • Tous les arbitrages (≥0.5%)\n"
        comparison += "  • Mode RISKED\n"
        comparison += "  • Calculateur personnalisé\n"
        comparison += "  • Stats avancées\n"
        comparison += "  • Support VIP\n"
        comparison += "  • Bonus referral x2\n"
        
        return comparison
