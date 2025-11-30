"""
Hybrid Odds Tracking System - The Odds API + Manual
"""
import logging
import aiohttp
import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)


# Bookmaker coverage mapping
ODDS_API_COVERAGE = {
    # Fully supported bookmakers
    'supported': {
        'Pinnacle': 'pinnacle',
        'Betsson': 'betsson',
        'bet365': 'bet365',
        'Betway': 'betway',
        'bwin': 'bwin',
        'BetVictor': 'betvictor',
        'LeoVegas': 'leovegas',
        '888sport': '888sport',
        'FanDuel': 'fanduel',
        'DraftKings': 'draftkings',
        'Betfair': 'betfair_ex_eu',
        'BetRivers': 'betrivers',
        'Betano': 'betano',
        'Coolbet': 'coolbet'
    },
    
    # Partially supported
    'partial': {
        'TonyBet': 'tonybet',
        'Bally Bet': 'ballybet'
    },
    
    # Not supported - manual tracking only
    'not_supported': [
        'BET99',
        'bet105',
        'Casumo',
        'iBet',
        'Jackpot.bet',
        'Mise-o-jeu',
        'Proline',
        'Sports Interaction',
        'Stake'
    ]
}


class HybridOddsTracker:
    """
    Hybrid odds tracking using The Odds API + manual reporting
    """
    
    def __init__(self):
        self.odds_api_key = os.getenv('ODDS_API_KEY', '')
        self.odds_api_base_url = 'https://api.the-odds-api.com/v4'
        self.casino_mapping = {**ODDS_API_COVERAGE['supported'], **ODDS_API_COVERAGE['partial']}
        self.session = None
        self.db = None
        
    async def initialize(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        self.db = SessionLocal()
        
    async def close(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.db:
            self.db.close()
    
    async def scan_for_odds_changes(self) -> Dict[str, Any]:
        """
        Scan all active bets for odds changes
        Returns summary of changes detected
        """
        logger.info('🔍 Hybrid odds tracking starting...')
        
        if not self.odds_api_key:
            logger.warning("No Odds API key configured - using manual tracking only")
            return await self.manual_tracking_only()
        
        # Get all pending bets from today
        result = self.db.execute(text("""
            SELECT 
                ub.id as bet_id,
                ub.bookmaker,
                ub.expected_profit as american_odds,
                ub.total_stake,
                ub.match_name,
                ub.bet_type,
                de.event_id,
                de.payload
            FROM user_bets ub
            LEFT JOIN drop_events de ON ub.drop_event_id = de.id
            WHERE ub.status = 'pending'
                AND DATE(ub.bet_date) >= CURRENT_DATE - INTERVAL '1 day'
                AND ub.match_date >= CURRENT_DATE
        """))
        
        bets = result.fetchall()
        
        changes = []
        needs_manual = []
        auto_tracked = 0
        
        for bet in bets:
            bookmaker = bet.bookmaker or 'Unknown'
            
            # Check if bookmaker is supported by Odds API
            if bookmaker in self.casino_mapping:
                # AUTO TRACKING via Odds API
                try:
                    current_odds = await self.fetch_from_odds_api(bet)
                    
                    if current_odds and self.has_significant_change(bet, current_odds):
                        change = await self.update_bet_odds(bet, current_odds, 'odds_api')
                        changes.append(change)
                    
                    auto_tracked += 1
                    
                except Exception as e:
                    logger.error(f"Error fetching odds for bet {bet.bet_id}: {e}")
                    needs_manual.append(bet)
            else:
                # MANUAL TRACKING needed
                needs_manual.append(bet)
        
        logger.info(f"✅ Auto-tracked: {auto_tracked} bets")
        logger.info(f"⚠️ Needs manual check: {len(needs_manual)} bets")
        logger.info(f"📊 Odds changed: {len(changes)} bets")
        
        # Recalculate affected parlays if odds changed
        if changes:
            await self.recalculate_affected_parlays(changes)
        
        # Send manual check alerts if many need checking
        if len(needs_manual) > 10:
            await self.send_manual_check_alert(needs_manual)
        
        return {
            'auto_tracked': auto_tracked,
            'odds_changed': len(changes),
            'needs_manual': len(needs_manual),
            'unsupported_bookmakers': self.get_unsupported_bookmakers(needs_manual)
        }
    
    async def fetch_from_odds_api(self, bet) -> Optional[Dict[str, Any]]:
        """Fetch current odds from The Odds API"""
        bookmaker_key = self.casino_mapping.get(bet.bookmaker)
        if not bookmaker_key:
            return None
        
        # Extract sport from bet
        sport_key = self.extract_sport_key(bet)
        if not sport_key:
            return None
        
        try:
            # Build API URL
            url = f"{self.odds_api_base_url}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.odds_api_key,
                'regions': 'us,us2,uk,eu,au',
                'markets': 'h2h,spreads,totals',
                'bookmakers': bookmaker_key,
                'oddsFormat': 'american'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Odds API error: {response.status}")
                    return None
                
                data = await response.json()
                
                # Find matching game
                game = self.find_matching_game(data, bet)
                if not game:
                    return None
                
                # Extract odds for this bet
                return self.extract_bet_odds(game, bet, bookmaker_key)
                
        except Exception as e:
            logger.error(f"Odds API fetch error: {e}")
            return None
    
    def extract_sport_key(self, bet) -> Optional[str]:
        """Extract Odds API sport key from bet"""
        # Try to extract from match name or payload
        match_name = (bet.match_name or '').upper()
        
        sport_mapping = {
            'NBA': 'basketball_nba',
            'NHL': 'icehockey_nhl',
            'NFL': 'americanfootball_nfl',
            'MLB': 'baseball_mlb',
            'MLS': 'soccer_usa_mls',
            'UEFA': 'soccer_uefa_champs_league',
            'EPL': 'soccer_epl',
            'PREMIER LEAGUE': 'soccer_epl',
            'LA LIGA': 'soccer_spain_la_liga',
            'SERIE A': 'soccer_italy_serie_a',
            'BUNDESLIGA': 'soccer_germany_bundesliga',
            'LIGUE 1': 'soccer_france_ligue_one'
        }
        
        for key, value in sport_mapping.items():
            if key in match_name:
                return value
        
        return None
    
    def find_matching_game(self, api_data: List[Dict], bet) -> Optional[Dict]:
        """Find the game matching this bet in API response"""
        if not bet.match_name:
            return None
        
        # Extract team names from bet
        teams = self.extract_teams_from_match(bet.match_name)
        if not teams:
            return None
        
        # Search for matching game in API data
        for game in api_data:
            home_team = game.get('home_team', '').lower()
            away_team = game.get('away_team', '').lower()
            
            # Check if teams match (fuzzy match)
            if (self.fuzzy_match_team(teams[0], home_team) and 
                self.fuzzy_match_team(teams[1], away_team)) or \
               (self.fuzzy_match_team(teams[0], away_team) and 
                self.fuzzy_match_team(teams[1], home_team)):
                return game
        
        return None
    
    def extract_teams_from_match(self, match_name: str) -> Optional[Tuple[str, str]]:
        """Extract team names from match string"""
        import re
        
        # Common separators
        separators = [' vs ', ' @ ', ' - ', ' v ']
        
        for sep in separators:
            if sep in match_name:
                parts = match_name.split(sep)
                if len(parts) == 2:
                    return (parts[0].strip().lower(), parts[1].strip().lower())
        
        return None
    
    def fuzzy_match_team(self, team1: str, team2: str) -> bool:
        """Fuzzy match team names"""
        # Simple fuzzy match - can be improved
        team1_words = set(team1.lower().split())
        team2_words = set(team2.lower().split())
        
        # Check if significant overlap
        common = team1_words & team2_words
        if len(common) >= 1:  # At least one word in common
            return True
        
        # Check if one contains the other
        if team1 in team2 or team2 in team1:
            return True
        
        return False
    
    def extract_bet_odds(self, game: Dict, bet, bookmaker_key: str) -> Optional[Dict]:
        """Extract specific bet odds from game data"""
        bookmakers = game.get('bookmakers', [])
        
        # Find the specific bookmaker
        bookmaker_data = None
        for bm in bookmakers:
            if bm.get('key') == bookmaker_key:
                bookmaker_data = bm
                break
        
        if not bookmaker_data:
            return None
        
        # Extract based on bet type
        bet_type = (bet.bet_type or '').lower()
        
        if 'arbitrage' in bet_type or 'arb' in bet_type:
            # For arbitrage, get h2h market
            markets = bookmaker_data.get('markets', [])
            for market in markets:
                if market.get('key') == 'h2h':
                    outcomes = market.get('outcomes', [])
                    if outcomes:
                        # Return first outcome odds
                        return {
                            'american_odds': outcomes[0].get('price'),
                            'decimal_odds': self.american_to_decimal(outcomes[0].get('price')),
                            'line': None
                        }
        
        elif 'middle' in bet_type:
            # For middle, check spreads or totals
            markets = bookmaker_data.get('markets', [])
            for market in markets:
                if market.get('key') in ['spreads', 'totals']:
                    outcomes = market.get('outcomes', [])
                    if outcomes:
                        return {
                            'american_odds': outcomes[0].get('price'),
                            'decimal_odds': self.american_to_decimal(outcomes[0].get('price')),
                            'line': outcomes[0].get('point')
                        }
        
        return None
    
    def has_significant_change(self, old_bet, new_odds: Dict) -> bool:
        """Check if odds changed significantly (2%+)"""
        try:
            old_odds = float(old_bet.american_odds or 100)
            new_odds_val = float(new_odds.get('american_odds', 100))
            
            old_decimal = self.american_to_decimal(old_odds)
            new_decimal = new_odds.get('decimal_odds', self.american_to_decimal(new_odds_val))
            
            change_percent = abs((new_decimal - old_decimal) / old_decimal) * 100
            
            return change_percent >= 2.0
            
        except Exception as e:
            logger.error(f"Error calculating odds change: {e}")
            return False
    
    async def update_bet_odds(self, bet, new_odds: Dict, source: str) -> Dict:
        """Update bet with new odds and log change"""
        try:
            old_odds = float(bet.american_odds or 100)
            new_odds_val = float(new_odds.get('american_odds', 100))
            
            old_decimal = self.american_to_decimal(old_odds)
            new_decimal = new_odds.get('decimal_odds', self.american_to_decimal(new_odds_val))
            
            change_percent = ((new_decimal - old_decimal) / old_decimal) * 100
            
            # Log odds change
            self.db.execute(text("""
                INSERT INTO odds_history (
                    bet_id, drop_event_id, old_american_odds, new_american_odds,
                    old_decimal_odds, new_decimal_odds, change_percent, source
                ) VALUES (:bet_id, :drop_id, :old_am, :new_am, :old_dec, :new_dec, :change, :source)
            """), {
                'bet_id': bet.bet_id,
                'drop_id': bet.event_id if hasattr(bet, 'event_id') else None,
                'old_am': int(old_odds),
                'new_am': int(new_odds_val),
                'old_dec': float(old_decimal),
                'new_dec': float(new_decimal),
                'change': float(change_percent),
                'source': source
            })
            
            self.db.commit()
            
            logger.info(f"📊 {bet.bookmaker} odds updated: {int(old_odds)} → {int(new_odds_val)}")
            
            return {
                'bet_id': bet.bet_id,
                'bookmaker': bet.bookmaker,
                'old_odds': int(old_odds),
                'new_odds': int(new_odds_val),
                'change_percent': change_percent
            }
            
        except Exception as e:
            logger.error(f"Error updating odds: {e}")
            self.db.rollback()
            return {}
    
    async def recalculate_affected_parlays(self, changes: List[Dict]):
        """Recalculate parlays affected by odds changes"""
        # This would recalculate parlay metrics
        # For now, just log
        logger.info(f"🔄 Would recalculate parlays affected by {len(changes)} odds changes")
    
    async def send_manual_check_alert(self, bets):
        """Alert about bets needing manual odds check"""
        by_bookmaker = {}
        for bet in bets:
            bm = bet.bookmaker or 'Unknown'
            if bm not in by_bookmaker:
                by_bookmaker[bm] = 0
            by_bookmaker[bm] += 1
        
        message = f"""
⚠️ MANUAL ODDS CHECK NEEDED

{len(bets)} bets from unsupported bookmakers need verification:

{chr(10).join(f'🏢 {book}: {count} bets' for book, count in by_bookmaker.items())}

Top unsupported: BET99, Mise-o-jeu, Sports Interaction

Users will be prompted to report odds changes via /report_odds
        """
        
        logger.info(message)
    
    def get_unsupported_bookmakers(self, needs_manual) -> List[str]:
        """Get list of unsupported bookmakers from bets"""
        bookmakers = set()
        for bet in needs_manual:
            bm = bet.bookmaker or 'Unknown'
            if bm not in self.casino_mapping:
                bookmakers.add(bm)
        return list(bookmakers)
    
    async def manual_tracking_only(self) -> Dict[str, Any]:
        """Fallback when no API key configured"""
        logger.info("Running in manual tracking mode (no API key)")
        
        # Just return summary
        return {
            'auto_tracked': 0,
            'odds_changed': 0,
            'needs_manual': 'all',
            'mode': 'manual_only'
        }
    
    def american_to_decimal(self, american: float) -> float:
        """Convert American odds to decimal"""
        if american > 0:
            return (american / 100) + 1
        else:
            return (100 / abs(american)) + 1
    
    def decimal_to_american(self, decimal: float) -> int:
        """Convert decimal odds to American"""
        if decimal >= 2.0:
            return int((decimal - 1) * 100)
        else:
            return int(-100 / (decimal - 1))


class ManualOddsReporter:
    """
    Handle manual odds reporting from users
    """
    
    def __init__(self):
        self.db = SessionLocal()
        
    async def handle_user_odds_report(self, user_id: int, bet_id: int, 
                                     new_american_odds: int) -> Dict[str, Any]:
        """
        Process user-reported odds change
        """
        try:
            # Get current bet
            result = self.db.execute(text("""
                SELECT * FROM user_bets WHERE id = :bet_id AND user_id = :user_id
            """), {'bet_id': bet_id, 'user_id': user_id})
            
            bet = result.fetchone()
            if not bet:
                return {'error': 'Bet not found'}
            
            old_odds = float(bet.expected_profit or 100)  # Using expected_profit as odds
            change_percent = ((new_american_odds - old_odds) / old_odds) * 100
            
            # Log the change
            self.db.execute(text("""
                INSERT INTO odds_history (
                    bet_id, old_american_odds, new_american_odds,
                    old_decimal_odds, new_decimal_odds, change_percent, source
                ) VALUES (:bet_id, :old, :new, :old_dec, :new_dec, :change, 'user_reported')
            """), {
                'bet_id': bet_id,
                'old': int(old_odds),
                'new': new_american_odds,
                'old_dec': self.american_to_decimal(old_odds),
                'new_dec': self.american_to_decimal(new_american_odds),
                'change': change_percent
            })
            
            # Update bet (store in expected_profit for now)
            self.db.execute(text("""
                UPDATE user_bets 
                SET expected_profit = :new_odds,
                    updated_at = NOW()
                WHERE id = :bet_id
            """), {'new_odds': new_american_odds, 'bet_id': bet_id})
            
            self.db.commit()
            
            return {
                'success': True,
                'old_odds': int(old_odds),
                'new_odds': new_american_odds,
                'change_percent': round(change_percent, 2),
                'message': f"Odds updated: {int(old_odds)} → {new_american_odds}"
            }
            
        except Exception as e:
            logger.error(f"Error in manual odds report: {e}")
            self.db.rollback()
            return {'error': str(e)}
    
    def american_to_decimal(self, american: float) -> float:
        """Convert American odds to decimal"""
        if american > 0:
            return (american / 100) + 1
        else:
            return (100 / abs(american)) + 1
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
