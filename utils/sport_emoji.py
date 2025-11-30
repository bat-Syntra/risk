"""
Sport Emoji Mapping
Maps sport/league names to correct emojis
"""

def get_sport_emoji(league: str, sport: str = '') -> str:
    """
    Get the correct emoji for a sport/league
    
    Args:
        league: League name (e.g., 'NBA', 'NFL', 'NCAAF')
        sport: Sport name (e.g., 'Basketball', 'Football')
    
    Returns:
        Emoji string
    """
    if not league:
        league = ''
    if not sport:
        sport = ''
    
    # Normalize to lowercase for matching
    league_lower = league.lower()
    sport_lower = sport.lower()
    
    # Basketball
    if any(x in league_lower for x in ['nba', 'ncaab', 'wnba', 'euroleague', 'ncaa basketball']):
        return '🏀'
    if 'basketball' in sport_lower:
        return '🏀'
    
    # American Football
    if any(x in league_lower for x in ['nfl', 'ncaaf', 'ncaa football', 'cfb']):
        return '🏈'
    if 'american football' in sport_lower or 'football' in sport_lower:
        # Check if it's NOT soccer
        if 'soccer' not in sport_lower and 'mls' not in league_lower and 'premier' not in league_lower:
            return '🏈'
    
    # Soccer/Football
    if any(x in league_lower for x in ['mls', 'premier', 'bundesliga', 'la liga', 'serie a', 'ligue 1', 'champions', 'fifa', 'uefa']):
        return '⚽'
    if 'soccer' in sport_lower:
        return '⚽'
    
    # Hockey
    if any(x in league_lower for x in ['nhl', 'khl', 'ahl', 'hockey']):
        return '🏒'
    if 'hockey' in sport_lower:
        return '🏒'
    
    # Baseball
    if any(x in league_lower for x in ['mlb', 'baseball']):
        return '⚾'
    if 'baseball' in sport_lower:
        return '⚾'
    
    # Tennis
    if any(x in league_lower for x in ['atp', 'wta', 'tennis', 'grand slam', 'wimbledon', 'us open']):
        return '🎾'
    if 'tennis' in sport_lower:
        return '🎾'
    
    # Golf
    if any(x in league_lower for x in ['pga', 'golf']):
        return '⛳'
    if 'golf' in sport_lower:
        return '⛳'
    
    # MMA/Boxing
    if any(x in league_lower for x in ['ufc', 'bellator', 'mma', 'boxing']):
        return '🥊'
    if 'mma' in sport_lower or 'boxing' in sport_lower:
        return '🥊'
    
    # Esports
    if any(x in league_lower for x in ['lol', 'dota', 'csgo', 'valorant', 'esport']):
        return '🎮'
    if 'esport' in sport_lower:
        return '🎮'
    
    # Rugby
    if 'rugby' in league_lower or 'rugby' in sport_lower:
        return '🏉'
    
    # Cricket
    if 'cricket' in league_lower or 'cricket' in sport_lower:
        return '🏏'
    
    # Default to general sports emoji
    return '🏅'
