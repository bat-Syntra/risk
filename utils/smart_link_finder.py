"""
Smart Link Finder - Hybride avec cache persistant
1. Check le cache
2. Essaie gratuitement
3. Si échec → Claude Vision
4. Sauvegarde pour la prochaine fois!
"""

import os
import json
import re
import asyncio
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from utils.best_effort_links import BestEffortLinks
from find_real_links_with_ai import AIBetFinder

class SmartLinkFinder:
    """
    Système intelligent avec cache persistant
    Apprend et s'améliore avec le temps!
    """
    
    def __init__(self, anthropic_key: str = None, cache_dir: str = "link_cache"):
        self.has_ai = bool(anthropic_key)
        self.ai_finder = AIBetFinder(anthropic_key) if self.has_ai else None
        self.best_effort = BestEffortLinks()
        
        # Cache persistant
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Fichiers de cache par casino
        self.cache_files = {
            'matches': self.cache_dir / 'matches.json',
            'patterns': self.cache_dir / 'url_patterns.json',
            'events': self.cache_dir / 'event_ids.json'
        }
        
        # Charge le cache existant
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Charge le cache depuis les fichiers"""
        cache = {
            'matches': {},  # Hash du match → event_id
            'patterns': {},  # Casino → patterns d'URL
            'events': {}     # Event_id → détails
        }
        
        for key, file_path in self.cache_files.items():
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        cache[key] = json.load(f)
                except:
                    pass
        
        return cache
    
    def _save_cache(self):
        """Sauvegarde le cache sur disque"""
        for key, file_path in self.cache_files.items():
            with open(file_path, 'w') as f:
                json.dump(self.cache[key], f, indent=2, default=str)
    
    def _get_match_hash(self, casino: str, team1: str, team2: str, date: str = None) -> str:
        """
        Génère un hash unique pour un match
        """
        # Normalise les noms
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        teams = sorted([t1, t2])  # Ordre consistent
        
        # Hash incluant casino et date approximative
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        match_str = f"{casino}_{teams[0]}_{teams[1]}_{date_str}"
        
        return hashlib.md5(match_str.encode()).hexdigest()[:12]
    
    async def find_bet_link(
        self,
        casino: str,
        sport: str,
        team1: str,
        team2: str,
        bet_team: str,
        market: str = "Moneyline",
        force_ai: bool = False
    ) -> Dict[str, Any]:
        """
        Trouve le lien avec stratégie hybride
        
        1. Check cache
        2. Essaie patterns connus
        3. Essaie best effort
        4. Si échec → Claude Vision
        5. Sauvegarde résultat
        """
        
        print(f"\n🔍 Recherche pour {casino}: {team1} vs {team2}")
        
        # Étape 1: Check le cache
        match_hash = self._get_match_hash(casino, team1, team2)
        
        if match_hash in self.cache['matches'] and not force_ai:
            event_id = self.cache['matches'][match_hash]
            cached_url = self._build_url_from_pattern(casino, event_id)
            
            if cached_url:
                print(f"   ✅ Trouvé dans le cache! Event ID: {event_id}")
                return {
                    'success': True,
                    'url': cached_url,
                    'event_id': event_id,
                    'method': 'cache',
                    'cost': 0
                }
        
        # Étape 2: Essaie les patterns connus
        if casino in self.cache['patterns'] and not force_ai:
            pattern = self.cache['patterns'][casino]
            
            # Essaie de construire l'URL avec le pattern
            predicted_url = self._try_pattern(pattern, team1, team2, sport)
            
            if predicted_url:
                print(f"   📊 Essai avec pattern connu: {predicted_url}")
                
                # Vérifie si l'URL marche (rapide avec requests)
                if await self._verify_url_works(predicted_url):
                    print(f"   ✅ Pattern marche!")
                    return {
                        'success': True,
                        'url': predicted_url,
                        'method': 'pattern',
                        'cost': 0
                    }
        
        # Étape 3: Best effort gratuit
        if not force_ai:
            print(f"   🎯 Essai best effort...")
            
            best_effort_result = self.best_effort.generate_best_link(
                casino=casino,
                sport=sport,
                team1=team1,
                team2=team2,
                bet_team=bet_team,
                market=market
            )
            
            if best_effort_result['confidence'] in ['high', 'medium']:
                print(f"   ⚡ Best effort: {best_effort_result['type']}")
                return {
                    'success': True,
                    'url': best_effort_result['url'],
                    'method': 'best_effort',
                    'confidence': best_effort_result['confidence'],
                    'cost': 0
                }
        
        # Étape 4: Claude Vision (si disponible)
        if self.has_ai:
            print(f"   🤖 Utilisation de Claude Vision...")
            
            ai_result = await self.ai_finder.find_exact_bet_link(
                casino=casino,
                sport=sport,
                team1=team1,
                team2=team2,
                bet_team=bet_team,
                market=market
            )
            
            if ai_result['success']:
                # IMPORTANT: Sauvegarde dans le cache!
                event_id = ai_result.get('event_id')
                if event_id:
                    self.cache['matches'][match_hash] = event_id
                    self.cache['events'][event_id] = {
                        'team1': team1,
                        'team2': team2,
                        'sport': sport,
                        'date': datetime.now().isoformat()
                    }
                    
                    # Extrait et sauvegarde le pattern
                    self._extract_and_save_pattern(casino, ai_result['url'], event_id)
                    
                    # Sauvegarde sur disque
                    self._save_cache()
                    
                    print(f"   💾 Sauvegardé dans le cache pour la prochaine fois!")
                
                return ai_result
        
        # Échec total - fallback basique
        print(f"   ❌ Aucune méthode n'a marché, fallback sur homepage")
        
        return {
            'success': False,
            'url': f"https://{casino.lower()}.com",
            'method': 'fallback',
            'cost': 0
        }
    
    def _build_url_from_pattern(self, casino: str, event_id: str) -> Optional[str]:
        """
        Construit l'URL depuis un pattern connu
        """
        patterns = {
            'Betway': f"https://betway.com/g/en-ca/sports/event/{event_id}",
            'BET99': f"https://bet99.ca/en/sportsbook/event/{event_id}",
            'Coolbet': f"https://www.coolbet.com/en/sports/event/{event_id}",
            'Sports Interaction': f"https://www.sportsinteraction.com/betting/event/{event_id}",
            'bet105': f"https://www.bet105.com/sports/event/{event_id}",
            'Betsson': f"https://www.betsson.com/en/sportsbook/event/{event_id}"
        }
        
        return patterns.get(casino)
    
    def _extract_and_save_pattern(self, casino: str, url: str, event_id: str):
        """
        Extrait le pattern d'URL pour réutilisation
        """
        # Remplace l'event_id par un placeholder
        pattern = url.replace(event_id, "{event_id}")
        
        # Sauvegarde le pattern
        if casino not in self.cache['patterns']:
            self.cache['patterns'][casino] = {}
        
        self.cache['patterns'][casino]['url_template'] = pattern
        
        # Essaie d'extraire d'autres patterns
        # Ex: /basketball/nba/ → sport pattern
        if '/basketball/' in url:
            self.cache['patterns'][casino]['basketball_path'] = '/basketball/'
        if '/nba/' in url:
            self.cache['patterns'][casino]['nba_path'] = '/nba/'
        if '/ncaab/' in url:
            self.cache['patterns'][casino]['ncaab_path'] = '/ncaab/'
    
    def _try_pattern(
        self,
        pattern: Dict,
        team1: str,
        team2: str,
        sport: str
    ) -> Optional[str]:
        """
        Essaie de construire une URL avec un pattern connu
        """
        # Pour l'instant, retourne None
        # On pourrait implémenter une logique plus complexe
        return None
    
    async def _verify_url_works(self, url: str) -> bool:
        """
        Vérifie rapidement si une URL fonctionne
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=3) as response:
                    return response.status == 200
        except:
            return False
    
    def get_cache_stats(self) -> Dict:
        """
        Statistiques du cache
        """
        return {
            'matches_cached': len(self.cache['matches']),
            'patterns_learned': len(self.cache['patterns']),
            'events_stored': len(self.cache['events']),
            'cache_size_kb': sum(
                f.stat().st_size / 1024 
                for f in self.cache_files.values() 
                if f.exists()
            )
        }


