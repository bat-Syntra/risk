"""
Bookmaker Link Resolver - Système à 4 niveaux pour obtenir des liens directs
Author: Risk0
Version: 1.0.0

Hiérarchie de résolution:
1. The Odds API avec includeLinks (LeoVegas, Coolbet, Betsson marchent)
2. OpticOdds API pour bookmakers canadiens (BET99, etc.)
3. Construction manuelle avec patterns + SIDs
4. Fallback sur homepage
"""

import os
import re
import logging
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)

# API Keys
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
OPTIC_ODDS_KEY = os.getenv("OPTIC_ODDS_KEY")  # Pour plus tard

class BookmakerLinkResolver:
    """Résout les liens directs pour tous les bookmakers avec système à 4 niveaux"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # Mapping nom → clé API The Odds
        self.api_keys = {
            '888sport': 'sport888',
            'bet365': 'bet365',
            'BetVictor': 'betvictor',
            'Betway': 'betway',
            'bwin': 'bwin',
            'Casumo': 'casumo',
            'LeoVegas': 'leovegas',
            'Betsson': 'betsson',
            'Pinnacle': 'pinnacle',
            'Coolbet': 'coolbet',  # Peut-être pas dans l'API
            'TonyBet': 'tonybet'    # Peut-être pas dans l'API
        }
        
        # Bookmakers canadiens (pas dans The Odds API standard)
        self.canadian_only = {'BET99', 'Sports Interaction', 'Proline', 'Mise-o-jeu'}
        
        # Petits bookmakers (pas dans l'API)
        self.small_bookies = {'iBet', 'Jackpot.bet', 'Stake'}
    
    def get_direct_link(
        self, 
        bookmaker: str,
        sport_key: str,
        event_id: str,
        market: Optional[str] = None,
        outcome: Optional[str] = None,
        teams: Optional[Tuple[str, str]] = None
    ) -> str:
        """
        Obtient le lien direct le plus précis possible pour un bookmaker
        
        Args:
            bookmaker: Nom du bookmaker (ex: "LeoVegas")
            sport_key: Clé sport API (ex: "basketball_nba")
            event_id: ID de l'événement The Odds API
            market: Type de marché (ex: "h2h", "player_points")
            outcome: Outcome spécifique (ex: "Kel'el Ware Over 14.5")
            teams: Tuple (home_team, away_team) pour construction manuelle
            
        Returns:
            URL direct vers le pari ou homepage en fallback
        """
        # Check cache
        cache_key = f"{bookmaker}:{event_id}:{market}:{outcome}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() < cached_data['expires']:
                logger.info(f"✅ Cache hit for {bookmaker}")
                return cached_data['link']
        
        link = None
        
        # 🔥 NIVEAU 1: The Odds API avec deep links
        if bookmaker not in self.canadian_only and bookmaker not in self.small_bookies:
            link = self._try_odds_api_link(bookmaker, sport_key, event_id, market, outcome)
            if link:
                logger.info(f"✅ Level 1 success for {bookmaker}: {link}")
                return self._cache_and_return(cache_key, link)
        
        # 🔥 NIVEAU 2: OpticOdds pour canadiens (TODO)
        if bookmaker in self.canadian_only:
            link = self._try_optic_odds_link(bookmaker, event_id)
            if link:
                logger.info(f"✅ Level 2 success for {bookmaker}: {link}")
                return self._cache_and_return(cache_key, link)
        
        # 🔥 NIVEAU 3: Construction manuelle avec patterns
        if teams:
            link = self._build_manual_link(bookmaker, sport_key, event_id, teams, market, outcome)
            if link:
                logger.info(f"✅ Level 3 success for {bookmaker}: {link}")
                return self._cache_and_return(cache_key, link)
        
        # 🔥 NIVEAU 4: Fallback homepage
        link = self._get_homepage_link(bookmaker)
        logger.warning(f"⚠️ Level 4 fallback for {bookmaker}: {link}")
        return self._cache_and_return(cache_key, link)
    
    def _try_odds_api_link(
        self,
        bookmaker: str,
        sport_key: str,
        event_id: str,
        market: Optional[str] = None,
        outcome: Optional[str] = None
    ) -> Optional[str]:
        """Essaie d'obtenir un lien depuis The Odds API"""
        
        api_key = self.api_keys.get(bookmaker)
        if not api_key:
            return None
        
        # Si c'est un player prop, The Odds API standard ne l'aura pas
        if market and market.startswith('player_'):
            logger.info(f"⚠️ Player props not in standard API for {bookmaker}")
            return None
        
        url = f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",  # EU a plus de deep links
            "markets": market or "h2h",
            "bookmakers": api_key,
            "includeLinks": "true",
            "includeSids": "true"
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            bookmakers = data.get('bookmakers', [])
            if not bookmakers:
                logger.warning(f"No data for {bookmaker} from API")
                return None
            
            book_data = bookmakers[0]
            
            # Priorité: outcome link > market link > event link
            link = None
            sid = book_data.get('sid')
            
            # 1. Essayer de trouver l'outcome exact
            if outcome and market:
                for mkt in book_data.get('markets', []):
                    if mkt.get('key') == market:
                        for out in mkt.get('outcomes', []):
                            if self._match_outcome(out.get('name', ''), outcome):
                                link = out.get('link')
                                if link:
                                    logger.info(f"Found outcome link for {bookmaker}")
                                    break
                        if not link:
                            link = mkt.get('link')
                            if link:
                                logger.info(f"Found market link for {bookmaker}")
                        break
            
            # 2. Sinon prendre le lien de l'event
            if not link:
                link = book_data.get('link')
                if link:
                    logger.info(f"Found event link for {bookmaker}")
            
            # 3. Si pas de lien mais SID, construire avec SID
            if not link and sid:
                link = self._build_link_from_sid(bookmaker, sid)
                if link:
                    logger.info(f"Built link from SID for {bookmaker}")
            
            # Transformer UK → CA
            if link:
                link = self._transform_to_canadian(bookmaker, link)
            
            return link
            
        except Exception as e:
            logger.error(f"Odds API error for {bookmaker}: {e}")
            return None
    
    def _try_optic_odds_link(self, bookmaker: str, event_id: str) -> Optional[str]:
        """Essaie d'obtenir un lien depuis OpticOdds (pour bookmakers canadiens)"""
        
        if not OPTIC_ODDS_KEY:
            logger.info(f"OpticOdds not configured for {bookmaker}")
            return None
        
        # TODO: Implémenter l'appel OpticOdds
        # Pour l'instant, retourner None
        return None
    
    def _build_manual_link(
        self,
        bookmaker: str,
        sport_key: str,
        event_id: str,
        teams: Tuple[str, str],
        market: Optional[str] = None,
        outcome: Optional[str] = None
    ) -> Optional[str]:
        """Construit manuellement un lien avec patterns connus"""
        
        home_team, away_team = teams
        
        # Patterns par bookmaker
        patterns = {
            # ✅ Confirmés fonctionnels
            'LeoVegas': lambda: f"https://www.leovegas.com/en-ca/betting#event/{event_id}",
            'Coolbet': lambda: f"https://www.coolbet.ca/en/sports/match/{event_id}",
            'Betsson': lambda: self._build_betsson_link(sport_key, event_id),
            
            # 🔧 Patterns à tester
            'bet365': lambda: f"https://www.bet365.ca/#/HO/{event_id}",
            'Betway': lambda: f"https://betway.ca/en/sports/evt/{event_id}",
            'Pinnacle': lambda: self._build_pinnacle_link(sport_key, home_team, away_team),
            'bwin': lambda: f"https://sports.bwin.ca/en/sports/{self._sport_to_path(sport_key)}/{event_id}",
            '888sport': lambda: f"https://www.888sport.com/ca/sports/{self._sport_to_path(sport_key)}/{event_id}",
            'BetVictor': lambda: f"https://www.betvictor.com/en-ca/sports/{self._sport_to_path(sport_key)}/{event_id}",
            
            # Bookmakers canadiens
            'BET99': lambda: f"https://bet99.ca/en/sportsbook/event/{event_id}",
            'Sports Interaction': lambda: f"https://sports.sportsinteraction.com/event/{event_id}",
            'TonyBet': lambda: f"https://tonybet.ca/sports/{self._sport_to_path(sport_key)}/{event_id}"
        }
        
        builder = patterns.get(bookmaker)
        if not builder:
            return None
        
        try:
            return builder()
        except Exception as e:
            logger.error(f"Failed to build manual link for {bookmaker}: {e}")
            return None
    
    def _build_link_from_sid(self, bookmaker: str, sid: str) -> Optional[str]:
        """Construit un lien à partir du SID (session ID) de l'API"""
        
        sid_patterns = {
            'bet365': f"https://www.bet365.ca/dl/sportsbookredirect?bs={sid}",
            'Betway': f"https://betway.ca/bet/{sid}",
            'Pinnacle': f"https://www.pinnacle.com/bet/{sid}",
            'bwin': f"https://sports.bwin.ca/bet/{sid}",
            '888sport': f"https://www.888sport.com/bet/{sid}",
            'BetVictor': f"https://www.betvictor.com/bet/{sid}"
        }
        
        return sid_patterns.get(bookmaker)
    
    def _transform_to_canadian(self, bookmaker: str, link: str) -> str:
        """Transforme un lien UK/EU vers un lien canadien"""
        
        if not link:
            return link
        
        transforms = {
            'LeoVegas': lambda l: l.replace('.co.uk', '.com').replace('/en-gb/', '/en-ca/'),
            'Coolbet': lambda l: l.replace('.com', '.ca'),
            'Betsson': lambda l: l.replace('/en/', '/en-ca/'),
            'bet365': lambda l: l.replace('.com', '.ca'),
            'Betway': lambda l: l.replace('.com', '.ca'),
            'bwin': lambda l: l.replace('.com', '.ca'),
            '888sport': lambda l: l.replace('/uk/', '/ca/'),
            'BetVictor': lambda l: l.replace('/en-gb/', '/en-ca/'),
            'Casumo': lambda l: l.replace('/en-gb/', '/en-ca/'),
            'TonyBet': lambda l: l.replace('.com', '.ca')
        }
        
        transform = transforms.get(bookmaker)
        if transform:
            return transform(link)
        return link
    
    def _get_homepage_link(self, bookmaker: str) -> str:
        """Retourne le lien de la homepage du bookmaker (fallback)"""
        
        homepages = {
            '888sport': 'https://www.888sport.com/ca',
            'bet365': 'https://www.bet365.ca',
            'BET99': 'https://bet99.ca/en/sportsbook',
            'Betsson': 'https://www.betsson.com/en-ca/sportsbook',
            'BetVictor': 'https://www.betvictor.com/en-ca/sports',
            'Betway': 'https://betway.ca/en/sports',
            'bwin': 'https://sports.bwin.ca',
            'Casumo': 'https://www.casumo.com/en-ca/sports',
            'Coolbet': 'https://www.coolbet.ca/en/sports',
            'iBet': 'https://www.ibet.ca',
            'Jackpot.bet': 'https://jackpot.bet',
            'LeoVegas': 'https://www.leovegas.com/en-ca/sports',
            'Mise-o-jeu': 'https://miseojeu.espacejeux.com/en/sports',
            'Pinnacle': 'https://www.pinnacle.com/en/sports',
            'Proline': 'https://proline.ca',
            'Sports Interaction': 'https://sports.sportsinteraction.com',
            'Stake': 'https://stake.com/sports',
            'TonyBet': 'https://tonybet.ca'
        }
        
        return homepages.get(bookmaker, f"https://{bookmaker.lower().replace(' ', '')}.com")
    
    def _match_outcome(self, api_outcome: str, target_outcome: str) -> bool:
        """Compare deux outcomes avec tolérance"""
        
        # Normaliser les deux
        api_norm = (api_outcome or '').lower().strip()
        target_norm = (target_outcome or '').lower().strip()
        
        # Match exact
        if api_norm == target_norm:
            return True
        
        # Match partiel (ex: "Kel'el Ware Over 14.5" dans "Kel'el Ware - Over 14.5 Points")
        if target_norm in api_norm or api_norm in target_norm:
            return True
        
        # Extraction des éléments clés
        # Pour "Kel'el Ware Over 14.5"
        parts = re.match(r"(.+?)\s+(over|under)\s+([\d.]+)", target_norm, re.I)
        if parts:
            player = parts.group(1)
            ou = parts.group(2)
            line = parts.group(3)
            
            # Check si tous les éléments sont présents
            if player in api_norm and ou in api_norm and line in api_norm:
                return True
        
        return False
    
    def _build_betsson_link(self, sport_key: str, event_id: str) -> str:
        """Construit un lien Betsson avec le bon sport"""
        
        sport_map = {
            'basketball_nba': 'basketball/nba/nba',
            'americanfootball_nfl': 'american-football/nfl/nfl',
            'icehockey_nhl': 'ice-hockey/nhl/nhl',
            'soccer_epl': 'football/england/premier-league'
        }
        
        sport_path = sport_map.get(sport_key, 'sports')
        return f"https://www.betsson.com/en-ca/sportsbook/{sport_path}?eventId={event_id}"
    
    def _build_pinnacle_link(self, sport_key: str, home: str, away: str) -> str:
        """Construit un lien Pinnacle avec match slug"""
        
        sport_map = {
            'basketball_nba': 'basketball/nba',
            'americanfootball_nfl': 'football/nfl',
            'icehockey_nhl': 'hockey/nhl'
        }
        
        sport_path = sport_map.get(sport_key, 'sports')
        match_slug = f"{self._slugify(away)}-{self._slugify(home)}"
        
        return f"https://www.pinnacle.com/en/{sport_path}/matchups/{match_slug}"
    
    def _sport_to_path(self, sport_key: str) -> str:
        """Convertit une clé sport API vers un path URL"""
        
        sport_map = {
            'basketball_nba': 'basketball/nba',
            'americanfootball_nfl': 'american-football/nfl',
            'icehockey_nhl': 'ice-hockey/nhl',
            'baseball_mlb': 'baseball/mlb',
            'soccer_epl': 'football/england/premier-league'
        }
        
        return sport_map.get(sport_key, sport_key.replace('_', '/'))
    
    def _slugify(self, text: str) -> str:
        """Convertit un texte en slug URL"""
        text = (text or '').lower().strip()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text
    
    def _cache_and_return(self, key: str, link: str) -> str:
        """Met en cache et retourne le lien"""
        self.cache[key] = {
            'link': link,
            'expires': datetime.now() + self.cache_ttl
        }
        return link


# Instance globale
resolver = BookmakerLinkResolver()
