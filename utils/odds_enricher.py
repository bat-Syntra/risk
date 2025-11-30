"""
Enrichit TOUTES les alertes (Arbitrage, Middle, Good EV) avec The Odds API
- Liens directs pour chaque casino
- Date/heure exacte du match
- Vérification des cotes en temps réel
"""

import os
import re
import logging
from typing import Dict, Optional, List, Tuple, Set
from datetime import datetime, timezone, timedelta
import requests

# Setup
logger = logging.getLogger(__name__)
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# ✅ OPTIMIZATION #3: Cache for leagues NOT in API (reduces API calls by 50%)
_MINOR_LEAGUES_CACHE: Set[str] = set()
_CACHE_EXPIRY = None

# Known minor leagues that are NEVER in The Odds API
KNOWN_MINOR_LEAGUES = {
    # Soccer
    'brazil - serie a', 'brazil - serie b', 'brazil - serie c',
    'france - ligue 2', 'france - national', 'france - national 2',
    'argentina - primera b', 'argentina - segunda',
    'spain - segunda', 'spain - segunda b',
    'italy - serie b', 'italy - serie c',
    'germany - 2. bundesliga', '2. bundesliga',
    'england - championship', 'england - league one', 'england - league two',
    'portugal - segunda liga',
    'netherlands - eerste divisie',
    # Tennis
    'atp challenger', 'wta 125', 'itf',
    # Basketball
    'g league', 'nba g league',
    # Hockey
    'ahl', 'echl',
}

def is_minor_league(league: str) -> bool:
    """
    Check if league is known to NOT be in The Odds API.
    Uses both cache and known minor leagues list.
    ⚡ Saves 2-3s per call for minor leagues (~50% of calls)
    """
    global _CACHE_EXPIRY, _MINOR_LEAGUES_CACHE
    
    # Reset cache daily
    if _CACHE_EXPIRY and datetime.now() > _CACHE_EXPIRY:
        _MINOR_LEAGUES_CACHE.clear()
        _CACHE_EXPIRY = None
    
    if not _CACHE_EXPIRY:
        _CACHE_EXPIRY = datetime.now() + timedelta(hours=24)
    
    league_lower = league.lower().strip()
    
    # Check cache first
    if league_lower in _MINOR_LEAGUES_CACHE:
        return True
    
    # Check known minor leagues
    if league_lower in KNOWN_MINOR_LEAGUES:
        _MINOR_LEAGUES_CACHE.add(league_lower)
        return True
    
    return False

# Sport mapping
SPORT_MAPPING = {
    # Basketball
    'NBA': 'basketball_nba',
    'NCAAB': 'basketball_ncaab',
    'NCAA Basketball': 'basketball_ncaab',
    'NCAA Men Basketball': 'basketball_ncaab',
    'EuroLeague': 'basketball_euroleague',
    
    # Hockey
    'NHL': 'icehockey_nhl',
    
    # Football
    'NFL': 'americanfootball_nfl',
    'NCAAF': 'americanfootball_ncaaf',
    'NCAA Football': 'americanfootball_ncaaf',
    
    # Soccer
    'Premier League': 'soccer_epl',
    'England - Premier League': 'soccer_epl',
    'EPL': 'soccer_epl',
    'Champions League': 'soccer_uefa_champs_league',
    'La Liga': 'soccer_spain_la_liga',
    'Spain - La Liga': 'soccer_spain_la_liga',
    'Serie A': 'soccer_italy_serie_a',
    'Italy - Serie A': 'soccer_italy_serie_a',
    'Brazil - Serie A': 'soccer_brazil_campeonato',
    'Serie B': 'soccer_italy_serie_b',
    'Ligue 1': 'soccer_france_ligue_one',
    'France - Ligue 1': 'soccer_france_ligue_one',
    'Bundesliga': 'soccer_germany_bundesliga',
    'Germany - Bundesliga': 'soccer_germany_bundesliga',
    'MLS': 'soccer_usa_mls',
    
    # Tennis
    'ATP': 'tennis_atp',
    'ATP Challenger': 'tennis_atp',  # Challengers may not be covered, try main ATP
    'WTA': 'tennis_wta',
    'WTA 125': 'tennis_wta',
    
    # Baseball
    'MLB': 'baseball_mlb',
    
    # MMA/Boxing
    'UFC': 'mma_mixed_martial_arts',
    'Boxing': 'boxing_boxing',
}


