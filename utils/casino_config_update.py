"""
Mise à jour de la configuration des casinos québécois
Ajoute iBet et autres casinos manquants
"""

# Configuration complète de TOUS les casinos québécois
QUEBEC_CASINOS_COMPLETE = {
    'iBet': {
        'base': 'https://www.ibet.com',
        'patterns': {
            'NBA': '/sports/basketball/nba',
            'NCAAB': '/sports/basketball/ncaab',
            'NHL': '/sports/hockey/nhl',
            'NFL': '/sports/football/nfl',
            'search': '/sports/search?q={query}'
        },
        'player_props_path': '#player-props'
    },
    'Sports Interaction': {
        'base': 'https://www.sportsinteraction.com',
        'patterns': {
            'NBA': '/betting/basketball/usa/nba',
            'NCAAB': '/betting/basketball/usa/ncaa',
            'NHL': '/betting/hockey/nhl',
            'NFL': '/betting/football/nfl',
            'search': '/betting/search?q={query}'
        },
        'player_props_path': '#props'
    },
    'BET99': {
        'base': 'https://bet99.ca',
        'patterns': {
            'NBA': '/en/sportsbook/basketball/usa/nba',
            'NCAAB': '/en/sportsbook/basketball/usa/ncaab',
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
            'NCAAB': '/en/sports/basketball/ncaab',
            'NHL': '/en/sports/ice-hockey/nhl',
            'NFL': '/en/sports/american-football/nfl',
            'search': '/en/sports/search/{query}'
        },
        'player_props_path': '#player-markets'
    },
    'Betway': {
        'base': 'https://betway.ca',
        'patterns': {
            'NBA': '/en/sports/grp/basketball/nba',
            'NCAAB': '/en/sports/grp/basketball/college-basketball',
            'NHL': '/en/sports/grp/ice-hockey/nhl',
            'NFL': '/en/sports/grp/american-football/nfl',
            'search': '/en/sports/search?searchTerm={query}'
        }
    },
    'Betsson': {
        'base': 'https://www.betsson.com',
        'patterns': {
            'NBA': '/en/sportsbook/basketball/nba',
            'NCAAB': '/en/sportsbook/basketball/ncaab',
            'NHL': '/en/sportsbook/ice-hockey/nhl',
            'NFL': '/en/sportsbook/american-football/nfl',
            'search': '/en/sportsbook/search?q={query}'
        }
    },
    'Mise-o-jeu': {
        'base': 'https://www.lotoquebec.com',
        'patterns': {
            'NBA': '/en/sports-betting/basketball/nba',
            'NCAAB': '/en/sports-betting/basketball/ncaab',
            'NHL': '/en/sports-betting/hockey/nhl',
            'NFL': '/en/sports-betting/football/nfl',
            'search': '/en/sports-betting/search?q={query}'
        }
    },
    'Pinnacle': {
        'base': 'https://www.pinnacle.com',
        'patterns': {
            'NBA': '/en/basketball/nba/matchups',
            'NCAAB': '/en/basketball/ncaab/matchups',
            'NHL': '/en/hockey/nhl/matchups',
            'NFL': '/en/american-football/nfl/matchups'
        }
    },
    'bet365': {
        'base': 'https://www.bet365.ca',
        'patterns': {
            'NBA': '/#/AC/B18/',
            'NCAAB': '/#/AC/B18/',  
            'NHL': '/#/AC/B17/',
            'NFL': '/#/AC/B12/'
        }
    },
    'LeoVegas': {
        'base': 'https://www.leovegas.com',
        'patterns': {
            'NBA': '/en-ca/betting/basketball/nba',
            'NCAAB': '/en-ca/betting/basketball/ncaab',
            'NHL': '/en-ca/betting/ice-hockey/nhl',
            'NFL': '/en-ca/betting/american-football/nfl'
        }
    },
    'TonyBet': {
        'base': 'https://tonybet.com',
        'patterns': {
            'NBA': '/ca/sportsbook/basketball-usa-nba',
            'NCAAB': '/ca/sportsbook/basketball-usa-ncaab',
            'NHL': '/ca/sportsbook/ice-hockey-usa-nhl',
            'NFL': '/ca/sportsbook/american-football-usa-nfl'
        }
    },
    'Proline+': {
        'base': 'https://www.proline.ca',
        'patterns': {
            'NBA': '/sports/basketball/nba',
            'NCAAB': '/sports/basketball/ncaab',
            'NHL': '/sports/hockey/nhl',
            'NFL': '/sports/football/nfl'
        }
    },
    'bet105': {
        'base': 'https://www.bet105.com',
        'patterns': {
            'NBA': '/sports/basketball/nba',
            'NCAAB': '/sports/basketball/ncaab',
            'NHL': '/sports/hockey/nhl',
            'NFL': '/sports/football/nfl',
            'search': '/sports/search?q={query}'
        }
    },
    'Unibet': {
        'base': 'https://www.unibet.ca',
        'patterns': {
            'NBA': '/betting/sports/filter/basketball/nba',
            'NCAAB': '/betting/sports/filter/basketball/ncaab',
            'NHL': '/betting/sports/filter/ice_hockey/nhl',
            'NFL': '/betting/sports/filter/american_football/nfl'
        }
    },
    '888sport': {
        'base': 'https://www.888sport.com',
        'patterns': {
            'NBA': '/basketball/nba',
            'NCAAB': '/basketball/ncaab',
            'NHL': '/ice-hockey/nhl',
            'NFL': '/american-football/nfl'
        }
    },
    'BetVictor': {
        'base': 'https://www.betvictor.com',
        'patterns': {
            'NBA': '/en-ca/sports/basketball/nba',
            'NCAAB': '/en-ca/sports/basketball/ncaab',
            'NHL': '/en-ca/sports/ice-hockey/nhl',
            'NFL': '/en-ca/sports/american-football/nfl'
        }
    },
    'bwin': {
        'base': 'https://www.bwin.com',
        'patterns': {
            'NBA': '/en/sports/basketball-7/nba',
            'NCAAB': '/en/sports/basketball-7/ncaab',
            'NHL': '/en/sports/ice-hockey-4/nhl',
            'NFL': '/en/sports/american-football-6/nfl'
        }
    },
    'Casumo': {
        'base': 'https://www.casumo.com',
        'patterns': {
            'NBA': '/en-ca/sports/basketball/nba',
            'NCAAB': '/en-ca/sports/basketball/ncaab',
            'NHL': '/en-ca/sports/ice-hockey/nhl',
            'NFL': '/en-ca/sports/american-football/nfl'
        }
    },
    'Jackpot.bet': {
        'base': 'https://www.jackpot.bet',
        'patterns': {
            'NBA': '/sports/basketball/nba',
            'NCAAB': '/sports/basketball/ncaab',
            'NHL': '/sports/ice-hockey/nhl',
            'NFL': '/sports/american-football/nfl'
        }
    },
    'Stake': {
        'base': 'https://stake.com',
        'patterns': {
            'NBA': '/sports/basketball/usa/nba',
            'NCAAB': '/sports/basketball/usa/ncaab',
            'NHL': '/sports/ice-hockey/usa/nhl',
            'NFL': '/sports/american-football/usa/nfl'
        }
    }
}

# Pour mettre à jour le fichier best_effort_links.py
if __name__ == "__main__":
    print("📋 Configuration complète des casinos québécois")
    print(f"   Total: {len(QUEBEC_CASINOS_COMPLETE)} casinos")
    print("\n✅ Casinos configurés:")
    for casino in QUEBEC_CASINOS_COMPLETE.keys():
        print(f"   - {casino}")
    
    print("\n💡 Pour utiliser cette config:")
    print("   1. Remplace CASINO_PATTERNS dans utils/best_effort_links.py")
    print("   2. Remplace QUEBEC_CASINOS dans utils/smart_casino_navigator.py")
