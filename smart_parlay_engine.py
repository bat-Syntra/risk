#!/usr/bin/env python3
"""
🎰 SMART PARLAY ENGINE v2.0
Génère des parlays intelligents à partir de TOUS les drops (Arbitrage, Middle, Good EV)
- PAS de filtrage par % - génère TOUT ce qui est bon
- Multi-stratégies: Safe, Balanced, Aggressive, Lottery
- Same-day et Cross-day parlays
- Calcule EV réel de chaque parlay
"""
import json
from datetime import datetime, date, timedelta
from database import SessionLocal
from sqlalchemy import text
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SmartParlayEngine:
    """
    Moteur de génération de parlays intelligent
    Utilise TOUS les drops sans filtrage de %
    """
    
    def __init__(self):
        self.db = SessionLocal()
        
    def get_all_recent_drops(self, days_back: int = 7) -> List[Dict]:
        """
        Récupère TOUS les drops récents (sans filtrage de %)
        """
        try:
            drops = self.db.execute(text("""
                SELECT id, event_id, match, league, market, bet_type, 
                       arb_percentage, payload, received_at
                FROM drop_events
                WHERE received_at >= datetime('now', :days_ago)
                ORDER BY received_at DESC
            """), {'days_ago': f'-{days_back} days'}).fetchall()
            
            result = []
            for drop in drops:
                parsed = self._parse_drop(drop)
                if parsed:
                    result.append(parsed)
            
            return result
        except Exception as e:
            logger.error(f"Error fetching drops: {e}")
            return []
    
    def _parse_drop(self, drop) -> Optional[Dict]:
        """
        Parse un drop en format utilisable pour parlays
        Extrait les legs (outcomes) de chaque drop
        """
        try:
            payload = drop.payload if isinstance(drop.payload, dict) else json.loads(drop.payload or '{}')
            
            bet_type = drop.bet_type or 'unknown'
            edge = float(drop.arb_percentage or 0)
            
            # Extraire sport du payload ou league
            sport = payload.get('sport', '') or drop.league or ''
            
            # Déterminer la date du match depuis le payload
            match_date = None
            commence_time = payload.get('commence_time') or payload.get('match_time')
            if commence_time:
                try:
                    if isinstance(commence_time, str):
                        match_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00')).date()
                    else:
                        match_date = commence_time.date() if hasattr(commence_time, 'date') else None
                except:
                    pass
            
            # Extraire les legs selon le type
            legs = []
            
            if bet_type == 'arbitrage':
                # Arbitrage a plusieurs outcomes
                outcomes = payload.get('outcomes', [])
                market = payload.get('market', drop.market or '')
                
                for outcome in outcomes:
                    odds = self._parse_odds(outcome.get('odds', 0))
                    if odds > 1.0:
                        outcome_text = outcome.get('outcome', '') or outcome.get('selection', '')
                        
                        # 🎯 Extraire le player du texte outcome si c'est un player prop
                        player = ''
                        selection = outcome_text
                        if 'Player' in market and outcome_text:
                            import re
                            match = re.match(r'^(.+?)\s+(Over|Under)\s+([\d.]+)', outcome_text)
                            if match:
                                player = match.group(1).strip()
                                selection = f"{match.group(2)} {match.group(3)}"
                        
                        legs.append({
                            'drop_id': drop.id,
                            'match': drop.match or payload.get('match', 'Unknown'),
                            'league': drop.league or payload.get('league', ''),
                            'sport': sport,
                            'market': market,
                            'player': player,  # 🎯 NOM DU JOUEUR!
                            'selection': selection,
                            'bookmaker': outcome.get('casino', outcome.get('bookmaker', '')),
                            'odds': odds,
                            'edge': edge,
                            'bet_type': bet_type,
                            'match_date': match_date,
                            'received_at': drop.received_at
                        })
            
            elif bet_type == 'middle':
                # Middle a side_a et side_b
                for side_key in ['side_a', 'side_b']:
                    side = payload.get(side_key, {})
                    odds = self._parse_odds(side.get('odds', 0))
                    if odds > 1.0:
                        legs.append({
                            'drop_id': drop.id,
                            'match': drop.match or payload.get('match', 'Unknown'),
                            'league': drop.league or payload.get('league', ''),
                            'sport': sport,
                            'market': side.get('market', drop.market or ''),
                            'selection': side.get('selection', f"{side.get('line', '')}"),
                            'bookmaker': side.get('bookmaker', ''),
                            'odds': odds,
                            'edge': edge,
                            'bet_type': bet_type,
                            'match_date': match_date,
                            'received_at': drop.received_at
                        })
            
            elif bet_type == 'good_ev':
                # Good EV a un seul outcome
                odds = self._parse_odds(payload.get('odds', 0))
                if odds > 1.0:
                    market = payload.get('market', drop.market or '')
                    selection = payload.get('selection', '')
                    
                    # 🎯 Extraire le player du payload ou de la selection
                    player = payload.get('player', '')
                    if not player and 'Player' in market:
                        # Essayer d'extraire le nom du joueur de la selection
                        # Format: "Joueur Over/Under X.X" ou juste dans outcomes
                        player = self._extract_player_name(selection, payload.get('outcomes', []))
                    
                    legs.append({
                        'drop_id': drop.id,
                        'match': drop.match or payload.get('match', 'Unknown'),
                        'league': drop.league or payload.get('league', ''),
                        'sport': sport,
                        'market': market,
                        'player': player,  # 🎯 NOM DU JOUEUR!
                        'selection': selection,
                        'bookmaker': payload.get('bookmaker', ''),
                        'odds': odds,
                        'edge': edge,
                        'bet_type': bet_type,
                        'match_date': match_date,
                        'received_at': drop.received_at
                    })
            
            return {'drop': drop, 'legs': legs} if legs else None
            
        except Exception as e:
            logger.error(f"Error parsing drop {drop.id}: {e}")
            return None
    
    def _parse_odds(self, odds_value) -> float:
        """Parse odds en format décimal"""
        try:
            if isinstance(odds_value, (int, float)):
                odds = float(odds_value)
            else:
                odds_str = str(odds_value).replace('+', '')
                if odds_str.startswith('-'):
                    # American negative odds
                    odds = 1 + (100 / abs(float(odds_str)))
                else:
                    # American positive odds or decimal
                    val = float(odds_str)
                    if val > 50:  # Probably American
                        odds = 1 + (val / 100)
                    else:
                        odds = val
            return odds if odds > 1.0 else 0
        except:
            return 0
    
    def _extract_player_name(self, selection: str, outcomes: List[Dict]) -> str:
        """
        Extrait le nom du joueur depuis la selection ou les outcomes
        Ex: "Landry Shamet Over 1.5" -> "Landry Shamet"
        Ex: outcomes[0]['outcome'] = "Ferran Torres Over 0.5" -> "Ferran Torres"
        """
        import re
        
        # Essayer d'abord dans les outcomes
        for outcome in outcomes:
            outcome_text = outcome.get('outcome', '') or outcome.get('selection', '')
            if outcome_text:
                # Chercher pattern: "Nom Joueur Over/Under X.X"
                match = re.match(r'^(.+?)\s+(Over|Under)\s+[\d.]+', outcome_text)
                if match:
                    return match.group(1).strip()
        
        # Sinon essayer dans la selection
        if selection:
            match = re.match(r'^(.+?)\s+(Over|Under)\s+[\d.]+', selection)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def generate_all_parlays(self) -> List[Dict]:
        """
        Génère TOUS les types de parlays possibles
        - Same Day: matchs de la même journée
        - Cross Day: matchs de jours différents (pas de vérif de date)
        - Safe: 2 legs, cotes basses
        - Balanced: 2-3 legs, cotes moyennes
        - Aggressive: 3-4 legs, grosses cotes
        - Lottery: 4+ legs, jackpot potentiel
        """
        drops_data = self.get_all_recent_drops(days_back=7)
        
        # Collecter tous les legs disponibles
        all_legs = []
        for data in drops_data:
            all_legs.extend(data['legs'])
        
        if len(all_legs) < 2:
            logger.info(f"Not enough legs for parlays ({len(all_legs)} found)")
            return []
        
        logger.info(f"🎰 Found {len(all_legs)} legs from {len(drops_data)} drops")
        
        parlays = []
        
        # ===== SAME DAY PARLAYS =====
        # Grouper par date de match
        legs_by_date = {}
        for leg in all_legs:
            if leg['match_date']:
                date_key = leg['match_date'].isoformat()
                if date_key not in legs_by_date:
                    legs_by_date[date_key] = []
                legs_by_date[date_key].append(leg)
        
        for date_key, date_legs in legs_by_date.items():
            if len(date_legs) >= 2:
                # Safe 2-leg same day
                parlays.extend(self._create_parlays(date_legs, 'SAME_DAY_SAFE', max_legs=2, min_combined=1.5, max_combined=3.0))
                # Balanced 2-3 legs same day
                parlays.extend(self._create_parlays(date_legs, 'SAME_DAY_BALANCED', max_legs=3, min_combined=2.0, max_combined=6.0))
                # Aggressive 3-4 legs same day
                if len(date_legs) >= 3:
                    parlays.extend(self._create_parlays(date_legs, 'SAME_DAY_AGGRESSIVE', max_legs=4, min_combined=4.0, max_combined=15.0))
        
        # ===== CROSS DAY PARLAYS (pas de vérif de date) =====
        # Utiliser TOUS les legs peu importe la date
        
        # Safe cross-day
        parlays.extend(self._create_parlays(all_legs, 'CROSS_DAY_SAFE', max_legs=2, min_combined=1.5, max_combined=3.0))
        
        # Balanced cross-day
        parlays.extend(self._create_parlays(all_legs, 'CROSS_DAY_BALANCED', max_legs=3, min_combined=2.5, max_combined=8.0))
        
        # Aggressive cross-day
        parlays.extend(self._create_parlays(all_legs, 'CROSS_DAY_AGGRESSIVE', max_legs=4, min_combined=5.0, max_combined=20.0))
        
        # Lottery (jackpot potential)
        if len(all_legs) >= 4:
            parlays.extend(self._create_parlays(all_legs, 'LOTTERY', max_legs=6, min_combined=10.0, max_combined=100.0))
        
        # ===== HIGH EV PARLAYS =====
        # Combiner les legs avec le plus haut edge
        high_ev_legs = sorted(all_legs, key=lambda x: x['edge'], reverse=True)[:20]
        if len(high_ev_legs) >= 2:
            parlays.extend(self._create_parlays(high_ev_legs, 'HIGH_EV', max_legs=3, min_combined=2.0, max_combined=10.0))
        
        # Dédupliquer et sauvegarder
        unique_parlays = self._deduplicate_parlays(parlays)
        
        logger.info(f"🎉 Generated {len(unique_parlays)} unique parlays")
        
        # Sauvegarder en DB
        saved_count = 0
        for parlay in unique_parlays:
            if self._save_parlay(parlay):
                saved_count += 1
        
        logger.info(f"💾 Saved {saved_count} new parlays to database")
        
        return unique_parlays
    
    def _create_parlays(self, legs: List[Dict], strategy: str, max_legs: int, 
                        min_combined: float, max_combined: float) -> List[Dict]:
        """
        Crée des parlays à partir d'une liste de legs
        IMPORTANT: Tous les legs doivent être du MÊME CASINO!
        """
        parlays = []
        
        if len(legs) < 2:
            return parlays
        
        # 🎯 GROUPER PAR CASINO - Un parlay = UN casino!
        legs_by_casino = {}
        for leg in legs:
            casino = leg.get('bookmaker', 'Unknown')
            if casino and casino != 'Unknown':
                if casino not in legs_by_casino:
                    legs_by_casino[casino] = []
                legs_by_casino[casino].append(leg)
        
        # Créer des parlays pour CHAQUE casino séparément
        from itertools import combinations
        
        for casino, casino_legs in legs_by_casino.items():
            if len(casino_legs) < 2:
                continue
            
            # Trier par edge (meilleurs en premier)
            sorted_legs = sorted(casino_legs, key=lambda x: x['edge'], reverse=True)
            
            for num_legs in range(2, min(max_legs + 1, len(sorted_legs) + 1)):
                # Prendre les meilleures combinaisons pour CE casino
                for combo in list(combinations(sorted_legs[:10], num_legs))[:5]:
                    # Vérifier que les legs sont de matchs différents
                    matches = set(leg['match'] for leg in combo)
                    if len(matches) < len(combo):
                        continue  # Skip si même match
                    
                    # Calculer les cotes combinées
                    combined_odds = 1.0
                    for leg in combo:
                        combined_odds *= leg['odds']
                    
                    # Vérifier les limites
                    if min_combined <= combined_odds <= max_combined:
                        # Calculer l'EV du parlay
                        avg_edge = sum(leg['edge'] for leg in combo) / len(combo)
                        
                        # Estimer la probabilité de gain
                        win_prob = 1.0
                        for leg in combo:
                            # Convertir edge en probabilité approximative
                            leg_prob = 0.5 + (leg['edge'] / 100) * 0.3  # Ajustement basé sur edge
                            win_prob *= leg_prob
                        
                        expected_value = (combined_odds * win_prob) - 1
                        
                        parlay = {
                            'strategy': strategy,
                            'casino': casino,  # 🎯 CASINO UNIQUE!
                            'legs': list(combo),
                            'num_legs': len(combo),
                            'combined_odds': round(combined_odds, 2),
                            'avg_edge': round(avg_edge, 2),
                            'estimated_win_prob': round(win_prob * 100, 1),
                            'expected_value': round(expected_value * 100, 2),
                            'potential_return': f"{combined_odds:.2f}x",
                            'created_at': datetime.now().isoformat(),
                            'risk_level': self._get_risk_level(strategy)
                        }
                        
                        parlays.append(parlay)
        
        return parlays
    
    def _get_risk_level(self, strategy: str) -> str:
        """Retourne le niveau de risque pour une stratégie"""
        if 'SAFE' in strategy:
            return 'LOW'
        elif 'BALANCED' in strategy:
            return 'MEDIUM'
        elif 'AGGRESSIVE' in strategy:
            return 'HIGH'
        elif 'LOTTERY' in strategy:
            return 'EXTREME'
        else:
            return 'MEDIUM'
    
    def _deduplicate_parlays(self, parlays: List[Dict]) -> List[Dict]:
        """Élimine les parlays en double"""
        seen = set()
        unique = []
        
        for parlay in parlays:
            # Créer une clé unique basée sur les legs
            leg_ids = tuple(sorted(leg['drop_id'] for leg in parlay['legs']))
            key = (leg_ids, parlay['strategy'])
            
            if key not in seen:
                seen.add(key)
                unique.append(parlay)
        
        return unique
    
    def _save_parlay(self, parlay: Dict) -> bool:
        """Sauvegarde un parlay en DB"""
        try:
            # Vérifier si existe déjà
            leg_ids = json.dumps(sorted(leg['drop_id'] for leg in parlay['legs']))
            
            existing = self.db.execute(text("""
                SELECT id FROM parlays WHERE leg_drop_ids = :leg_ids
            """), {'leg_ids': leg_ids}).fetchone()
            
            if existing:
                return False
            
            # Créer le parlay
            self.db.execute(text("""
                INSERT INTO parlays (
                    strategy, casino, num_legs, combined_odds, avg_edge,
                    estimated_win_prob, expected_value, risk_level,
                    leg_drop_ids, legs_json, created_at, status
                ) VALUES (
                    :strategy, :casino, :num_legs, :combined_odds, :avg_edge,
                    :win_prob, :ev, :risk, :leg_ids, :legs_json, :created, 'active'
                )
            """), {
                'strategy': parlay['strategy'],
                'casino': parlay.get('casino', 'Unknown'),
                'num_legs': parlay['num_legs'],
                'combined_odds': parlay['combined_odds'],
                'avg_edge': parlay['avg_edge'],
                'win_prob': parlay['estimated_win_prob'],
                'ev': parlay['expected_value'],
                'risk': parlay['risk_level'],
                'leg_ids': leg_ids,
                'legs_json': json.dumps(parlay['legs'], default=str),
                'created': datetime.now()
            })
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving parlay: {e}")
            self.db.rollback()
            return False
    
    def get_parlays_for_user(self, user_id: int, risk_levels: List[str] = None) -> List[Dict]:
        """
        Récupère les parlays actifs pour un utilisateur
        Filtre par niveau de risque si spécifié
        """
        try:
            query = """
                SELECT * FROM parlays 
                WHERE status = 'active' 
                AND created_at >= datetime('now', '-2 days')
            """
            
            if risk_levels:
                placeholders = ','.join(f"'{r}'" for r in risk_levels)
                query += f" AND risk_level IN ({placeholders})"
            
            query += " ORDER BY expected_value DESC LIMIT 20"
            
            parlays = self.db.execute(text(query)).fetchall()
            
            result = []
            for p in parlays:
                result.append({
                    'id': p.id,
                    'strategy': p.strategy,
                    'num_legs': p.num_legs,
                    'combined_odds': p.combined_odds,
                    'avg_edge': p.avg_edge,
                    'estimated_win_prob': p.estimated_win_prob,
                    'expected_value': p.expected_value,
                    'risk_level': p.risk_level,
                    'legs': json.loads(p.legs_json) if p.legs_json else [],
                    'created_at': p.created_at
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching parlays: {e}")
            return []


# Fonction globale pour génération en temps réel
def on_drop_received(drop_event_id: int):
    """
    Appelé quand un nouveau drop arrive
    Génère immédiatement des parlays
    """
    try:
        engine = SmartParlayEngine()
        
        print(f"🔥 New drop {drop_event_id} - Analyzing for parlays...")
        
        # Générer tous les parlays possibles
        parlays = engine.generate_all_parlays()
        
        if parlays:
            print(f"🎉 Generated {len(parlays)} parlays from drop {drop_event_id}")
        else:
            print(f"⚠️ No parlays generated from drop {drop_event_id}")
            
    except Exception as e:
        print(f"❌ Error in parlay generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Test
    engine = SmartParlayEngine()
    parlays = engine.generate_all_parlays()
    
    print(f"\n📊 SUMMARY:")
    print(f"Total parlays: {len(parlays)}")
    
    for p in parlays[:5]:
        print(f"\n{p['strategy']} - {p['num_legs']} legs @ {p['combined_odds']}x")
        print(f"  EV: {p['expected_value']}% | Win prob: {p['estimated_win_prob']}%")
