"""
EV Quality System - Tags and recommendations for Good Odds alerts
"""
from typing import Dict

# Configuration
SYSTEM_MIN_EV = 0.5  # Minimum system threshold - user filters control the actual minimum

# Recommended minimums by user profile
RECOMMENDED_MIN_EV = {
    'beginner': 12.0,      # <100 bets total
    'intermediate': 8.0,   # 100-500 bets
    'advanced': 5.0        # 500+ bets
}

# Quality tiers with visual tags
EV_QUALITY_TIERS = {
    'very_risky': {
        'range': (0.5, 5.0),
        'tag_fr': '🔴 EV TRÈS RISQUÉ',
        'tag_en': '🔴 VERY RISKY EV',
        'emoji': '🔴',
        'advice_fr': 'Stakes très petits. Variance très élevée.',
        'advice_en': 'Very small stakes. Very high variance.',
        'recommended_for_fr': 'Expert seulement',
        'recommended_for_en': 'Expert only'
    },
    'risky': {
        'range': (5.0, 8.0),
        'tag_fr': '⚠️ EV RISQUÉ',
        'tag_en': '⚠️ RISKY EV',
        'emoji': '⚠️',
        'advice_fr': 'Petits stakes recommandés. Variance élevée.',
        'advice_en': 'Small stakes recommended. High variance.',
        'recommended_for_fr': 'Avancé seulement',
        'recommended_for_en': 'Advanced only'
    },
    'decent': {
        'range': (8.0, 12.0),
        'tag_fr': '✅ EV CORRECT',
        'tag_en': '✅ DECENT EV',
        'emoji': '✅',
        'advice_fr': 'Bon bet pour expérimentés.',
        'advice_en': 'Good bet for experienced users.',
        'recommended_for_fr': 'Intermédiaire/Avancé',
        'recommended_for_en': 'Intermediate/Advanced'
    },
    'good': {
        'range': (12.0, 18.0),
        'tag_fr': '💎 BON EV',
        'tag_en': '💎 GOOD EV',
        'emoji': '💎',
        'advice_fr': 'Excellent bet, recommandé!',
        'advice_en': 'Excellent bet, recommended!',
        'recommended_for_fr': 'Tous',
        'recommended_for_en': 'Everyone'
    },
    'excellent': {
        'range': (18.0, 100.0),
        'tag_fr': '🔥 EV EXCEPTIONNEL',
        'tag_en': '🔥 EXCEPTIONAL EV',
        'emoji': '🔥',
        'advice_fr': 'Rare! Max bet!',
        'advice_en': 'Rare! Max bet!',
        'recommended_for_fr': 'Tous',
        'recommended_for_en': 'Everyone'
    }
}


def get_ev_quality(ev_percent: float, lang: str = 'en') -> Dict:
    """
    Returns quality info for a given EV percentage
    
    Args:
        ev_percent: EV percentage (e.g., 8.5)
        lang: Language ('en' or 'fr')
    
    Returns:
        Dict with tier, tag, emoji, advice, recommended_for
    """
    for tier_name, tier_data in EV_QUALITY_TIERS.items():
        min_ev, max_ev = tier_data['range']
        if min_ev <= ev_percent < max_ev:
            tag_key = f'tag_{lang}'
            advice_key = f'advice_{lang}'
            rec_key = f'recommended_for_{lang}'
            
            return {
                'tier': tier_name,
                'tag': tier_data.get(tag_key, tier_data['tag_en']),
                'emoji': tier_data['emoji'],
                'advice': tier_data.get(advice_key, tier_data['advice_en']),
                'recommended_for': tier_data.get(rec_key, tier_data['recommended_for_en'])
            }
    
    # Fallback for <0.5% (should not happen)
    if lang == 'fr':
        return {
            'tier': 'too_low',
            'tag': '❌ EV TROP FAIBLE',
            'emoji': '❌',
            'advice': 'Skip ce bet.',
            'recommended_for': 'Personne'
        }
    else:
        return {
            'tier': 'too_low',
            'tag': '❌ EV TOO LOW',
            'emoji': '❌',
            'advice': 'Skip this bet.',
            'recommended_for': 'Nobody'
        }


def get_user_profile(total_good_odds_bets: int) -> str:
    """
    Determines user profile based on experience
    
    Args:
        total_good_odds_bets: Total number of Good Odds bets placed
    
    Returns:
        Profile string: 'beginner', 'intermediate', or 'advanced'
    """
    if total_good_odds_bets < 100:
        return 'beginner'
    elif total_good_odds_bets < 500:
        return 'intermediate'
    else:
        return 'advanced'


def get_profile_warning(ev_percent: float, user_profile: str, lang: str = 'en') -> str:
    """
    Returns warning message if EV is too low for user's profile
    
    Args:
        ev_percent: EV percentage
        user_profile: User's profile ('beginner', 'intermediate', 'advanced')
        lang: Language
    
    Returns:
        Warning message or empty string
    """
    quality = get_ev_quality(ev_percent, lang)
    recommended_min = RECOMMENDED_MIN_EV[user_profile]
    
    # Advanced users get warnings for very low EV (< 5%)
    if user_profile == 'advanced' and ev_percent < 5.0:
        if lang == 'fr':
            return f"""
⚠️ <b>ATTENTION - EV TRÈS FAIBLE</b>

EV: {ev_percent}% - Variance extrême
Recommandé: Stakes <1% bankroll
"""
        else:
            return f"""
⚠️ <b>WARNING - VERY LOW EV</b>

EV: {ev_percent}% - Extreme variance
Recommended: Stakes <1% bankroll
"""
    elif user_profile == 'advanced':
        return ""
    
    # Beginner warning for <12% EV
    if user_profile == 'beginner' and ev_percent < 12.0:
        if lang == 'fr':
            return f"""
⚠️ <b>ATTENTION - BET AVANCÉ</b>

Cet EV est bas ({ev_percent}%). Recommandé seulement pour:
• Users avec 100+ bets d'expérience
• Bankroll >$2,000
• Compréhension de la variance

<b>Si tu débutes, attends EV 12%+ pour commencer!</b>
"""
        else:
            return f"""
⚠️ <b>WARNING - ADVANCED BET</b>

This EV is low ({ev_percent}%). Recommended only for:
• Users with 100+ bets experience
• Bankroll >$2,000
• Understanding of variance

<b>If you're new, wait for EV 12%+ to start!</b>
"""
    
    # Intermediate warning for <8% EV
    if user_profile == 'intermediate' and ev_percent < 8.0:
        if lang == 'fr':
            return f"""
⚠️ <b>ATTENTION - BET EXPERT</b>

Cet EV ({ev_percent}%) a beaucoup de variance.
Recommandé si:
• 500+ bets d'expérience
• Bankroll >$5,000
• Discipline long terme

<b>Vise EV 8%+ pour meilleurs résultats!</b>
"""
        else:
            return f"""
⚠️ <b>WARNING - EXPERT BET</b>

This EV ({ev_percent}%) has high variance.
Recommended if:
• 500+ bets experience
• Bankroll >$5,000
• Long-term discipline

<b>Target EV 8%+ for better results!</b>
"""
    
    return ""


def calculate_bankroll_multiplier(ev_percent: float) -> int:
    """
    Returns recommended bankroll multiplier based on EV
    Higher EV = can use smaller bankroll (less variance)
    """
    if ev_percent >= 15:
        return 30
    elif ev_percent >= 10:
        return 40
    elif ev_percent >= 7:
        return 50
    else:
        return 75