def format_match_time_with_countdown(commence_time_iso: str, lang: str = 'fr') -> str:
    """
    Formate l'heure du match avec countdown
    Ex FR: "Saturday, Nov 29 - 02:45 PM ET (débute dans 50h 32min)"
    Ex EN: "Saturday, Nov 29 - 02:45 PM ET (starts in 50h 32min)"
    """
    try:
        # Parse ISO timestamp
        dt = datetime.fromisoformat(commence_time_iso.replace('Z', '+00:00'))
        
        # Convert to ET (UTC-5)
        et_tz = timezone(timedelta(hours=-5))
        dt_et = dt.astimezone(et_tz)
        
        # Format day and date
        day_name = dt_et.strftime('%A')  # Saturday
        date_str = dt_et.strftime('%b %d')  # Nov 29
        time_str = dt_et.strftime('%I:%M %p')  # 02:45 PM
        
        # Calculate countdown
        now = datetime.now(timezone.utc)
        time_diff = dt - now
        
        if time_diff.total_seconds() > 0:
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            if lang == 'fr':
                countdown = f"débute dans {hours}h {minutes:02d}min"
            else:
                countdown = f"starts in {hours}h {minutes:02d}min"
        else:
            # Match already started or passed
            if lang == 'fr':
                countdown = "EN COURS" if abs(time_diff.total_seconds()) < 10800 else "TERMINÉ"
            else:
                countdown = "LIVE" if abs(time_diff.total_seconds()) < 10800 else "ENDED"
        
        return f"{day_name}, {date_str} - {time_str} ET ({countdown})"
        
    except Exception as e:
        logger.error(f"Error formatting match time: {e}")
        return commence_time_iso


def extract_teams_from_match(match_str: str) -> Tuple[str, str]:
    """
    Extrait les deux équipes d'un string de match
    Ex: "Lakers @ Warriors" → ("Lakers", "Warriors")
    Ex: "Lakers vs Warriors" → ("Lakers", "Warriors")
    Ex: "Lakers - Warriors" → ("Lakers", "Warriors")
    """
    # Try various separators
    for sep in [' @ ', ' vs ', ' v ', ' - ', ' at ']:
        if sep in match_str:
            parts = match_str.split(sep)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    
    return None, None


