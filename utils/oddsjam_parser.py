"""
OddsJam Notifications Parser
Parse Positive EV, Middle, and Arbitrage alerts from OddsJam app via Tasker
"""
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def parse_positive_ev_notification(notif_text: str) -> Optional[Dict]:
    """
    Parse notification Positive EV d'OddsJam
    
    Input:
    "🚨 Positive EV Alert 3.92% 🚨
    Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] 
    +125 @ Betsson (Basketball, NBA)"
    
    Returns:
    {
        'type': 'positive_ev',
        'ev_percent': 3.92,
        'team1': 'Orlando Magic',
        'team2': 'New York Knicks',
        'market': 'Player Made Threes',
        'player': 'Landry Shamet',
        'selection': 'Under 1.5',
        'odds': '+125',
        'bookmaker': 'Betsson',
        'sport': 'Basketball',
        'league': 'NBA'
    }
    """
    
    try:
        # Extract %
        ev_match = re.search(r'(\d+\.\d+)%', notif_text)
        if not ev_match:
            return None
        ev_percent = float(ev_match.group(1))
        
        # Extract teams (support numbers and special chars like "Parma Calcio 1913")
        teams_match = re.search(r'([A-Za-z0-9\s\.\-]+?) vs ([A-Za-z0-9\s\.\-]+?)\s*\[', notif_text)
        if not teams_match:
            return None
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        
        # Extract market
        market_match = re.search(r'\[([^\]]+)\]', notif_text)
        if not market_match:
            return None
        market_content = market_match.group(1)
        
        # Parse market content: "Player Made Threes : Landry Shamet Under 1.5"
        parts = market_content.split(':')
        if len(parts) >= 2:
            market = parts[0].strip()
            selection_full = parts[1].strip()
            
            # Extract player name (avant Over/Under)
            player_match = re.search(r'(.+?)\s+(Over|Under)\s+(\d+\.?\d*)', selection_full)
            if player_match:
                player = player_match.group(1).strip()
                direction = player_match.group(2)
                value = player_match.group(3)
                selection = f"{direction} {value}"
            else:
                player = None
                selection = selection_full
        else:
            market = market_content
            player = None
            selection = "N/A"
        
        # Extract odds
        odds_match = re.search(r'([+-]\d+)\s*@', notif_text)
        if not odds_match:
            return None
        odds = odds_match.group(1)
        
        # Extract bookmaker
        book_match = re.search(r'@\s*([A-Za-z0-9\s]+?)\s*\(', notif_text)
        if not book_match:
            return None
        bookmaker = book_match.group(1).strip()
        
        # Extract sport/league
        sport_match = re.search(r'\(([^,]+),\s*([^)]+)\)', notif_text)
        if sport_match:
            sport = sport_match.group(1).strip()
            league = sport_match.group(2).strip()
        else:
            sport = "Unknown"
            league = "Unknown"
        
        return {
            'type': 'positive_ev',
            'ev_percent': ev_percent,
            'team1': team1,
            'team2': team2,
            'market': market,
            'player': player,
            'selection': selection,
            'odds': odds,
            'bookmaker': bookmaker,
            'sport': sport,
            'league': league
        }
        
    except Exception as e:
        logger.error(f"Failed to parse Positive EV: {e}")
        return None


