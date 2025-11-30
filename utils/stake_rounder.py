"""
Stake Rounding Utility
Arrondit les stakes d'arbitrage pour être moins suspect
"""
from typing import Tuple, Optional
import math
import random


def round_stakes(stake_a: float, stake_b: float, total_budget: float, rounding_level: int = 0, rounding_mode: str = 'nearest') -> Tuple[float, float]:
    """
    Arrondit les stakes intelligemment avec contrôle du mode
    
    Args:
        stake_a: Stake original pour le côté A (ex: 360.85)
        stake_b: Stake original pour le côté B (ex: 389.15)
        total_budget: Budget total maximum (ex: 750.0)
        rounding_level: Niveau d'arrondi
            - 0: Aucun arrondi (précis au cent)
            - 1: Arrondi au dollar près
            - 5: Arrondi au multiple de $5
            - 10: Arrondi au multiple de $10
        rounding_mode: Mode d'arrondi
            - 'nearest': Arrondit au plus proche (défaut)
            - 'down': Arrondit toujours vers le bas (économise CASHH)
            - 'up': Arrondit toujours vers le haut (peut dépasser budget)
    
    Returns:
        Tuple (stake_a_rounded, stake_b_rounded)
    
    Examples:
        >>> round_stakes(360.85, 389.15, 750, 0)
        (360.85, 389.15)
        
        >>> round_stakes(360.85, 389.15, 750, 1, 'nearest')
        (361.0, 389.0)
        
        >>> round_stakes(360.85, 389.15, 750, 5, 'down')
        (360.0, 385.0)
        
        >>> round_stakes(360.85, 389.15, 750, 5, 'up')
        (365.0, 390.0)
    """
    
    # Si pas d'arrondi, retourner les valeurs originales
    if rounding_level == 0:
        return (round(stake_a, 2), round(stake_b, 2))
    
    # Fonction d'arrondi selon le niveau et le mode
    def smart_round(value: float, level: int, mode: str) -> float:
        """Arrondit selon le mode choisi"""
        if level == 1:
            if mode == 'down':
                return math.floor(value)
            elif mode == 'up':
                return math.ceil(value)
            else:  # nearest
                return round(value)
        else:
            if mode == 'down':
                return math.floor(value / level) * level
            elif mode == 'up':
                return math.ceil(value / level) * level
            else:  # nearest
                return round(value / level) * level
    
    # Arrondir les deux stakes selon le mode
    rounded_a = smart_round(stake_a, rounding_level, rounding_mode)
    rounded_b = smart_round(stake_b, rounding_level, rounding_mode)
    
    # Vérifier que le total ne dépasse pas le budget
    total_rounded = rounded_a + rounded_b
    
    if total_rounded <= total_budget:
        # Parfait, le total est dans le budget
        return (rounded_a, rounded_b)
    
    # Si le total dépasse le budget:
    # - Mode 'up': On autorise le dépassement (les users veulent la flexibilité)
    # - Mode 'down' ou 'nearest': On ajuste pour rester dans le budget
    if rounding_mode == 'up':
        # Permettre de dépasser le budget
        return (rounded_a, rounded_b)
    
    # Ajuster le stake le plus gros pour rester dans le budget
    if stake_a > stake_b:
        # Réduire stake_a
        rounded_a = total_budget - rounded_b
        # Arrondir au niveau inférieur pour être sûr
        rounded_a = math.floor(rounded_a / rounding_level) * rounding_level if rounding_level > 1 else math.floor(rounded_a)
        rounded_b = total_budget - rounded_a
    else:
        # Réduire stake_b
        rounded_b = total_budget - rounded_a
        # Arrondir au niveau inférieur pour être sûr
        rounded_b = math.floor(rounded_b / rounding_level) * rounding_level if rounding_level > 1 else math.floor(rounded_b)
        rounded_a = total_budget - rounded_b
    
    # S'assurer que les valeurs sont positives
    rounded_a = max(0, rounded_a)
    rounded_b = max(0, rounded_b)
    
    return (round(rounded_a, 2), round(rounded_b, 2))


