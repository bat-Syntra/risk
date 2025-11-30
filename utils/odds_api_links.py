"""
The Odds API Integration - Deep Links System
Récupère les liens directs vers les paris sur les sites de bookmakers
"""
import requests
import logging
import os
from typing import Dict, Optional, List
import re
from urllib.parse import quote_plus, urlparse
from datetime import datetime, timedelta
try:
    from .bookmaker_link_resolver import resolver as link_resolver
except ImportError:
    link_resolver = None

# Configuration API
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "c5fc406d49eeea305125461f1fecea07")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Mapping: nom affiché → key The Odds API
BOOKMAKER_API_KEYS = {
    "888sport": "888sport",
    "bet365": "bet365",
    "BET99": "bet99",
    "Betsson": "betsson",
    "BetVictor": "betvictor",
    "Betway": "betway",
    "bwin": "bwin",
    "Casumo": "casumo",
    "Coolbet": "coolbet",
    "iBet": None,  # Pas dans API
    "Jackpot.bet": None,  # Pas dans API
    "LeoVegas": "leovegas",
    "Mise-o-jeu": "lotoquebec",
    "Pinnacle": "pinnacle",
    "Proline": "proline",
    "Sports Interaction": "sport_interaction",
    "Stake": "stake",
    "TonyBet": "tonybet"
}

# Liens de fallback si pas dans API ou pas de deep link
BOOKMAKER_FALLBACK_URLS = {
    "888sport": "https://www.888sport.com",
    "bet365": "https://www.bet365.com",
    "BET99": "https://www.bet99.com",
    "Betsson": "https://www.betsson.com",
    "BetVictor": "https://www.betvictor.com",
    "Betway": "https://www.betway.com",
    "bwin": "https://www.bwin.com",
    "Casumo": "https://www.casumo.com",
    "Coolbet": "https://www.coolbet.com",
    "iBet": "https://www.ibet.com",
    "Jackpot.bet": "https://www.jackpot.bet",
    "LeoVegas": "https://www.leovegas.com",
    "Mise-o-jeu": "https://www.lotoquebec.com/en/lottery-tickets/sports-betting",
    "Pinnacle": "https://www.pinnacle.com",
    "Proline": "https://proline.ca",
    "Sports Interaction": "https://www.sportsinteraction.com",
    "Stake": "https://www.stake.com",
    "TonyBet": "https://www.tonybet.com"
}

LINKS_CACHE = {}
CACHE_DURATION = timedelta(minutes=1)

logger = logging.getLogger(__name__)

def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s)
    return s.strip('-')

def _guess_sport_key(sport: Optional[str], league: Optional[str]) -> Optional[str]:
    ls = (league or "").lower()
    ss = (sport or "").lower()
    if 'nfl' in ls or 'nfl' in ss or 'football' in ss:
        return 'americanfootball_nfl'
    if 'nba' in ls or 'nba' in ss or 'basketball' in ss:
        return 'basketball_nba'
    if 'nhl' in ls or 'nhl' in ss:
        return 'icehockey_nhl'
    if 'premier league' in ls:
        return 'soccer_epl'
    if 'serie a' in ls and 'italy' in ls:
        return 'soccer_italy_serie_a'
    if 'serie a' in ls and 'brazil' in ls:
        return 'soccer_brazil_serie_a'
    if 'primera division' in ls and 'argentina' in ls:
        return 'soccer_argentina_primera_division'
    if 'mls' in ls:
        return 'soccer_usa_mls'
    if 'ncaab' in ls:
        return 'basketball_ncaab'
    if 'ncaaf' in ls:
        return 'americanfootball_ncaaf'
    if 'soccer' in ss:
        return 'soccer'
    return None

def _split_match(match: str) -> List[str]:
    try:
        parts = [p.strip() for p in (match or '').split(' vs ') if p.strip()]
        if len(parts) == 2:
            return parts
    except Exception:
        pass
    return []

