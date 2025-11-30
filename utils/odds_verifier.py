#!/usr/bin/env python3
"""
Real-time Odds Verification using The Odds API
Checks if parlay odds are still valid or have changed
"""
import os
import json
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class OddsVerifier:
    
    def __init__(self):
        self.api_key = os.getenv('ODDS_API_KEY')
        if not self.api_key:
            raise ValueError("ODDS_API_KEY not found!")
        
        self.base_url = "https://api.the-odds-api.com/v4"
    
    async def verify_parlay_odds(self, parlay_legs):
        """
        Verify if parlay legs still have the same odds
        
        Args:
            parlay_legs: List of legs with match, market, odds info
            
        Returns:
            dict with verification results
        """
        results = {
            'total_legs': len(parlay_legs),
            'verified_legs': 0,
            'legs_changed': 0,
            'legs_better': 0,
            'legs_worse': 0,
            'legs_unavailable': 0,
            'details': [],
            'overall_status': 'unknown'
        }
        
        async with aiohttp.ClientSession() as session:
            for leg in parlay_legs:
                leg_result = await self.verify_single_leg(session, leg)
                results['details'].append(leg_result)
                
                if leg_result['status'] == 'verified':
                    results['verified_legs'] += 1
                elif leg_result['status'] == 'better':
                    results['legs_better'] += 1
                elif leg_result['status'] == 'worse':
                    results['legs_worse'] += 1
                elif leg_result['status'] == 'unavailable':
                    results['legs_unavailable'] += 1
                
                if leg_result['status'] in ['better', 'worse']:
                    results['legs_changed'] += 1
        
        # Determine overall status
        if results['legs_unavailable'] > 0:
            results['overall_status'] = 'some_unavailable'
        elif results['legs_worse'] > 0:
            results['overall_status'] = 'odds_worse'
        elif results['legs_better'] > 0:
            results['overall_status'] = 'odds_better'
        elif results['verified_legs'] == results['total_legs']:
            results['overall_status'] = 'all_good'
        else:
            results['overall_status'] = 'changed'
        
        return results
    
    async def verify_single_leg(self, session, leg):
        """Verify a single leg of the parlay"""
        
        # Extract info from leg
        match = leg.get('match', '')
        sport = leg.get('sport', 'NBA')
        original_odds = leg.get('odds', 0)
        market_type = leg.get('market', '')
        bookmaker = leg.get('bookmaker', 'bet365')
        
        # Detect if it's a player prop
        is_player_prop = any(word in market_type.upper() for word in ['PLAYER', 'PASSING', 'RUSHING', 'RECEIVING', 'POINTS', 'REBOUNDS', 'ASSISTS'])
        
        # Map sport to API sport key
        sport_key = self.map_sport_to_api(sport)
        
        # If sport not recognized, can't verify
        if sport_key is None:
            return {
                'leg': leg,
                'status': 'unavailable',
                'message': f"Sport non supporté pour vérification automatique",
                'original_odds': original_odds,
                'note': f'Unknown sport: {sport}'
            }
        
        # Try to fetch current odds
        try:
            # Different endpoint for player props
            if is_player_prop:
                # Player props not available for automatic verification
                return {
                    'leg': leg,
                    'status': 'unavailable',
                    'message': f"Player prop - Vérification manuelle nécessaire",
                    'original_odds': original_odds,
                    'note': 'Player props not available via API'
                }
            
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us,us2,uk,eu',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'decimal',
                'bookmakers': self.map_bookmaker_to_api(bookmaker)
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {
                        'leg': leg,
                        'status': 'error',
                        'message': f"API error: {response.status}"
                    }
                
                events = await response.json()
                
                # Debug: Log what we received
                print(f"📊 API returned {len(events)} events for {sport_key}")
                
                # Find matching event
                current_odds = self.find_matching_odds(events, match, market_type, bookmaker)
                
                if current_odds is None:
                    return {
                        'leg': leg,
                        'status': 'unavailable',
                        'message': f"Non trouvé - Vérification manuelle recommandée",
                        'original_odds': original_odds,
                        'events_scanned': len(events)
                    }
                
                # Compare odds
                change_pct = ((current_odds - original_odds) / original_odds) * 100
                
                if abs(change_pct) < 2:  # Within 2% = same
                    status = 'verified'
                    message = f"✅ Unchanged ({current_odds})"
                elif change_pct > 0:  # Better odds
                    status = 'better'
                    message = f"📈 Better! {original_odds} → {current_odds} (+{change_pct:.1f}%)"
                else:  # Worse odds
                    status = 'worse'
                    message = f"📉 Worse! {original_odds} → {current_odds} ({change_pct:.1f}%)"
                
                return {
                    'leg': leg,
                    'status': status,
                    'message': message,
                    'original_odds': original_odds,
                    'current_odds': current_odds,
                    'change_pct': change_pct
                }
                
        except Exception as e:
            return {
                'leg': leg,
                'status': 'error',
                'message': f"Error: {str(e)}",
                'original_odds': original_odds
            }
    
    def find_matching_odds(self, events, match, market_type, bookmaker):
        """Find odds for specific match and market"""
        
        # Normalize match name for comparison
        match_normalized = match.lower().replace('@', 'vs').replace(' at ', ' vs ')
        
        for event in events:
            # Check if event matches
            home = event.get('home_team', '').lower()
            away = event.get('away_team', '').lower()
            
            event_match = f"{away} vs {home}"
            
            if home not in match_normalized and away not in match_normalized:
                continue
            
            # Found matching event, now find odds
            for book in event.get('bookmakers', []):
                if book.get('key', '') != self.map_bookmaker_to_api(bookmaker):
                    continue
                
                # Find matching market
                for market in book.get('markets', []):
                    # Match market type
                    market_key = market.get('key', '')
                    
                    if ('ML' in market_type.upper() or 'MONEYLINE' in market_type.upper()) and market_key == 'h2h':
                        # Return first outcome (simplified)
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            return outcomes[0].get('price', 0)
                    
                    elif ('SPREAD' in market_type.upper() or 'HANDICAP' in market_type.upper()) and market_key == 'spreads':
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            return outcomes[0].get('price', 0)
                    
                    elif ('OVER' in market_type.upper() or 'UNDER' in market_type.upper() or 'TOTAL' in market_type.upper()) and market_key == 'totals':
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            # Match over/under
                            for outcome in outcomes:
                                if 'OVER' in market_type.upper() and outcome.get('name', '').lower() == 'over':
                                    return outcome.get('price', 0)
                                elif 'UNDER' in market_type.upper() and outcome.get('name', '').lower() == 'under':
                                    return outcome.get('price', 0)
        
        return None
    
    def map_sport_to_api(self, sport):
        """Map display sport to API key"""
        sport_upper = sport.upper()
        
        # Direct mappings
        mapping = {
            'NBA': 'basketball_nba',
            'NHL': 'icehockey_nhl',
            'NFL': 'americanfootball_nfl',
            'MLB': 'baseball_mlb',
            'MLS': 'soccer_usa_mls',
            'NCAAB': 'basketball_ncaab',
            'NCAAF': 'americanfootball_ncaaf',
            'EPL': 'soccer_epl',
            'PREMIER LEAGUE': 'soccer_epl',
            'LA LIGA': 'soccer_spain_la_liga',
            'BUNDESLIGA': 'soccer_germany_bundesliga',
            'SERIE A': 'soccer_italy_serie_a',
            'LIGUE 1': 'soccer_france_ligue_one',
            'UEFA CHAMPIONS LEAGUE': 'soccer_uefa_champs_league',
            'CHAMPIONS LEAGUE': 'soccer_uefa_champs_league',
            'ATP': 'tennis_atp',
            'WTA': 'tennis_wta'
        }
        
        # Check direct mapping
        if sport_upper in mapping:
            return mapping[sport_upper]
        
        # Check if league name contains keywords
        if 'LA LIGA' in sport_upper or 'SPAIN' in sport_upper:
            return 'soccer_spain_la_liga'
        elif 'PREMIER' in sport_upper or 'EPL' in sport_upper or 'ENGLAND' in sport_upper:
            return 'soccer_epl'
        elif 'BUNDESLIGA' in sport_upper or 'GERMANY' in sport_upper:
            return 'soccer_germany_bundesliga'
        elif 'SERIE A' in sport_upper or 'ITALY' in sport_upper:
            return 'soccer_italy_serie_a'
        elif 'LIGUE 1' in sport_upper or 'FRANCE' in sport_upper:
            return 'soccer_france_ligue_one'
        elif 'CHAMPIONS' in sport_upper or 'UEFA' in sport_upper:
            return 'soccer_uefa_champs_league'
        elif 'NBA' in sport_upper or 'BASKETBALL' in sport_upper:
            return 'basketball_nba'
        elif 'NHL' in sport_upper or 'HOCKEY' in sport_upper:
            return 'icehockey_nhl'
        elif 'NFL' in sport_upper or 'FOOTBALL' in sport_upper and 'AMERICAN' in sport_upper:
            return 'americanfootball_nfl'
        elif 'NCAAF' in sport_upper:
            return 'americanfootball_ncaaf'
        elif 'SOCCER' in sport_upper or 'FOOTBALL' in sport_upper:
            return 'soccer_epl'  # Default soccer
        else:
            # Unknown - return None so we can detect it
            print(f"⚠️ Unknown sport mapping: {sport}")
            return None
    
    def map_bookmaker_to_api(self, bookmaker):
        """Map display bookmaker to API key"""
        mapping = {
            'bet365': 'bet365',
            'Pinnacle': 'pinnacle',
            'Betsson': 'betsson',
            'Sports Interaction': 'sportsbetting',
            'LeoVegas': 'leovegas',
            'Coolbet': 'coolbet',
            'BetVictor': 'betvictor',
            '888sport': '888sport',
            'Betway': 'betway',
            'bwin': 'bwin',
            'Casumo': 'casumo',
            'TonyBet': 'tonybet',
            'Stake': 'stake',
            'BET99': 'bet365',  # Pas dans API
            'iBet': 'bet365',  # Pas dans API
            'Mise-o-jeu': 'bet365',  # Pas dans API
            'Proline': 'bet365',  # Pas dans API
            'Jackpot.bet': 'bet365'  # Pas dans API
        }
        return mapping.get(bookmaker, 'bet365')