def round_arbitrage_stakes(stake_a: float, stake_b: float, odds_a: int, odds_b: int, 
                          total_budget: float, rounding_level: int = 0, 
                          rounding_mode: str = 'nearest', user=None) -> Optional[dict]:
    """
    Arrondit les stakes d'arbitrage ET recalcule profit/ROI avec valeurs arrondies.
    Vérifie que le profit reste positif après arrondi.
    
    Args:
        stake_a: Stake original pour le côté A
        stake_b: Stake original pour le côté B
        odds_a: Cotes américaines pour A (ex: -169)
        odds_b: Cotes américaines pour B (ex: +205)
        total_budget: Budget total
        rounding_level: 0=précis, 1=dollar, 5=$5, 10=$10
        rounding_mode: 'down', 'nearest', ou 'up'
    
    Returns:
        Dict avec:
        - stake_a: Stake arrondi A
        - stake_b: Stake arrondi B
        - return_a: Retour si A gagne (avec stake arrondi)
        - return_b: Retour si B gagne (avec stake arrondi)
        - profit_guaranteed: Profit garanti (minimum des deux scénarios)
        - roi_percent: ROI en % (basé sur profit garanti et stakes arrondis)
        - total_stake: Total des stakes arrondis
        OU None si l'arrondi rendrait le profit négatif
    """
    # Si pas d'arrondi, calculer directement avec valeurs précises
    if rounding_level == 0:
        rounded_a, rounded_b = round(stake_a, 2), round(stake_b, 2)
    else:
        # Arrondir les stakes
        rounded_a, rounded_b = round_stakes(stake_a, stake_b, total_budget, rounding_level, rounding_mode)
    
    # Apply stake randomizer if user is provided and has it enabled
    if user:
        rounded_a, rounded_b = apply_stake_randomizer(rounded_a, rounded_b, user)
    
    # Convertir cotes américaines → décimales
    def american_to_decimal(odds: int) -> float:
        if odds > 0:
            return 1 + odds / 100.0
        else:
            return 1 + 100.0 / abs(odds)
    
    dec_a = american_to_decimal(odds_a)
    dec_b = american_to_decimal(odds_b)
    
    # Calculer returns avec stakes ARRONDIS
    return_a = rounded_a * dec_a
    return_b = rounded_b * dec_b
    
    # Calculer profit garanti = min(return_a, return_b) - total_stake
    total_stake = rounded_a + rounded_b
    profit_guaranteed = min(return_a, return_b) - total_stake
    
    # VALIDATION CRITIQUE: Refuser si profit devient négatif ou nul
    if profit_guaranteed <= 0:
        # L'arrondi a tué l'arbitrage, on refuse
        return None
    
    # Calculer ROI avec valeurs ARRONDIES
    roi_percent = (profit_guaranteed / total_stake * 100.0) if total_stake > 0 else 0
    
    return {
        'stake_a': rounded_a,
        'stake_b': rounded_b,
        'return_a': return_a,
        'return_b': return_b,
        'profit_guaranteed': profit_guaranteed,
        'roi_percent': roi_percent,
        'total_stake': total_stake,
    }


def get_rounding_display(rounding_level: int, lang: str = 'en') -> str:
    """
    Retourne le texte d'affichage pour le niveau d'arrondi
    
    Args:
        rounding_level: 0, 1, 5, ou 10
        lang: 'en' ou 'fr'
    
    Returns:
        Texte formaté
    """
    if lang == 'fr':
        if rounding_level == 0:
            return "Précis"
        elif rounding_level == 1:
            return "Dollar"
        elif rounding_level == 5:
            return "5 Dollars"
        elif rounding_level == 10:
            return "10 Dollars"
        else:
            return f"${rounding_level}"
    else:
        if rounding_level == 0:
            return "Precise"
        elif rounding_level == 1:
            return "Dollar"
        elif rounding_level == 5:
            return "5 Dollars"
        elif rounding_level == 10:
            return "10 Dollars"
        else:
            return f"${rounding_level}"


def apply_stake_randomizer(stake_a: float, stake_b: float, user) -> Tuple[float, float]:
    """
    Applique la randomisation des stakes pour avoir l'air plus humain
    
    Cette fonction est appelée APRÈS le rounding normal, et ajoute une variation
    aléatoire aux stakes pour créer des patterns imprévisibles.
    
    Args:
        stake_a: Stake arrondi pour le côté A
        stake_b: Stake arrondi pour le côté B
        user: Objet User avec les paramètres de randomisation
    
    Returns:
        Tuple (stake_a_randomized, stake_b_randomized)
    
    Examples:
        Avec amounts="5,10" et mode="random":
        - Call 1: +$5 sur A, -$5 sur B
        - Call 2: -$10 sur A, +$10 sur B
        - Call 3: +$10 sur A, -$10 sur B
        
        Avec amounts="5" et mode="up":
        - Toujours +$5 sur les deux stakes
        
        Avec amounts="1,5,10" et mode="down":
        - Toujours -$1, -$5 ou -$10 (choisi au hasard)
    """
    # Check if randomizer is enabled
    randomizer_enabled = getattr(user, 'stake_randomizer_enabled', False)
    if not randomizer_enabled:
        return (stake_a, stake_b)
    
    # Get randomizer settings
    randomizer_amounts_str = getattr(user, 'stake_randomizer_amounts', '')
    randomizer_mode = getattr(user, 'stake_randomizer_mode', 'random')
    
    # Parse amounts
    if not randomizer_amounts_str:
        return (stake_a, stake_b)
    
    try:
        amounts = [int(x) for x in randomizer_amounts_str.split(',') if x.strip()]
    except Exception:
        return (stake_a, stake_b)
    
    if not amounts:
        return (stake_a, stake_b)
    
    # Pick a random amount from the list
    adjustment = random.choice(amounts)
    
    # Apply based on mode
    if randomizer_mode == 'up':
        # Always add to both stakes
        stake_a += adjustment
        stake_b += adjustment
    elif randomizer_mode == 'down':
        # Always subtract from both stakes (ensure positive)
        stake_a = max(10, stake_a - adjustment)  # Keep minimum $10
        stake_b = max(10, stake_b - adjustment)
    else:  # random mode
        # Randomly add or subtract to each stake independently
        # This creates maximum unpredictability
        if random.choice([True, False]):
            stake_a += adjustment
        else:
            stake_a = max(10, stake_a - adjustment)
        
        if random.choice([True, False]):
            stake_b += adjustment
        else:
            stake_b = max(10, stake_b - adjustment)
    
    return (round(stake_a, 2), round(stake_b, 2))