def parse_middle_notification(notif_text: str) -> Optional[Dict]:
    """
    Parse notification Middle d'OddsJam
    
    Input:
    "🚨 Middle Alert 3.1% 🚨
    Coastal Carolina vs North Dakota [Point Spread : Coastal Carolina +3.5/North Dakota -2] 
    Coastal Carolina +3.5 -132 @ TonyBet, North Dakota -2 +150 @ LeoVegas (Basketball, NCAAB)"
    
    Returns:
    {
        'type': 'middle',
        'middle_percent': 3.1,
        'team1': 'Coastal Carolina',
        'team2': 'North Dakota',
        'market': 'Point Spread',
        'side_a': {...},
        'side_b': {...},
        'sport': 'Basketball',
        'league': 'NCAAB'
    }
    """
    
    try:
        # Extract %
        middle_match = re.search(r'(\d+\.\d+)%', notif_text)
        if not middle_match:
            return None
        middle_percent = float(middle_match.group(1))
        
        # Extract teams (support numbers and special chars like "Parma Calcio 1913")
        teams_match = re.search(r'([A-Za-z0-9\s\.\-]+?) vs ([A-Za-z0-9\s\.\-]+?)\s*\[', notif_text)
        if not teams_match:
            return None
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        
        # Extract market
        market_match = re.search(r'\[([^\]]+)\]', notif_text)
        if not market_match:
            return None
        market_content = market_match.group(1)
        
        # Parse market: "Point Spread : Team1 +3.5/Team2 -2"
        market_parts = market_content.split(':')
        market = market_parts[0].strip()
        
        # Extract bets details after ]
        bets_text = notif_text.split(']')[1]
        
        # Pattern: "TeamA +3.5 -132 @ BookA, TeamB -2 +150 @ BookB"
        # Pattern: "TeamA Over 3.5 -132 @ BookA, TeamB Under 4 +150 @ BookB" OR spreads like "+3.5"/"-2"
        # Groups: (team, over/under token optional, line, odds, bookmaker)
        # Note: bookmaker peut contenir des tirets (ex: "Mise-o-jeu", "bet-o-win") → inclure '-' dans le pattern
        bet_pattern = r'([A-Za-z0-9\s\.\-]+?)\s+([OoUu][a-z]+\s+)?([+-]?\d+\.?\d*)\s+([+-]\d+)\s*@\s*([A-Za-z0-9\s\.\-]+?)(?:,|\()'
        bets = re.findall(bet_pattern, bets_text)
        
        if len(bets) < 2:
            return None
        
        # Groups: (team, over/under, line, odds, bookmaker)
        dir_a = (bets[0][1] or '').strip().title()
        dir_b = (bets[1][1] or '').strip().title()
        sel_a = f"{dir_a} {bets[0][2]}".strip() if dir_a else bets[0][2]
        sel_b = f"{dir_b} {bets[1][2]}".strip() if dir_b else bets[1][2]
        side_a = {
            'team': bets[0][0].strip(),
            'selection': sel_a,
            'line': bets[0][2],
            'odds': bets[0][3],
            'bookmaker': bets[0][4].strip()
        }
        
        side_b = {
            'team': bets[1][0].strip(),
            'selection': sel_b,
            'line': bets[1][2],
            'odds': bets[1][3],
            'bookmaker': bets[1][4].strip()
        }
        
        # Extract sport/league
        sport_match = re.search(r'\(([^,]+),\s*([^)]+)\)', notif_text)
        if sport_match:
            sport = sport_match.group(1).strip()
            league = sport_match.group(2).strip()
        else:
            sport = "Unknown"
            league = "Unknown"
        
        return {
            'type': 'middle',
            'middle_percent': middle_percent,
            'team1': team1,
            'team2': team2,
            'market': market,
            'side_a': side_a,
            'side_b': side_b,
            'sport': sport,
            'league': league
        }
        
    except Exception as e:
        logger.error(f"Failed to parse Middle: {e}")
        return None


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal"""
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))


def calculate_middle_stakes(odds_a: str, odds_b: str, total_bankroll: float) -> Dict:
    """
    Calculate optimal stakes for middle betting opportunity
    
    A middle bet is when you bet on overlapping lines:
    - If ONE wins → small loss (most of the time, ~80-85%)
    - If BOTH win (middle hit) → BIG profit (rare, ~15-20%)
    - EV+ because: (middle_prob × big_gain) > (no_middle_prob × small_loss)
    
    Example:
        Over 20.5 @ -118 → Stake $25.50 → Return $47
        Under 22.5 @ +114 → Stake $22.00 → Return $47
        Total staked: $47.50
        
        Scenarios:
        1. ≤20 points (Under wins): $47 - $47.50 = -$0.50 ❌
        2. 21-22 points (MIDDLE!): $94 - $47.50 = +$46.50 🚀
        3. ≥23 points (Over wins): $47 - $47.50 = -$0.50 ❌
    
    Returns:
        Dict with stakes, returns, and profit scenarios
    """
    # Convert American odds to decimal
    dec_a = american_to_decimal(int(odds_a.replace('+', '').replace('−', '-')))
    dec_b = american_to_decimal(int(odds_b.replace('+', '').replace('−', '-')))
    
    # Calculate optimal stakes to balance payouts
    # We want return_a ≈ return_b so the loss when one wins is minimized
    total_odds = dec_a + dec_b
    stake_a = total_bankroll * (dec_b / total_odds)
    stake_b = total_bankroll * (dec_a / total_odds)
    
    # Calculate returns if each side wins
    return_a = stake_a * dec_a
    return_b = stake_b * dec_b
    
    # Calculate profits for each scenario
    total_stake = stake_a + stake_b
    
    # Scenario 1: Only side A wins (no middle)
    profit_a_only = return_a - total_stake
    
    # Scenario 2: Only side B wins (no middle)
    profit_b_only = return_b - total_stake
    
    # Scenario 3: Both win (MIDDLE HIT! 🚀)
    profit_both = (return_a + return_b) - total_stake
    
    # The "no middle" profit is what you get 80-85% of the time
    # Usually a small loss (-$0.50 to -$2)
    no_middle_profit = max(profit_a_only, profit_b_only)
    
    return {
        'stake_a': stake_a,
        'stake_b': stake_b,
        'return_a': return_a,
        'return_b': return_b,
        'profit_a_only': profit_a_only,
        'profit_b_only': profit_b_only,
        'middle_profit': profit_both,
        'no_middle_profit': no_middle_profit,  # What you get when middle doesn't hit
        'total_stake': total_stake
    }


def parse_arbitrage_from_text(notif_text: str) -> Optional[Dict]:
    """
    Parse arbitrage or middle alert from text format
    
    Input:
    "🎰 Odds Alert
    🚨 Arbitrage Alert 2.68% 🚨
    SSC Napoli vs Qarabağ Ağdam FK [Player Shots : Kady Iuri Borges Malinowski Over 1.5/Kady Iuri Borges Malinowski Under 1.5] 
    Kady Iuri Borges Malinowski Over 1.5 +250 @ bwin, Kady Iuri Borges Malinowski Under 1.5 -220 @ LeoVegas (Soccer, UEFA - Champions League)"
    
    OR:
    "🎰 Odds Alert
    🚨 Middle Alert 3.92% 🚨
    McNeese vs Murray State [Total Points : Over 154.5/Under 155.5] Over 154.5 +130 @ BET99, Under 155.5 -111 @ Betway (Basketball, NCAAB)"
    
    Returns structured dict for send_arbitrage_alert_to_users
    """
    try:
        # Extract arb/middle percentage (try both patterns)
        arb_match = re.search(r'(Arbitrage|Middle) Alert\s+(\d+\.\d+)%', notif_text)
        if not arb_match:
            return None
        arb_percentage = float(arb_match.group(2))
        
        # Extract teams
        teams_match = re.search(r'([A-Za-z0-9\s\.\-]+?) vs ([A-Za-z0-9\s\.\-]+?)\s*\[', notif_text)
        if not teams_match:
            return None
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        match = f"{team1} vs {team2}"
        
        # Extract market info
        market_match = re.search(r'\[([^\]]+)\]', notif_text)
        if not market_match:
            return None
        market_content = market_match.group(1)
        
        # Parse market: "Player Shots : Kady Iuri Borges Malinowski Over 1.5/Under 1.5"
        parts = market_content.split(':')
        if len(parts) >= 2:
            market = parts[0].strip()
            outcomes_text = parts[1].strip()
        else:
            market = market_content
            outcomes_text = ""
        
        # Extract sport/league from end (Sport, League)
        sport_league_match = re.search(r'\(([^,]+),\s*([^\)]+)\)', notif_text)
        if sport_league_match:
            sport = sport_league_match.group(1).strip()
            league = sport_league_match.group(2).strip()
        else:
            sport = "Unknown"
            league = "Unknown"
        
        # Extract outcomes section (after the bracket and before sport/league)
        # Find text after "]" and before "("
        # More flexible: capture everything between ] and the last (
        bracket_end = notif_text.rfind(']')
        paren_start = notif_text.rfind('(')
        
        if bracket_end == -1 or paren_start == -1 or paren_start <= bracket_end:
            logger.warning(f"Could not find outcomes section in arbitrage: {notif_text}")
            return None
        
        outcomes_text = notif_text[bracket_end + 1:paren_start].strip()
        
        # Pattern: "OUTCOME +/-ODDS @ BOOKMAKER"
        # Split by comma first
        outcome_parts = outcomes_text.split(',')
        
        outcomes = []
        for part in outcome_parts[:2]:  # Take only first 2
            part = part.strip()
            # Match: "NJIT +17.5 +121 @ Betsson" or "Over 74.5 +115 @ BET99"
            # Use greedy match for odds to capture the last occurrence
            match = re.search(r'(.+)\s+([+-]\d+)\s+@\s+(.+)$', part)
            if not match:
                logger.warning(f"Could not parse outcome part: {part}")
                continue
            
            outcome_name = match.group(1).strip()
            odds_str = match.group(2).strip()
            bookmaker = match.group(3).strip()
            
            # Clean outcome name - remove any leftover text before the actual outcome
            # If it contains newlines or the alert text, extract just the outcome
            if '\n' in outcome_name or '🎰' in outcome_name or 'Alert' in outcome_name:
                # Take only the last line or part after the last occurrence of team/market info
                lines = outcome_name.split('\n')
                outcome_name = lines[-1].strip()
            
            # Convert odds string to int
            try:
                odds = int(odds_str)
            except ValueError:
                logger.warning(f"Invalid odds format: {odds_str}")
                continue
            
            outcomes.append({
                'outcome': outcome_name,
                'odds': odds,
                'casino': bookmaker
            })
        
        if len(outcomes) < 2:
            logger.warning(f"Only found {len(outcomes)} outcomes, need 2")
            return None
        
        return {
            'event_id': f"arb_{team1.replace(' ', '_').lower()}_{team2.replace(' ', '_').lower()}",
            'arb_percentage': arb_percentage,
            'match': match,
            'league': league,
            'market': market,
            'sport': sport,
            'outcomes': outcomes
        }
        
    except Exception as e:
        logger.error(f"Failed to parse arbitrage text: {e}")
        return None