def _resolve_event_id(sport_key: str, team1: str, team2: str) -> Optional[str]:
    try:
        url = f"{ODDS_API_BASE}/sports/{sport_key}/events"
        params = {
            "apiKey": ODDS_API_KEY,
            "dateFormat": "iso"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        events = response.json() or []
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        for ev in events:
            h = (ev.get('home_team') or '').lower().strip()
            a = (ev.get('away_team') or '').lower().strip()
            names = {h, a}
            if any(t1 in nm or nm in t1 for nm in names) and any(t2 in nm or nm in t2 for nm in names):
                return ev.get('id')
    except Exception as e:
        logger.error(f"Failed to resolve event id: {e}")
    return None

def build_league_fallback_url(bookmaker_name: str, league: str) -> Optional[str]:
    """Return a league-level URL for a bookmaker if possible.

    Example: Italy - Serie A → /football/italy/serie-a
    Currently implemented for Betsson and Coolbet.
    """
    if not league:
        return None
    # Try to split 'Country - League'
    country = None
    league_name = league
    if ' - ' in league:
        parts = league.split(' - ', 1)
        country = parts[0]
        league_name = parts[1]
    country_slug = _slugify(country or '')
    league_slug = _slugify(league_name)
    # Default to football (soccer) sections for EU books
    base_path = f"football/{country_slug}/{league_slug}" if country_slug else f"football/{league_slug}"

    if bookmaker_name == 'Betsson':
        return f"https://www.betsson.com/en/sports/{base_path}"
    if bookmaker_name == 'Coolbet':
        return f"https://www.coolbet.com/en/sports/{base_path}"
    # Could add more books here
    return None

def build_search_fallback_url(bookmaker_name: str, match: str, league: str) -> Optional[str]:
    """Return a Google site: search URL targeting the bookmaker for the match.

    This is used when the API does not provide event/market/outcome links.
    """
    base = BOOKMAKER_FALLBACK_URLS.get(bookmaker_name)
    if not base:
        return None
    try:
        domain = urlparse(base).netloc or base
    except Exception:
        domain = base
    q_parts = []
    if match:
        q_parts.append(match)
    if league:
        q_parts.append(league)
    query = "+".join(quote_plus(p) for p in q_parts if p)
    if not query:
        return None
    # Prefer English results, Canada region
    return f"https://www.google.com/search?q=site:{domain}+{query}&hl=en&gl=ca&num=10"


def fetch_event_links(
    sport_key: str,
    event_id: str,
    markets: List[str] = None,
    bookmakers: List[str] = None
) -> Dict:
    """
    Récupère les liens deep link pour un événement depuis The Odds API
    
    Args:
        sport_key: 'soccer_france_ligue_one', 'basketball_nba', etc.
        event_id: ID de l'événement depuis The Odds API
        markets: Liste des marchés (ex: ['h2h', 'totals', 'spreads'])
    
    Returns:
        Dict avec structure complète de l'événement + liens
        Structure: {
            "id": "event_id",
            "sport_key": "...",
            "commence_time": "...",
            "home_team": "...",
            "away_team": "...",
            "bookmakers": [
                {
                    "key": "betsson",
                    "title": "Betsson",
                    "link": "https://...",  # Page événement
                    "markets": [
                        {
                            "key": "h2h",
                            "link": "https://...",  # Page marché (optionnel)
                            "outcomes": [
                                {
                                    "name": "Team A",
                                    "price": 150,
                                    "link": "https://..."  # Deep link outcome (optimal!)
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    """
    # If not specified, request a BROAD set of markets to maximize chance of links
    if markets is None:
        markets = ['h2h']
    
    url = f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds"
    
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": ",".join(markets),
        "oddsFormat": "american",
        "includeLinks": "true",  # CRITIQUE pour avoir les deep links!
        "includeSids": "true"
    }
    if bookmakers:
        params["bookmakers"] = ",".join(bookmakers)
    
    try:
        logger.info(f"Fetching links for event {event_id} in sport {sport_key}; markets={','.join(markets)}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched links, {len(data.get('bookmakers', []))} bookmakers found")
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching event links for {event_id}")
        return {}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch event links: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching event links: {e}")
        return {}


def _normalize_outcome_aliases(name: str) -> List[str]:
    """Generate relaxed aliases for an outcome like 'Udinese Calcio Over 3'."""
    aliases = []
    n = name or ""
    aliases.append(n)
    # Extract Over/Under and value
    m = re.search(r"\b(over|under)\s*([0-9]+(?:\.[0-9]+)?)", n, flags=re.I)
    if m:
        side = m.group(1).lower()
        val = m.group(2)
        aliases.append(f"{side} {val}")  # 'over 3'
        # Common abbreviations
        if side.startswith('o'):
            aliases.append(f"o {val}")
        else:
            aliases.append(f"u {val}")
    return list(dict.fromkeys([a.strip().lower() for a in aliases if a]))


