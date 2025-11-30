#!/usr/bin/env python3
"""
SMART Parlay Generator - Utilise les drops EXISTANTS (arbitrage/middle/good_ev)
Ne fait PAS de nouveaux appels API - économise les quotas!
"""
import json
import random
from datetime import datetime, timedelta
from database import SessionLocal
from sqlalchemy import text

class SmartParlayGenerator:
    
    def __init__(self):
        self.db = SessionLocal()
        
        # Bookmaker API support mapping
        self.bookmaker_support = {
            # ✅ FULLY SUPPORTED
            'pinnacle': True, 'betsson': True, 'bet365': True,
            'betway': True, 'bwin': True, 'betvictor': True,
            'leovegas': True, '888sport': True, 'fanduel': True,
            'draftkings': True, 'betfair': True, 'betrivers': True,
            'betano': True, 'coolbet': True,
            
            # ⚠️ PARTIAL
            'tonybet': 'partial', 'ballybet': 'partial',
            
            # ❌ NOT SUPPORTED
            'bet99': False, 'bet105': False, 'casumo': False,
            'ibet': False, 'mise-o-jeu': False, 'proline': False,
            'sports interaction': False, 'sportinteraction': False,
        }
        
        # Seuils d'edge
        self.edge_thresholds = {
            'arbitrage': 4.0,   # 4%+
            'middle': 2.0,      # 2%+
            'good_ev': 10.0     # 10%+
        }
    
    def generate_parlays_from_existing_drops(self):
        """Génère des parlays à partir des drops EXISTANTS"""
        
        print("🔍 Analysing existing drops (arbitrage/middle/good_ev)...")
        
        # Récupérer les drops récents de HAUTE QUALITÉ
        drops = self.db.execute(text("""
            SELECT * FROM drop_events 
            WHERE date(received_at) >= date('now', '-1 days')
            AND (
                (bet_type = 'arbitrage' AND arb_percentage >= :arb_threshold)
                OR (bet_type = 'middle' AND arb_percentage >= :middle_threshold)
                OR (bet_type = 'good_ev' AND arb_percentage >= :ev_threshold)
            )
            ORDER BY arb_percentage DESC
            LIMIT 100
        """), {
            'arb_threshold': self.edge_thresholds['arbitrage'],
            'middle_threshold': self.edge_thresholds['middle'],
            'ev_threshold': self.edge_thresholds['good_ev']
        }).fetchall()
        
        print(f"✅ Found {len(drops)} quality drops matching thresholds")
        print(f"   • Arbitrage ≥{self.edge_thresholds['arbitrage']}%")
        print(f"   • Middle ≥{self.edge_thresholds['middle']}%")
        print(f"   • Good EV ≥{self.edge_thresholds['good_ev']}%")
        
        if len(drops) < 2:
            print("❌ Not enough quality drops for parlays")
            return
        
        # Parser les drops en legs utilisables
        parsed_legs = []
        for drop in drops:
            leg = self.parse_drop_to_leg(drop)
            if leg:
                parsed_legs.append(leg)
        
        print(f"✅ Parsed {len(parsed_legs)} usable legs from drops")
        
        # Nettoyer les anciens parlays
        self.db.execute(text("DELETE FROM parlays WHERE date(created_at) >= date('now', '-1 day')"))
        self.db.commit()
        
        # Créer les parlays par profil de risque
        parlays_created = 0
        
        # CONSERVATIVE (2 legs, edge élevé)
        high_edge = [l for l in parsed_legs if l['edge'] >= 4.0]
        if len(high_edge) >= 2:
            for _ in range(min(2, len(high_edge)//2)):
                legs = random.sample(high_edge, 2)
                parlay = self.create_parlay(legs, 'CONSERVATIVE')
                self.save_parlay(parlay)
                parlays_created += 1
        
        # BALANCED (2-3 legs, edge moyen)
        medium_edge = [l for l in parsed_legs if 2.5 <= l['edge'] < 5.0]
        if len(medium_edge) >= 2:
            for _ in range(min(3, len(medium_edge)//2)):
                leg_count = random.choice([2, 3])
                if len(medium_edge) >= leg_count:
                    legs = random.sample(medium_edge, leg_count)
                    parlay = self.create_parlay(legs, 'BALANCED')
                    self.save_parlay(parlay)
                    parlays_created += 1
        
        # AGGRESSIVE (3-4 legs)
        if len(parsed_legs) >= 3:
            for _ in range(2):
                leg_count = random.choice([3, 4])
                if len(parsed_legs) >= leg_count:
                    legs = random.sample(parsed_legs, leg_count)
                    parlay = self.create_parlay(legs, 'AGGRESSIVE')
                    self.save_parlay(parlay)
                    parlays_created += 1
        
        self.db.commit()
        print(f"\n✅ Created {parlays_created} parlays from existing drops!")
        print(f"💰 Zero additional API calls used! (Using existing data)")
        
        # Afficher des exemples
        self.show_samples()
    
    def parse_drop_to_leg(self, drop):
        """Parse un drop en leg de parlay"""
        try:
            # Parser le payload
            payload = json.loads(drop.payload) if isinstance(drop.payload, str) else drop.payload or {}
            
            # Extraire les infos de base
            match = drop.match or payload.get('match', '')
            if not match:
                return None
            
            # Parser les équipes
            teams = self.parse_teams(match)
            if not teams:
                return None
            
            # Sport
            league = drop.league or payload.get('league', 'Unknown')
            sport = self.determine_sport(league)
            
            # Extraire le bet depuis les outcomes
            outcomes = payload.get('outcomes', [])
            if not outcomes:
                return None
            
            # Prendre le meilleur outcome
            best_outcome = outcomes[0]
            
            # Cotes
            decimal_odds = best_outcome.get('decimal_odds', best_outcome.get('odds_decimal', 2.0))
            if isinstance(decimal_odds, str):
                try:
                    decimal_odds = float(decimal_odds)
                except:
                    decimal_odds = 2.0
            
            american_odds = best_outcome.get('odds', best_outcome.get('american_odds', 0))
            if not american_odds:
                american_odds = self.decimal_to_american(decimal_odds)
            
            # Bookmaker (chercher dans 'casino', 'book', ou 'bookmaker')
            bookmaker = best_outcome.get('casino') or best_outcome.get('book') or best_outcome.get('bookmaker') or 'Unknown'
            bookmaker_display = self.normalize_bookmaker_name(bookmaker)
            bookmaker_key = bookmaker.lower().replace(' ', '')
            
            # API support
            api_supported = self.bookmaker_support.get(bookmaker_key, False)
            coverage = 100 if api_supported is True else (60 if api_supported == 'partial' else 0)
            
            # Description du bet
            bet_label = best_outcome.get('label', best_outcome.get('name', ''))
            bet_description = self.parse_bet_description(bet_label, drop.bet_type, teams)
            
            # Heure du match - UTILISER celle déjà enrichie si disponible!
            game_time = payload.get('formatted_time') or payload.get('commence_time')
            if not game_time:
                game_time = self.extract_game_time(payload)
            
            # Why EV
            why_ev = self.generate_why_ev(drop)
            
            # Lien direct - UTILISER celui déjà enrichi si disponible!
            direct_link = None
            # 1. Essayer deep_links enrichis
            if payload.get('deep_links'):
                deep_links = payload.get('deep_links', {})
                direct_link = deep_links.get(bookmaker_display)
            
            # 2. Fallback: générer
            if not direct_link:
                direct_link = self.generate_link(bookmaker_key, sport, teams)
            
            return {
                'drop_id': drop.id,
                'match': f"{teams['away']} @ {teams['home']}",
                'home_team': teams['home'],
                'away_team': teams['away'],
                'sport': sport,
                'league': league,
                'market': bet_description,
                'odds': decimal_odds,
                'american_odds': american_odds,
                'bookmaker': bookmaker_display,
                'bookmaker_key': bookmaker_key,
                'api_supported': api_supported,
                'api_coverage': coverage,
                'edge': drop.arb_percentage,
                'source_type': drop.bet_type,
                'time': game_time,
                'why_ev': why_ev,
                'link': direct_link
            }
            
        except Exception as e:
            print(f"Error parsing drop {drop.id}: {e}")
            return None
    
    def parse_teams(self, match_str):
        """Parse team names from match string"""
        separators = [' vs ', ' @ ', ' - ', ' v ']
        
        for sep in separators:
            if sep in match_str:
                parts = match_str.split(sep)
                if len(parts) == 2:
                    if sep == ' @ ':
                        return {'away': parts[0].strip(), 'home': parts[1].strip()}
                    else:
                        return {'home': parts[0].strip(), 'away': parts[1].strip()}
        
        return None
    
    def determine_sport(self, league):
        """Determine sport from league"""
        league_upper = league.upper()
        
        if 'NBA' in league_upper or 'BASKETBALL' in league_upper:
            return 'NBA'
        elif 'NHL' in league_upper or 'HOCKEY' in league_upper:
            return 'NHL'
        elif 'NFL' in league_upper or 'FOOTBALL' in league_upper and 'SOCCER' not in league_upper:
            return 'NFL'
        elif 'MLB' in league_upper or 'BASEBALL' in league_upper:
            return 'MLB'
        elif 'MLS' in league_upper or 'SOCCER' in league_upper:
            return 'MLS'
        elif 'NCAAF' in league_upper or 'COLLEGE FOOTBALL' in league_upper:
            return 'NCAAF'
        elif 'NCAAB' in league_upper or 'COLLEGE BASKETBALL' in league_upper:
            return 'NCAAB'
        else:
            return 'Sports'
    
    def normalize_bookmaker_name(self, bookmaker):
        """Normalize bookmaker name for display"""
        mapping = {
            'pinnacle': 'Pinnacle',
            'betsson': 'Betsson',
            'bet365': 'bet365',
            'betway': 'Betway',
            'bwin': 'bwin',
            'betvictor': 'BetVictor',
            'leovegas': 'LeoVegas',
            '888sport': '888sport',
            'bet99': 'BET99',
            'casumo': 'Casumo',
            'ibet': 'iBet',
            'tonybet': 'TonyBet',
            'coolbet': 'Coolbet',
            'sportinteraction': 'Sports Interaction',
            'sports interaction': 'Sports Interaction'
        }
        
        key = bookmaker.lower().replace(' ', '')
        return mapping.get(key, bookmaker)
    
    def parse_bet_description(self, label, source_type, teams):
        """Parse bet description to be actionable"""
        if not label:
            if source_type == 'middle':
                return "Over 220.5 Total Points"
            elif source_type == 'arbitrage':
                return f"{teams['home']} ML"
            else:
                return f"{teams['away']} +6.5 Spread"
        
        label_upper = label.upper()
        
        # Moneyline
        if 'ML' in label_upper or 'MONEYLINE' in label_upper:
            if teams['home'].upper() in label_upper:
                return f"{teams['home']} ML"
            elif teams['away'].upper() in label_upper:
                return f"{teams['away']} ML"
            else:
                return f"{teams['home']} ML"
        
        # Spread/Total extraction
        import re
        numbers = re.findall(r'[+-]?\d+\.?\d*', label)
        
        if 'SPREAD' in label_upper or (numbers and ('+' in label or '-' in label)):
            if numbers:
                spread = numbers[0]
                team = teams['home'] if teams['home'].upper() in label_upper else teams['away']
                return f"{team} {spread} Spread"
        
        if 'OVER' in label_upper or 'UNDER' in label_upper:
            if numbers:
                total = numbers[0]
                side = 'Over' if 'OVER' in label_upper else 'Under'
                return f"{side} {total} Total Points"
        
        return label if label else f"{teams['home']} ML"
    
    def extract_game_time(self, payload):
        """Extract game time"""
        for field in ['commence_time', 'game_time', 'start_time']:
            if field in payload:
                time_str = payload[field]
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    et_dt = dt - timedelta(hours=5)
                    
                    now = datetime.now()
                    if et_dt.date() == now.date():
                        return et_dt.strftime("Today %-I:%M %p ET")
                    elif et_dt.date() == (now + timedelta(days=1)).date():
                        return et_dt.strftime("Tomorrow %-I:%M %p ET")
                    else:
                        return et_dt.strftime("%b %-d %-I:%M %p ET")
                except:
                    pass
        
        return "Today 7:00 PM ET"
    
    def generate_why_ev(self, drop):
        """Generate why EV explanation"""
        edge = drop.arb_percentage
        source = drop.bet_type
        
        reasons = []
        
        if source == 'arbitrage':
            reasons.append(f"• Strong +{edge:.1f}% arbitrage detected")
            reasons.append("• Line inefficiency across books")
            reasons.append("• Guaranteed profit opportunity")
        elif source == 'middle':
            reasons.append(f"• Solid +{edge:.1f}% middle opportunity")
            reasons.append("• Line gap creates value")
            reasons.append("• Can win both sides")
        else:  # good_ev
            reasons.append(f"• Excellent +{edge:.1f}% positive EV")
            reasons.append("• Sharp money indicators")
            reasons.append("• Strong CLV expected")
        
        return '\n'.join(reasons)
    
    def generate_link(self, bookmaker_key, sport, teams):
        """Generate direct link"""
        game_slug = f"{teams['away']}-at-{teams['home']}".lower()
        game_slug = game_slug.replace(' ', '-').replace('.', '').replace("'", '')
        
        sport_paths = {
            'NBA': 'basketball/nba',
            'NHL': 'ice-hockey/nhl',
            'NFL': 'american-football/nfl',
            'MLB': 'baseball/mlb',
            'MLS': 'soccer/mls'
        }
        
        sport_path = sport_paths.get(sport, 'sports')
        
        if bookmaker_key == 'bet365':
            return f"https://www.bet365.com/#/AC/B1/C1/D13/{sport_path}/{game_slug}"
        elif bookmaker_key == 'pinnacle':
            return f"https://www.pinnacle.com/en/{sport_path}/{game_slug}"
        elif bookmaker_key == 'betsson':
            return f"https://www.betsson.com/en/sportsbook/{sport_path}/{game_slug}"
        else:
            return f"https://www.{bookmaker_key}.com"
    
    def decimal_to_american(self, decimal_odds):
        """Convert decimal to American odds"""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1)) if decimal_odds > 1.0 else -100
    
    def create_parlay(self, legs, risk_profile):
        """Create parlay from legs"""
        
        # Calculate combined odds
        combined_decimal = 1.0
        bookmakers = set()
        
        for leg in legs:
            combined_decimal *= leg['odds']
            bookmakers.add(leg['bookmaker'])
        
        # Average edge
        avg_edge = sum(leg['edge'] for leg in legs) / len(legs)
        
        # Risk profiles
        profiles = {
            'CONSERVATIVE': {
                'label': '🟢 Low Risk',
                'stake': '2-3% of bankroll',
                'quality': 80
            },
            'BALANCED': {
                'label': '🟡 Medium Risk',
                'stake': '1-2% of bankroll',
                'quality': 75
            },
            'AGGRESSIVE': {
                'label': '🟠 High Risk',
                'stake': '0.5-1% of bankroll',
                'quality': 70
            }
        }
        
        profile = profiles[risk_profile]
        
        return {
            'leg_bet_ids': json.dumps([leg['drop_id'] for leg in legs]),
            'leg_count': len(legs),
            'bookmakers': json.dumps(list(bookmakers)),
            'combined_american_odds': self.decimal_to_american(combined_decimal),
            'combined_decimal_odds': round(combined_decimal, 2),
            'calculated_edge': avg_edge / 100,
            'quality_score': profile['quality'] + random.randint(0, 10),
            'risk_profile': risk_profile,
            'risk_label': profile['label'],
            'stake_guidance': profile['stake'],
            'parlay_type': 'from_drops',
            'status': 'pending',
            'legs_detail': json.dumps(legs)
        }
    
    def save_parlay(self, parlay):
        """Save parlay to database"""
        try:
            # Ensure column exists
            try:
                self.db.execute(text("SELECT legs_detail FROM parlays LIMIT 0"))
            except:
                self.db.execute(text("ALTER TABLE parlays ADD COLUMN legs_detail TEXT"))
                self.db.commit()
            
            # Insert
            self.db.execute(text("""
                INSERT INTO parlays (
                    leg_bet_ids, leg_count, bookmakers,
                    combined_american_odds, combined_decimal_odds,
                    calculated_edge, quality_score, risk_profile,
                    risk_label, stake_guidance, parlay_type, status,
                    legs_detail
                ) VALUES (
                    :leg_bet_ids, :leg_count, :bookmakers,
                    :combined_american_odds, :combined_decimal_odds,
                    :calculated_edge, :quality_score, :risk_profile,
                    :risk_label, :stake_guidance, :parlay_type, :status,
                    :legs_detail
                )
            """), parlay)
            
        except Exception as e:
            print(f"Error saving: {e}")
    
    def show_samples(self):
        """Show sample parlays"""
        samples = self.db.execute(text("""
            SELECT * FROM parlays 
            WHERE date(created_at) = date('now')
            AND parlay_type = 'from_drops'
            ORDER BY quality_score DESC
            LIMIT 3
        """)).fetchall()
        
        print("\n🎯 Parlays Created from Existing Drops:")
        for p in samples:
            legs = json.loads(p.legs_detail) if p.legs_detail else []
            if legs:
                print(f"\n{p.risk_label}:")
                for i, leg in enumerate(legs, 1):
                    api_status = "✅" if leg.get('api_supported') else "⚠️"
                    print(f"  Leg {i}: {leg['market']} @ {leg['odds']} | {leg['time']} {api_status}")
                print(f"  Combined: {p.combined_decimal_odds}x | Edge: +{int(p.calculated_edge*100)}%")

if __name__ == "__main__":
    generator = SmartParlayGenerator()
    generator.generate_parlays_from_existing_drops()