def find_event_by_teams(sport_key: str, team1: str, team2: str) -> Optional[Dict]:
    """
    Trouve un événement via l'API en matchant les noms d'équipes
    """
    if not ODDS_API_KEY or not sport_key:
        return None
    
    url = f"{ODDS_API_BASE}/sports/{sport_key}/events"
    params = {
        "apiKey": ODDS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            events = response.json()
            
            # Normaliser pour comparaison
            t1_lower = team1.lower()
            t2_lower = team2.lower()
            
            for event in events:
                home = event.get('home_team', '').lower()
                away = event.get('away_team', '').lower()
                
                # Vérifier les deux ordres possibles
                if (t1_lower in home and t2_lower in away) or \
                   (t2_lower in home and t1_lower in away) or \
                   (home in t1_lower and away in t2_lower) or \
                   (away in t1_lower and home in t2_lower):
                    return {
                        'event_id': event.get('id'),
                        'sport_key': sport_key,
                        'commence_time': event.get('commence_time'),
                        'home_team': event.get('home_team'),
                        'away_team': event.get('away_team')
                    }
    except Exception as e:
        logger.error(f"Error finding event: {e}")
    
    return None


def get_odds_and_links(event_id: str, sport_key: str, bookmakers: List[str] = None) -> Dict:
    """
    Récupère les cotes ET les liens directs pour un événement
    """
    if not ODDS_API_KEY or not event_id or not sport_key:
        return {}
    
    url = f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds"
    
    # Map bookmaker names to API keys
    bookmaker_keys = []
    if bookmakers:
        key_mapping = {
            'BET99': 'bet99',
            'Sports Interaction': 'sportsinteraction',
            'Betway': 'betway',
            'TonyBet': 'tonybet',
            'Coolbet': 'coolbet',
            'bet365': 'bet365',
            'Pinnacle': 'pinnacle',
            'Betsson': 'betsson',
            'Mise-o-jeu': 'miseojeu',
            'Proline': 'proline',
            'Stake': 'stake',
        }
        for book in bookmakers:
            if book in key_mapping:
                bookmaker_keys.append(key_mapping[book])
    
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us,eu",
        "markets": "h2h,totals,spreads",
        "oddsFormat": "american",
        "includeLinks": "true",  # ← CRUCIAL pour les liens directs!
        "includeSids": "true"
    }
    
    if bookmaker_keys:
        params["bookmakers"] = ",".join(bookmaker_keys)
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            result = {
                'commence_time': data.get('commence_time'),
                'home_team': data.get('home_team'),
                'away_team': data.get('away_team'),
                'bookmakers': {}
            }
            
            # Parser chaque bookmaker
            for bookmaker in data.get('bookmakers', []):
                book_name = bookmaker.get('title')
                book_data = {
                    'link': bookmaker.get('link'),  # Lien page événement
                    'markets': {}
                }
                
                # Parser chaque marché
                for market in bookmaker.get('markets', []):
                    market_key = market.get('key')
                    market_data = {
                        'link': market.get('link'),  # Lien marché
                        'outcomes': []
                    }
                    
                    # Parser chaque outcome
                    for outcome in market.get('outcomes', []):
                        market_data['outcomes'].append({
                            'name': outcome.get('name'),
                            'price': outcome.get('price'),
                            'link': outcome.get('link')  # DEEP LINK!
                        })
                    
                    book_data['markets'][market_key] = market_data
                
                # Map API name back to our name
                name_mapping = {
                    'bet99': 'BET99',
                    'sportsinteraction': 'Sports Interaction',
                    'betway': 'Betway',
                    'tonybet': 'TonyBet',
                    'coolbet': 'Coolbet',
                    'bet365': 'bet365',
                    'pinnacle': 'Pinnacle',
                    'betsson': 'Betsson',
                    'miseojeu': 'Mise-o-jeu',
                    'proline': 'Proline',
                    'stake': 'Stake',
                }
                
                for api_name, display_name in name_mapping.items():
                    if bookmaker.get('key') == api_name:
                        result['bookmakers'][display_name] = book_data
                        break
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting odds and links: {e}")
    
    return {}