def transform_to_canadian_link(bookmaker_name: str, url: Optional[str]) -> Optional[str]:
    """Transforme un lien global/UK en lien plus adapté au Canada pour un bookmaker donné.

    Cette transformation est best-effort: si aucun pattern ne matche, l'URL est renvoyée telle quelle.
    """
    if not url:
        return url
    name = (bookmaker_name or "").strip()
    u = url

    if name == "LeoVegas":
        if "leovegas.co.uk" in u:
            u = u.replace("leovegas.co.uk", "leovegas.com")
        if "/en-gb/" in u:
            u = u.replace("/en-gb/", "/en-ca/")
        if "leovegas.com" in u and "/en-ca/" not in u:
            u = u.replace("leovegas.com/", "leovegas.com/en-ca/")

    elif name == "bet365":
        if "bet365.com" in u:
            u = u.replace("bet365.com", "bet365.ca")
        if "/en-gb/" in u:
            u = u.replace("/en-gb/", "/en-ca/")

    elif name == "Betway":
        if "betway.com/en" in u:
            u = u.replace("betway.com/en", "betway.ca/en")
        elif "betway.com" in u:
            u = u.replace("betway.com", "betway.ca")
        if "/en-gb/" in u:
            u = u.replace("/en-gb/", "/en-ca/")

    elif name == "BetVictor":
        if "betvictor.com/en-gb" in u:
            u = u.replace("betvictor.com/en-gb", "betvictor.com/en-ca")

    elif name == "Casumo":
        if "/en-gb/" in u:
            u = u.replace("/en-gb/", "/en-ca/")
        if "casumo.com" in u and "/en-ca/" not in u:
            u = u.replace("casumo.com/", "casumo.com/en-ca/")

    elif name == "bwin":
        if "sports.bwin.com" in u:
            u = u.replace("sports.bwin.com", "sports.bwin.ca")
        elif "bwin.com" in u:
            u = u.replace("bwin.com", "bwin.ca")

    elif name == "Betsson":
        # Les deep links avec eventId fonctionnent mieux sous '/en/' (sinon 404 parfois).
        if "eventId=" in u and "/en-ca/" in u:
            u = u.replace("/en-ca/", "/en/")
        else:
            if "/en/" in u and "/en-ca/" not in u:
                u = u.replace("/en/", "/en-ca/")

    elif name == "TonyBet":
        if "tonybet.com" in u:
            u = u.replace("tonybet.com", "tonybet.ca")

    elif name == "Coolbet":
        if "coolbet.com/en" in u:
            u = u.replace("coolbet.com/en", "coolbet.ca/en")
        elif "coolbet.com" in u:
            u = u.replace("coolbet.com", "coolbet.ca")

    elif name == "888sport":
        if "/uk/" in u:
            u = u.replace("/uk/", "/ca/")
        if "/en-gb/" in u:
            u = u.replace("/en-gb/", "/en-ca/")

    # Pinnacle, Stake et les books CA-only restent en .com / domaines locaux

    return u


def find_outcome_link_v2(
    bookmaker_name: str,
    sport_key: str,
    event_id: str,
    market_type: str,
    outcome_name: str,
    teams: Optional[tuple] = None
) -> Optional[str]:
    """
    Version 2: Utilise le BookmakerLinkResolver à 4 niveaux
    """
    try:
        link = link_resolver.get_direct_link(
            bookmaker=bookmaker_name,
            sport_key=sport_key,
            event_id=event_id,
            market=market_type,
            outcome=outcome_name,
            teams=teams
        )
        return link
    except Exception as e:
        logger.error(f"Link resolver failed for {bookmaker_name}: {e}")
        # Fallback sur l'ancienne méthode
        return BOOKMAKER_FALLBACK_URLS.get(bookmaker_name)