# Wrapper pour utilisation simple
async def find_arbitrage_links(arbitrage_data: Dict[str, Any]) -> Dict:
    """
    Trouve les liens pour un arbitrage complet
    """
    
    # Initialise le finder
    api_key = os.getenv('ANTHROPIC_API_KEY')
    finder = SmartLinkFinder(api_key)
    
    print("🎯 Recherche intelligente des liens")
    print(f"   Cache: {finder.get_cache_stats()['matches_cached']} matchs en mémoire")
    print("=" * 50)
    
    # Bet 1
    bet1_result = await finder.find_bet_link(
        casino=arbitrage_data['bet1']['casino'],
        sport=arbitrage_data['sport'],
        team1=arbitrage_data['team1'],
        team2=arbitrage_data['team2'],
        bet_team=arbitrage_data['bet1']['team'],
        market=arbitrage_data['bet1'].get('market', 'Moneyline')
    )
    
    # Bet 2
    bet2_result = await finder.find_bet_link(
        casino=arbitrage_data['bet2']['casino'],
        sport=arbitrage_data['sport'],
        team1=arbitrage_data['team1'],
        team2=arbitrage_data['team2'],
        bet_team=arbitrage_data['bet2']['team'],
        market=arbitrage_data['bet2'].get('market', 'Moneyline')
    )
    
    total_cost = bet1_result.get('cost', 0) + bet2_result.get('cost', 0)
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ:")
    print(f"   Bet1: {bet1_result['method']} - {bet1_result.get('url', 'N/A')[:50]}...")
    print(f"   Bet2: {bet2_result['method']} - {bet2_result.get('url', 'N/A')[:50]}...")
    print(f"   Coût total: ${total_cost:.3f}")
    print(f"   Cache stats: {finder.get_cache_stats()}")
    
    return {
        'bet1': bet1_result,
        'bet2': bet2_result,
        'total_cost': total_cost
    }


if __name__ == "__main__":
    # Test avec ton arbitrage
    arbitrage = {
        'team1': 'Oral Roberts',
        'team2': 'Rice',
        'sport': 'NCAAB',
        'bet1': {
            'casino': 'Betway',
            'team': 'Rice',
            'market': 'Moneyline'
        },
        'bet2': {
            'casino': 'bet105',
            'team': 'Oral Roberts',
            'market': 'Moneyline'
        }
    }
    
    asyncio.run(find_arbitrage_links(arbitrage))
