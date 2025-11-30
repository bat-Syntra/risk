"""
Best Effort Links - Le mieux qu'on peut faire sans IA
"""

from typing import Dict, Any
from urllib.parse import quote

class BestEffortLinks:
    """
    Génère les meilleurs liens possibles pour chaque casino
    Sans IA, sans navigation complexe
    """
    
    # Patterns optimisés pour chaque casino et sport
    CASINO_PATTERNS = {
        'Betway': {
            'base': 'https://betway.ca',
            'sports': {
                'NBA': '/en/sports/grp/basketball/nba',
                'NCAAB': '/en/sports/grp/basketball/college-basketball',
                'NHL': '/en/sports/grp/ice-hockey/nhl',
                'NFL': '/en/sports/grp/american-football/nfl'
            },
            'search_suffix': '?searchTerm={query}',
            'direct_match': '/games/{team1}-vs-{team2}'
        },
        'bet105': {
            'base': 'https://www.bet105.com',
            'sports': {
                'NBA': '/sports/basketball/nba',
                'NCAAB': '/sports/basketball/ncaab',
                'NHL': '/sports/hockey/nhl',
                'NFL': '/sports/football/nfl'
            },
            'search_suffix': '#search={query}'
        },
        'BET99': {
            'base': 'https://bet99.ca',
            'sports': {
                'NBA': '/en/sportsbook/basketball/usa/nba',
                'NCAAB': '/en/sportsbook/basketball/usa/ncaab',
                'NHL': '/en/sportsbook/ice-hockey/usa/nhl',
                'NFL': '/en/sportsbook/american-football/usa/nfl'
            },
            'search_suffix': '?query={query}'
        },
        'Coolbet': {
            'base': 'https://www.coolbet.com',
            'sports': {
                'NBA': '/en/sports/basketball/nba',
                'NCAAB': '/en/sports/basketball/ncaab',
                'NHL': '/en/sports/ice-hockey/nhl',
                'NFL': '/en/sports/american-football/nfl'
            },
            'search_suffix': '?search={query}'
        },
        'Sports Interaction': {
            'base': 'https://www.sportsinteraction.com',
            'sports': {
                'NBA': '/betting/basketball/usa/nba',
                'NCAAB': '/betting/basketball/usa/ncaa',
                'NHL': '/betting/hockey/nhl',
                'NFL': '/betting/football/nfl'
            },
            'search_suffix': '?q={query}'
        },
        'Betsson': {
            'base': 'https://www.betsson.com',
            'sports': {
                'NBA': '/en/sportsbook/basketball/nba',
                'NCAAB': '/en/sportsbook/basketball/ncaab',
                'NHL': '/en/sportsbook/ice-hockey/nhl',
                'NFL': '/en/sportsbook/american-football/nfl'
            }
        }
    }
    
    def generate_best_link(
        self,
        casino: str,
        sport: str,
        team1: str,
        team2: str,
        bet_team: str = None,
        market: str = None
    ) -> Dict[str, Any]:
        """
        Génère le meilleur lien possible pour un bet
        
        Returns:
            {
                'url': 'https://...',
                'confidence': 'high|medium|low',
                'type': 'direct|search|sport_page'
            }
        """
        
        casino_config = self.CASINO_PATTERNS.get(casino, {})
        if not casino_config:
            return {
                'url': f'https://www.google.com/search?q={quote(casino)}+{quote(team1)}+{quote(team2)}',
                'confidence': 'low',
                'type': 'google_search'
            }
        
        base = casino_config['base']
        sport_path = casino_config.get('sports', {}).get(sport)
        
        # Stratégie 1: Essayer un lien direct (si le pattern existe)
        if 'direct_match' in casino_config:
            # Formater les noms d'équipe pour l'URL
            t1 = team1.lower().replace(' ', '-')
            t2 = team2.lower().replace(' ', '-')
            direct_url = base + sport_path + casino_config['direct_match'].format(
                team1=t1, team2=t2
            )
            
            return {
                'url': direct_url,
                'confidence': 'medium',
                'type': 'direct_guess'
            }
        
        # Stratégie 2: Page du sport avec recherche
        if sport_path and 'search_suffix' in casino_config:
            search_query = f"{team1} {team2}"
            if bet_team:
                search_query = bet_team
            
            search_url = base + sport_path + casino_config['search_suffix'].format(
                query=quote(search_query)
            )
            
            return {
                'url': search_url,
                'confidence': 'high',
                'type': 'search'
            }
        
        # Stratégie 3: Juste la page du sport
        if sport_path:
            return {
                'url': base + sport_path,
                'confidence': 'medium',
                'type': 'sport_page'
            }
        
        # Fallback: Page d'accueil
        return {
            'url': base,
            'confidence': 'low',
            'type': 'homepage'
        }
    
    def generate_arbitrage_links(self, arbitrage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère les liens pour un arbitrage complet
        """
        
        team1 = arbitrage_data.get('team1', '')
        team2 = arbitrage_data.get('team2', '')
        sport = arbitrage_data.get('sport', 'NBA')
        
        bet1 = arbitrage_data.get('bet1', {})
        bet2 = arbitrage_data.get('bet2', {})
        
        result1 = self.generate_best_link(
            casino=bet1.get('casino'),
            sport=sport,
            team1=team1,
            team2=team2,
            bet_team=bet1.get('team'),
            market=bet1.get('market')
        )
        
        result2 = self.generate_best_link(
            casino=bet2.get('casino'),
            sport=sport,
            team1=team1,
            team2=team2,
            bet_team=bet2.get('team'),
            market=bet2.get('market')
        )
        
        return {
            'bet1': result1,
            'bet2': result2,
            'overall_confidence': self._calculate_confidence(result1, result2)
        }
    
    def _calculate_confidence(self, result1, result2):
        """Calcule la confiance globale"""
        scores = {'high': 3, 'medium': 2, 'low': 1}
        total = scores.get(result1['confidence'], 0) + scores.get(result2['confidence'], 0)
        
        if total >= 5:
            return 'high'
        elif total >= 3:
            return 'medium'
        else:
            return 'low'


# Test avec ton arbitrage
if __name__ == "__main__":
    generator = BestEffortLinks()
    
    # Ton arbitrage Rice vs Oral Roberts
    arbitrage = {
        'team1': 'Oral Roberts',
        'team2': 'Rice',
        'sport': 'NCAAB',
        'bet1': {
            'casino': 'Betway',
            'team': 'Rice',
            'market': 'Moneyline',
            'odds': '+120'
        },
        'bet2': {
            'casino': 'bet105',
            'team': 'Oral Roberts',
            'market': 'Moneyline',
            'odds': '+197'
        }
    }
    
    results = generator.generate_arbitrage_links(arbitrage)
    
    print("🎯 Meilleurs liens possibles sans IA:\n")
    print("=" * 50)
    
    print(f"\n🎰 Betway - {results['bet1']['confidence'].upper()} confidence")
    print(f"   Type: {results['bet1']['type']}")
    print(f"   URL: {results['bet1']['url']}")
    
    print(f"\n🎲 bet105 - {results['bet2']['confidence'].upper()} confidence")
    print(f"   Type: {results['bet2']['type']}")
    print(f"   URL: {results['bet2']['url']}")
    
    print(f"\n📊 Confiance globale: {results['overall_confidence'].upper()}")
    
    print("\n💡 Explication des types:")
    print("   - search: Va direct sur la page avec recherche pré-remplie")
    print("   - sport_page: Page du sport, l'user cherche le match")
    print("   - direct_guess: Tentative de lien direct (peut marcher ou pas)")