def find_outcome_link(
    event_data: Dict,
    bookmaker_name: str,
    market_type: str,
    outcome_name: str
) -> Optional[str]:
    """
    Trouve le lien le plus précis pour un outcome donné
    
    Priority (du meilleur au pire):
    1. outcome.link → Lien direct vers le pari exact (OPTIMAL)
    2. market.link → Page du marché spécifique
    3. bookmaker.link → Page de l'événement général
    4. Fallback URL → Homepage du bookmaker
    
    Args:
        event_data: Réponse de fetch_event_links()
        bookmaker_name: "Betsson", "Coolbet", etc.
        market_type: "h2h", "totals", "team_totals", "spreads"
        outcome_name: "Over 4.5", "Team A Win", "Under 2.5", etc.
    
    Returns:
        URL du lien ou None si bookmaker pas trouvé
    """
    # Mapper vers API key
    book_key = BOOKMAKER_API_KEYS.get(bookmaker_name)
    
    # Si bookmaker pas dans l'API (iBet, Jackpot.bet)
    if not book_key:
        logger.info(f"Bookmaker {bookmaker_name} not in Odds API, returning fallback")
        return BOOKMAKER_FALLBACK_URLS.get(bookmaker_name)
    
    bookmakers = event_data.get("bookmakers", [])
    
    for book in bookmakers:
        if book.get("key") != book_key:
            continue
        
        # Fallback niveau 3: lien bookmaker général (page de l'événement)
        book_link = book.get("link")
        logger.debug(f"Found bookmaker {bookmaker_name}, link: {book_link}")
        # Try multiple market keys in priority order
        market_keys = [mk for mk in [market_type, 'team_totals', 'totals', 'h2h', 'spreads'] if mk]
        aliases = _normalize_outcome_aliases(outcome_name)

        for wanted in market_keys:
            for market in book.get("markets", []):
                if market.get("key") != wanted:
                    continue
                # Fallback niveau 2: lien marché
                market_link = market.get("link") or book_link
                logger.debug(f"Found market {wanted}, link: {market_link}")
                # Try match outcomes
                for outcome in market.get("outcomes", []):
                    outcome_api_name = (outcome.get("name") or "").strip().lower()
                    if any(alias in outcome_api_name or outcome_api_name in alias for alias in aliases):
                        outcome_link = outcome.get("link")
                        if outcome_link:
                            logger.info(f"✅ Found outcome link for {bookmaker_name} - '{outcome.get('name')}' via market {wanted}")
                            return transform_to_canadian_link(bookmaker_name, outcome_link)
                        # No direct outcome link → use market
                        if market_link:
                            logger.info(f"⚠️ Using market link for {bookmaker_name} (no outcome link) via {wanted}")
                            return transform_to_canadian_link(bookmaker_name, market_link)
                # No outcome matched but market exists → use market link
                if market_link:
                    logger.info(f"⚠️ No outcome match; using market link for {bookmaker_name} via {wanted}")
                    return transform_to_canadian_link(bookmaker_name, market_link)

        # If no wanted market found but we have an event link
        if book_link:
            logger.info(f"⚠️ No wanted market; using event link for {bookmaker_name}")
            return transform_to_canadian_link(bookmaker_name, book_link)
        
        # Otherwise continue to next bookmaker (unlikely as we matched key)
        continue
    
    # Bookmaker pas trouvé dans l'event → fallback
    logger.warning(f"Bookmaker {bookmaker_name} not found in event data, using fallback")
    return BOOKMAKER_FALLBACK_URLS.get(bookmaker_name)


def determine_market_type(market_name: str) -> str:
    """
    Mappe le nom de ton marché vers The Odds API market key
    
    Args:
        market_name: "Moneyline", "Total Goals", "Team Total Corners", etc.
    
    Returns:
        API market key: "h2h", "totals", "team_totals", "spreads"
    """
    market_name_lower = market_name.lower()
    
    # Mapping complet
    # Player props (standards pris en charge par l'API)
    if 'player' in market_name_lower:
        if 'points' in market_name_lower and not ('rebounds' in market_name_lower or 'assists' in market_name_lower):
            return 'player_points'
        if 'rebounds' in market_name_lower and 'assists' not in market_name_lower and 'points' not in market_name_lower:
            return 'player_rebounds'
        if 'assists' in market_name_lower and 'rebounds' not in market_name_lower and 'points' not in market_name_lower:
            return 'player_assists'
        if '3' in market_name_lower or 'threes' in market_name_lower or '3-pointers' in market_name_lower:
            return 'player_threes'
        # Combos (PRA, P+R, P+A, R+A) non supportés pour vérification → on laisse tomber sur défaut
    if any(x in market_name_lower for x in ["moneyline", "winner", "match result", "1x2"]):
        return "h2h"
    
    if any(x in market_name_lower for x in ["team total", "team over", "team under"]):
        return "team_totals"
    
    if any(x in market_name_lower for x in ["total", "over", "under", "o/u"]):
        return "totals"
    
    if any(x in market_name_lower for x in ["spread", "handicap", "point spread"]):
        return "spreads"
    
    # Default
    return "h2h"


