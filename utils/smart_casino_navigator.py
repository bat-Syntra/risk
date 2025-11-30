"""
Smart Casino Navigator - Utilise The Odds API pour enrichir les données
puis navigue intelligemment sur les casinos québécois
"""

import os
import re
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote, urljoin
from playwright.async_api import async_playwright

class SmartCasinoNavigator:
    """
    Stratégie intelligente:
    1. Utilise The Odds API pour obtenir les données exactes du match
    2. Construit des URLs directes pour les casinos québécois
    3. Pas de screenshots, pas de Claude Vision = 0$ de coût!
    """
    
    # Mapping intelligent des casinos québécois
    QUEBEC_CASINOS = {
        'BET99': {
            'base': 'https://bet99.ca',
            'patterns': {
                'NBA': '/en/sportsbook/basketball/usa/nba',
                'NHL': '/en/sportsbook/ice-hockey/usa/nhl', 
                'NFL': '/en/sportsbook/american-football/usa/nfl',
                'search': '/en/sportsbook/search?query={query}'
            },
            'player_props_path': '#player-props'
        },
        'Coolbet': {
            'base': 'https://www.coolbet.com',
            'patterns': {
                'NBA': '/en/sports/basketball/nba',
                'NHL': '/en/sports/ice-hockey/nhl',
                'NFL': '/en/sports/american-football/nfl',
                'search': '/en/sports/search/{query}'
            },
            'player_props_path': '#player-markets'
        },
        'Sports Interaction': {
            'base': 'https://www.sportsinteraction.com',
            'patterns': {
                'NBA': '/betting/basketball/usa/nba',
                'NHL': '/betting/hockey/nhl',
                'NFL': '/betting/football/nfl',
                'search': '/betting/search?q={query}'
            },
            'player_props_path': '#props'
        },
        'Betsson': {
            'base': 'https://www.betsson.com',
            'patterns': {
                'NBA': '/en/sportsbook/basketball/nba',
                'NHL': '/en/sportsbook/ice-hockey/nhl',
                'NFL': '/en/sportsbook/american-football/nfl',
                'search': '/en/sportsbook/search?q={query}'
            }
        },
        'Mise-o-jeu': {
            'base': 'https://www.lotoquebec.com',
            'patterns': {
                'NBA': '/en/sports-betting/basketball/nba',
                'NHL': '/en/sports-betting/hockey/nhl',
                'NFL': '/en/sports-betting/football/nfl',
                'search': '/en/sports-betting/search?q={query}'
            }
        },
        'Pinnacle': {
            'base': 'https://www.pinnacle.com',
            'patterns': {
                'NBA': '/en/basketball/nba/matchups',
                'NHL': '/en/hockey/nhl/matchups',
                'NFL': '/en/american-football/nfl/matchups'
            }
        },
        'bet365': {
            'base': 'https://www.bet365.ca',
            'patterns': {
                # bet365 uses special hash routing
                'NBA': '/#/AC/B18/',  
                'NHL': '/#/AC/B17/',
                'NFL': '/#/AC/B12/'
            }
        },
        'Betway': {
            'base': 'https://betway.ca',
            'patterns': {
                'NBA': '/en/sports/grp/basketball/nba',
                'NHL': '/en/sports/grp/ice-hockey/nhl',
                'NFL': '/en/sports/grp/american-football/nfl'
            }
        },
        'LeoVegas': {
            'base': 'https://www.leovegas.com',
            'patterns': {
                'NBA': '/en-ca/betting/basketball/nba',
                'NHL': '/en-ca/betting/ice-hockey/nhl',
                'NFL': '/en-ca/betting/american-football/nfl'
            }
        },
        'TonyBet': {
            'base': 'https://tonybet.com',
            'patterns': {
                'NBA': '/ca/sportsbook/basketball-usa-nba',
                'NHL': '/ca/sportsbook/ice-hockey-usa-nhl',
                'NFL': '/ca/sportsbook/american-football-usa-nfl'
            }
        },
        'Proline+': {
            'base': 'https://www.proline.ca',
            'patterns': {
                'NBA': '/sports/basketball/nba',
                'NHL': '/sports/hockey/nhl',
                'NFL': '/sports/football/nfl'
            }
        }
    }
    
    def __init__(self, odds_api_key: str = None):
        self.odds_api_key = odds_api_key or os.getenv('ODDS_API_KEY')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def parse_arbitrage_data(self, message_text: str) -> Dict[str, Any]:
        """
        Parse le message d'arbitrage pour extraire les infos
        
        Example input:
        🏟️ Miami Heat vs Milwaukee Bucks
        🏀 NBA - Player Assists : Myles Turner Over 2.5/Under 2.5
        🕐 Wednesday, Nov 26 - 07:40 PM ET
        """
        
        data = {}
        
        # Extract teams
        teams_match = re.search(r'🏟️\s*([^vs]+)\s+vs\s+(.+)', message_text)
        if teams_match:
            data['home_team'] = teams_match.group(1).strip()
            data['away_team'] = teams_match.group(2).strip()
        
        # Extract sport and market
        sport_match = re.search(r'🏀\s*(\w+)\s*-\s*(.+?):', message_text)
        if sport_match:
            data['sport'] = sport_match.group(1).strip()
            data['market_type'] = sport_match.group(2).strip()
        
        # Extract player and line
        player_match = re.search(r':\s*([A-Za-z\s]+)\s+(Over|Under)\s+([\d.]+)', message_text)
        if player_match:
            data['player'] = player_match.group(1).strip()
            data['line'] = float(player_match.group(3))
        
        # Extract date/time
        time_match = re.search(r'🕐\s*([^-]+)\s*-\s*(.+?)(?:\(|$)', message_text)
        if time_match:
            data['game_date'] = time_match.group(1).strip()
            data['game_time'] = time_match.group(2).strip()
        
        # Extract casinos and odds
        bet99_match = re.search(r'\[BET99\].*?([\+\-]\d+)', message_text)
        coolbet_match = re.search(r'\[Coolbet\].*?([\+\-]\d+)', message_text)
        
        if bet99_match:
            data['bet1'] = {
                'casino': 'BET99',
                'odds': bet99_match.group(1)
            }
        if coolbet_match:
            data['bet2'] = {
                'casino': 'Coolbet', 
                'odds': coolbet_match.group(1)
            }
            
        return data
    
    async def enrich_with_odds_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Utilise The Odds API pour enrichir avec les vraies données du match
        """
        
        if not self.odds_api_key:
            # Pas d'API key, on retourne les données brutes
            return data
            
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Map sport to API format
        sport_map = {
            'NBA': 'basketball_nba',
            'NHL': 'icehockey_nhl',
            'NFL': 'americanfootball_nfl',
            'MLB': 'baseball_mlb',
            'UFC': 'mma_ufc'
        }
        
        sport_key = sport_map.get(data.get('sport', 'NBA'), 'basketball_nba')
        
        # Get upcoming events
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events"
        params = {'apiKey': self.odds_api_key}
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    events = await resp.json()
                    
                    # Find best match
                    home = data.get('home_team', '').lower()
                    away = data.get('away_team', '').lower()
                    
                    for event in events:
                        event_home = event.get('home_team', '').lower()
                        event_away = event.get('away_team', '').lower()
                        
                        # Flexible matching
                        if (home in event_home or event_home in home) and \
                           (away in event_away or event_away in away):
                            # Enrich data
                            data['event_id'] = event.get('id')
                            data['exact_home_team'] = event.get('home_team')
                            data['exact_away_team'] = event.get('away_team')
                            data['commence_time'] = event.get('commence_time')
                            data['sport_key'] = event.get('sport_key')
                            break
        except:
            pass
            
        return data
    
    def build_direct_url(
        self,
        casino: str,
        sport: str,
        home_team: str = None,
        away_team: str = None,
        player: str = None,
        market_type: str = None
    ) -> str:
        """
        Construit l'URL directe vers le bet sur le casino
        """
        
        casino_config = self.QUEBEC_CASINOS.get(casino)
        if not casino_config:
            return None
            
        base = casino_config['base']
        patterns = casino_config.get('patterns', {})
        
        # Try sport-specific pattern first
        sport_path = patterns.get(sport)
        if sport_path:
            url = base + sport_path
            
            # Add search query if we have teams
            if home_team and away_team:
                if 'search' in patterns:
                    search_pattern = patterns['search']
                    query = f"{away_team} {home_team}"
                    if player:
                        query += f" {player}"
                    search_url = base + search_pattern.format(query=quote(query))
                    return search_url
                else:
                    # Add as URL params
                    url += f"?teams={quote(f'{away_team} vs {home_team}')}"
                    
            # Add player props anchor if available
            if player and market_type:
                props_path = casino_config.get('player_props_path')
                if props_path:
                    url += props_path
                    
            return url
            
        # Fallback to search
        if 'search' in patterns:
            query = f"{sport} {home_team} {away_team}"
            if player:
                query += f" {player}"
            return base + patterns['search'].format(query=quote(query))
            
        # Last resort - just the base
        return base
    
    async def find_bet_links(self, arbitrage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trouve les liens directs sans screenshots ni IA
        
        1. Parse les données
        2. Enrichit avec Odds API si disponible  
        3. Construit les URLs directes
        """
        
        # Enrichir avec Odds API
        enriched = await self.enrich_with_odds_api(arbitrage_data)
        
        # Build URLs for both casinos
        bet1_casino = enriched['bet1']['casino']
        bet2_casino = enriched['bet2']['casino']
        
        bet1_url = self.build_direct_url(
            casino=bet1_casino,
            sport=enriched.get('sport'),
            home_team=enriched.get('exact_home_team', enriched.get('home_team')),
            away_team=enriched.get('exact_away_team', enriched.get('away_team')),
            player=enriched.get('player'),
            market_type=enriched.get('market_type')
        )
        
        bet2_url = self.build_direct_url(
            casino=bet2_casino,
            sport=enriched.get('sport'),
            home_team=enriched.get('exact_home_team', enriched.get('home_team')),
            away_team=enriched.get('exact_away_team', enriched.get('away_team')),
            player=enriched.get('player'),
            market_type=enriched.get('market_type')
        )
        
        return {
            'bet1_link': bet1_url,
            'bet2_link': bet2_url,
            'enriched_data': enriched,
            'success': bool(bet1_url and bet2_url)
        }
    
    async def verify_odds_smart(
        self,
        bet1_link: str,
        bet2_link: str,
        player: str,
        line: float,
        expected_odds1: str,
        expected_odds2: str
    ) -> Dict[str, Any]:
        """
        Vérifie les cotes en naviguant intelligemment (sans screenshots)
        Utilise Playwright pour extraire les cotes du DOM
        """
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Verify both in parallel
            results = await asyncio.gather(
                self._verify_single_odd(browser, bet1_link, player, line, expected_odds1),
                self._verify_single_odd(browser, bet2_link, player, line, expected_odds2)
            )
            
            await browser.close()
            
            return {
                'bet1': results[0],
                'bet2': results[1],
                'still_valid': results[0]['match'] and results[1]['match']
            }
    
    async def _verify_single_odd(
        self,
        browser,
        url: str,
        player: str,
        line: float,
        expected_odds: str
    ) -> Dict[str, Any]:
        """
        Vérifie une seule cote en extrayant du DOM
        """
        
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle')
            
            # Cherche le joueur et la ligne
            player_elements = await page.query_selector_all(f'text={player}')
            
            for elem in player_elements:
                # Cherche la ligne à proximité
                parent = await elem.evaluate_handle('el => el.parentElement.parentElement')
                text = await parent.inner_text()
                
                if str(line) in text:
                    # Extrait les cotes (cherche pattern +123 ou -123)
                    import re
                    odds_pattern = r'([\+\-]\d{3,4})'
                    matches = re.findall(odds_pattern, text)
                    
                    if matches:
                        current_odds = matches[0]
                        
                        # Compare
                        match = self._odds_match(expected_odds, current_odds)
                        
                        await page.close()
                        return {
                            'found': True,
                            'current_odds': current_odds,
                            'match': match
                        }
            
            await page.close()
            return {'found': False, 'current_odds': None, 'match': False}
            
        except Exception as e:
            await page.close()
            return {'found': False, 'error': str(e), 'match': False}
    
    def _odds_match(self, expected: str, current: str, tolerance: int = 10) -> bool:
        """Check if odds match within tolerance"""
        try:
            exp_val = int(expected.replace('+', '').replace('-', ''))
            cur_val = int(current.replace('+', '').replace('-', ''))
            
            # Check same sign
            if ('+' in expected) != ('+' in current) and ('-' in expected) != ('-' in current):
                return False
                
            return abs(exp_val - cur_val) <= tolerance
        except:
            return False


# Example usage for your bot
async def handle_arbitrage_smart(message_text: str):
    """
    Exemple d'intégration dans ton bot
    """
    
    async with SmartCasinoNavigator(odds_api_key='YOUR_KEY_OPTIONAL') as nav:
        # Parse from message
        data = nav.parse_arbitrage_data(message_text)
        
        # Add bet info
        data['bet1'] = {'casino': 'BET99', 'odds': '+335'}
        data['bet2'] = {'casino': 'Coolbet', 'odds': '-256'}
        data['player'] = 'Myles Turner'
        data['sport'] = 'NBA'
        
        # Get direct links (instant, no cost)
        result = await nav.find_bet_links(data)
        
        print(f"BET99 Link: {result['bet1_link']}")
        print(f"Coolbet Link: {result['bet2_link']}")
        
        # Only verify if user asks
        if user_clicks_verify:
            verify_result = await nav.verify_odds_smart(
                bet1_link=result['bet1_link'],
                bet2_link=result['bet2_link'],
                player=data['player'],
                line=2.5,
                expected_odds1='+335',
                expected_odds2='-256'
            )
            
            print(f"Still valid: {verify_result['still_valid']}")