def enrich_alert_with_api(alert_data: Dict, alert_type: str = 'arbitrage') -> Dict:
    """
    Enrichit n'importe quelle alerte avec les données API
    
    Args:
        alert_data: Les données parsées de l'alerte
        alert_type: 'arbitrage', 'middle', 'good_ev'
    
    Returns:
        alert_data enrichi avec:
        - event_id_api: ID de l'événement API
        - sport_key: Clé du sport pour l'API
        - commence_time: Date/heure du match
        - verified_odds: Cotes vérifiées en temps réel
        - deep_links: Liens directs pour chaque bookmaker
    """
    
    # Extraire les infos de base
    match = alert_data.get('match')
    league = alert_data.get('league', '')
    
    # ✅ OPTIMIZATION #3: Skip API call for known minor leagues (saves 2-3s)
    if league and is_minor_league(league):
        logger.info(f"⚡ CACHE HIT: {league} is minor league, skipping API enrichment")
        return alert_data
    
    # Si "match" n'est pas présent mais qu'on a team1/team2, le reconstruire
    team1_raw = alert_data.get('team1')
    team2_raw = alert_data.get('team2')
    if not match and team1_raw and team2_raw:
        match = f"{team1_raw} vs {team2_raw}"
        alert_data['match'] = match
    
    # Trouver le sport_key
    sport_key = None
    if league:
        sport_key = SPORT_MAPPING.get(league)
        if not sport_key:
            logger.info(f"⚠️ League '{league}' not in API mapping - event may not be covered")
    
    if not sport_key and match:
        # Essayer de deviner depuis le match ou le marché
        lower_match = match.lower()
        if any(x in lower_match for x in ['lakers', 'celtics', 'heat', 'warriors']):
            sport_key = 'basketball_nba'
        elif any(x in lower_match for x in ['maple leafs', 'canadiens', 'rangers']):
            sport_key = 'icehockey_nhl'
    
    if not sport_key:
        logger.info(f"⚠️ No sport_key found for league '{league}' - skipping API enrichment")
        return alert_data
    
    # Extraire les équipes
    if not match:
        logger.warning("No match info available to extract teams - skipping API enrichment")
        return alert_data
    
    team1, team2 = extract_teams_from_match(match)
    
    if not team1 or not team2:
        logger.warning(f"Could not extract teams from: {match}")
        return alert_data
    
    # Trouver l'événement
    event_info = find_event_by_teams(sport_key, team1, team2)
    
    if not event_info:
        logger.info(f"⚠️ Event not found in API: {team1} vs {team2} ({league})")
        logger.info(f"   → Minor leagues (Challenger, Division 2, etc.) are usually not covered by The Odds API")
        # Add to cache for next time
        if league:
            global _MINOR_LEAGUES_CACHE
            _MINOR_LEAGUES_CACHE.add(league.lower().strip())
            logger.info(f"⚡ CACHE: Added {league} to minor leagues cache")
        return alert_data
    
    # Enrichir avec event_id et sport_key
    alert_data['event_id_api'] = event_info['event_id']
    alert_data['sport_key'] = event_info['sport_key']
    alert_data['commence_time'] = event_info['commence_time']
    
    # Extraire les bookmakers selon le type d'alerte
    bookmakers = []
    if alert_type == 'arbitrage':
        # Pour arbitrage, on a des outcomes
        for outcome in alert_data.get('outcomes', []):
            book = outcome.get('casino')
            if book and book not in bookmakers:
                bookmakers.append(book)
    elif alert_type == 'middle':
        # Pour middle, on a side_a et side_b
        if 'side_a' in alert_data:
            book_a = alert_data['side_a'].get('bookmaker')
            if book_a:
                bookmakers.append(book_a)
        if 'side_b' in alert_data:
            book_b = alert_data['side_b'].get('bookmaker')
            if book_b and book_b not in bookmakers:
                bookmakers.append(book_b)
    elif alert_type == 'good_ev':
        # Pour good_ev, on a un bookmaker direct
        book = alert_data.get('bookmaker')
        if book:
            bookmakers.append(book)
    
    # Récupérer les cotes et liens
    odds_data = get_odds_and_links(
        event_info['event_id'],
        event_info['sport_key'],
        bookmakers
    )
    
    # Ajouter les liens directs et cotes vérifiées
    alert_data['deep_links'] = {}
    alert_data['verified_odds'] = {}
    
    for book_name, book_data in odds_data.get('bookmakers', {}).items():
        # Récupérer le meilleur lien disponible
        best_link = book_data.get('link')  # Lien page événement par défaut
        
        # Essayer de trouver un deep link pour h2h (moneyline)
        h2h_market = book_data.get('markets', {}).get('h2h')
        if h2h_market:
            # Prendre le lien du marché si disponible
            if h2h_market.get('link'):
                best_link = h2h_market['link']
            
            # Ou encore mieux, le lien direct de l'outcome
            for outcome in h2h_market.get('outcomes', []):
                if outcome.get('link'):
                    best_link = outcome['link']
                    break  # Prendre le premier deep link trouvé
            
            # Stocker les cotes vérifiées
            alert_data['verified_odds'][book_name] = {
                'outcomes': h2h_market.get('outcomes', [])
            }
        
        alert_data['deep_links'][book_name] = best_link
    
    # Formater la date pour affichage avec countdown
    if alert_data.get('commence_time'):
        alert_data['formatted_time'] = format_match_time_with_countdown(alert_data['commence_time'])
    
    logger.info(f"Enriched {alert_type} alert with API data: {len(alert_data.get('deep_links', {}))} links found")
    
    return alert_data


# Fonction de test
if __name__ == "__main__":
    # Test avec une alerte arbitrage
    test_arb = {
        'match': 'Lakers @ Warriors',
        'league': 'NBA',
        'outcomes': [
            {'casino': 'BET99', 'outcome': 'Lakers', 'odds': 150},
            {'casino': 'Sports Interaction', 'outcome': 'Warriors', 'odds': 180}
        ]
    }
    
    enriched = enrich_alert_with_api(test_arb, 'arbitrage')
    print("Enriched arbitrage:")
    print(f"  Event ID: {enriched.get('event_id_api')}")
    print(f"  Sport: {enriched.get('sport_key')}")
    print(f"  Time: {enriched.get('formatted_time')}")
    print(f"  Links: {enriched.get('deep_links')}")
    print(f"  Verified odds: {enriched.get('verified_odds')}")