def get_links_for_drop(
    drop: Dict,
    sport_key: str = None,
    event_id: str = None
) -> Dict[str, str]:
    """
    Récupère les liens pour les 2 bookmakers d'un drop
    
    Args:
        drop: Dict contenant outcomes avec bookmakers
        sport_key: Clé sport API (optionnel, essaie de détecter)
        event_id: ID événement API (optionnel)
    
    Returns:
        Dict {
            "bookmaker1_name": "https://link1",
            "bookmaker2_name": "https://link2"
        }
    """
    links = {}
    
    bookmaker_keys = []
    for outcome in drop.get('outcomes', [])[:2]:
        book_name = outcome.get('casino')
        api_key = BOOKMAKER_API_KEYS.get(book_name)
        if api_key:
            bookmaker_keys.append(api_key)
    if bookmaker_keys:
        bookmaker_keys = list(dict.fromkeys(bookmaker_keys))
    
    # Si pas d'event_id/sport_key essaye de résoudre via match + league
    if not sport_key or not event_id:
        sport_key = sport_key or _guess_sport_key(drop.get('sport'), drop.get('league'))
        teams = _split_match(drop.get('match', ''))
        if sport_key and len(teams) == 2:
            eid = _resolve_event_id(sport_key, teams[0], teams[1])
            if eid:
                event_id = eid
    # Si toujours rien → fallbacks simples (mais valides!)
    if not event_id or not sport_key:
        for outcome in drop.get('outcomes', [])[:2]:
            book_name = outcome.get('casino')
            links[book_name] = get_fallback_url(book_name)  # GARANTIT un lien valide
        return links
    
    # Déterminer le type de marché
    market = drop.get('market', 'Moneyline')
    market_type = determine_market_type(market)

    cache_key = None
    if sport_key and event_id:
        cache_key = f"{sport_key}:{event_id}:{market_type}:{','.join(bookmaker_keys) if bookmaker_keys else ''}"
        cached = LINKS_CACHE.get(cache_key)
        if cached and cached.get('expires') and cached['expires'] > datetime.now():
            cached_links = cached.get('links') or {}
            return dict(cached_links)
    
    # Récupérer event data depuis API (toutes les markets utiles)
    event_data = fetch_event_links(
        sport_key=sport_key,
        event_id=event_id,
        markets=[market_type],
        bookmakers=bookmaker_keys or None
    )
    
    # Si échec API, fallback (mais valides!)
    if not event_data or not event_data.get('bookmakers'):
        logger.warning("Failed to fetch event data or no bookmakers found, using fallbacks")
        for outcome in drop.get('outcomes', [])[:2]:
            book_name = outcome.get('casino')
            links[book_name] = get_fallback_url(book_name)  # GARANTIT un lien valide
        return links
    
    # Trouver les liens pour chaque outcome
    for outcome in drop.get('outcomes', [])[:2]:
        book_name = outcome.get('casino')
        outcome_name = outcome.get('outcome', '')
        
        link = find_outcome_link(
            event_data,
            book_name,
            market_type,
            outcome_name
        )
        
        # Fallback si rien trouvé → Smart search → League-level URL → Homepage
        if not link:
            # Try search on the bookmaker domain for the match
            search_url = build_search_fallback_url(book_name, drop.get('match'), drop.get('league'))
            if search_url:
                link = search_url
            else:
                # Try league-level landing page to at least open the match area
                league_url = build_league_fallback_url(book_name, drop.get('league'))
                link = league_url or get_fallback_url(book_name)
        
        # GARANTIR qu'on a TOUJOURS un lien valide
        if not link or link == "":
            link = get_fallback_url(book_name)
        
        links[book_name] = link

    if cache_key:
        LINKS_CACHE[cache_key] = {
            'links': links,
            'expires': datetime.now() + CACHE_DURATION
        }
    
    return links


def get_fallback_url(bookmaker_name: str) -> str:
    """
    Retourne l'URL de fallback pour un bookmaker
    GARANTIT de retourner un lien qui marche
    
    Args:
        bookmaker_name: Nom du bookmaker
    
    Returns:
        URL de la homepage (toujours valide)
    """
    # Normaliser le nom (case-insensitive)
    for key, url in BOOKMAKER_FALLBACK_URLS.items():
        if key.lower() == bookmaker_name.lower():
            return url
    
    # Si pas trouvé, retourner l'URL exacte du dict ou Google
    return BOOKMAKER_FALLBACK_URLS.get(bookmaker_name, "https://www.google.com/search?q=" + bookmaker_name.replace(' ', '+'))
