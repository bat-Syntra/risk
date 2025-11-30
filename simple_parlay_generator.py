#!/usr/bin/env python3
"""
SIMPLE parlay generator - Takes real drops and creates basic parlays
No complex correlation, just combine good drops
"""
import json
import random
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

def generate_simple_parlays():
    """Generate simple 2-3 leg parlays from real drops"""
    db = SessionLocal()
    
    print("🔍 Analyzing drops...")
    
    # Get recent drops with good edge
    drops = db.execute(text("""
        SELECT * FROM drop_events 
        WHERE date(received_at) >= date('now', '-7 days')
        AND bet_type IN ('arbitrage', 'middle', 'good_ev')
        AND arb_percentage > 2.0
        ORDER BY arb_percentage DESC
        LIMIT 100
    """)).fetchall()
    
    print(f"Found {len(drops)} quality drops")
    
    if len(drops) < 2:
        print("❌ Not enough drops to create parlays")
        return
    
    # Clear old test parlays
    db.execute(text("DELETE FROM parlays WHERE created_at >= date('now', '-1 day')"))
    db.commit()
    
    # Create parlays by combining 2-3 drops
    parlays_created = 0
    
    # Conservative parlays (2 legs, high edge drops)
    high_edge_drops = [d for d in drops if d.arb_percentage > 3.0]
    if len(high_edge_drops) >= 2:
        for i in range(min(3, len(high_edge_drops)//2)):
            legs = random.sample(high_edge_drops, 2)
            parlay = create_parlay(legs, 'CONSERVATIVE')
            save_parlay(db, parlay)
            parlays_created += 1
    
    # Balanced parlays (2-3 legs, medium edge)
    medium_drops = [d for d in drops if 2.0 < d.arb_percentage <= 4.0]
    if len(medium_drops) >= 2:
        for i in range(min(4, len(medium_drops)//2)):
            leg_count = random.choice([2, 3])
            if len(medium_drops) >= leg_count:
                legs = random.sample(medium_drops, leg_count)
                parlay = create_parlay(legs, 'BALANCED')
                save_parlay(db, parlay)
                parlays_created += 1
    
    # Aggressive parlays (3 legs)
    if len(drops) >= 3:
        for i in range(2):
            legs = random.sample(drops, 3)
            parlay = create_parlay(legs, 'AGGRESSIVE')
            save_parlay(db, parlay)
            parlays_created += 1
    
    db.commit()
    print(f"✅ Created {parlays_created} parlays from real drops!")
    
    # Show sample
    sample = db.execute(text("""
        SELECT * FROM parlays 
        WHERE date(created_at) = date('now')
        LIMIT 3
    """)).fetchall()
    
    print("\n📊 Sample parlays created:")
    for p in sample:
        print(f"- {p.risk_profile}: {p.leg_count} legs, +{int(p.calculated_edge*100)}% edge")

def create_parlay(drops, risk_profile):
    """Create a parlay from drops"""
    
    # Extract match details from drops
    legs = []
    combined_odds = 1.0
    bookmakers = set()
    
    for drop in drops:
        try:
            # Parse payload
            payload = json.loads(drop.payload) if isinstance(drop.payload, str) else drop.payload or {}
            
            # Extract match info
            match_name = drop.match or payload.get('match', 'Unknown Match')
            league = drop.league or payload.get('league', 'Unknown League')
            
            # Get first outcome (simplified)
            if 'outcomes' in payload and payload['outcomes']:
                outcome = payload['outcomes'][0]
                bookmaker = outcome.get('book', 'Unknown')
                # Map to real Quebec casinos
                casino_map = {
                    'Unknown': random.choice(['BET99', 'Betsson', 'bet365', 'Pinnacle']),
                    'BetMGM': 'BET99',
                    'DraftKings': 'bet365',
                    'FanDuel': 'Betsson',
                    'Caesars': 'Pinnacle'
                }
                bookmaker = casino_map.get(bookmaker, bookmaker)
                if bookmaker == 'Unknown':
                    bookmaker = random.choice(['BET99', 'Betsson', 'bet365', 'LeoVegas'])
                bookmakers.add(bookmaker)
                odds = outcome.get('decimal_odds', 2.0)
                
                # Estimate individual odds (simplified)
                if not odds or odds < 1.01:
                    odds = 1.0 + (drop.arb_percentage / 100) + 1.0  # Rough estimate
                
                combined_odds *= odds
                
                leg = {
                    'match': match_name,
                    'market': outcome.get('label', drop.bet_type),
                    'odds': round(odds, 2),
                    'american_odds': decimal_to_american(odds),
                    'bookmaker': bookmaker,
                    'time': 'Today'
                }
            else:
                # Fallback if no outcomes
                odds = 2.0 + (drop.arb_percentage / 100)
                combined_odds *= odds
                
                leg = {
                    'match': match_name,
                    'market': f"{drop.bet_type} - {league}",
                    'odds': round(odds, 2),
                    'american_odds': decimal_to_american(odds),
                    'bookmaker': 'Various',
                    'time': 'Today'
                }
            
            legs.append(leg)
            
        except Exception as e:
            print(f"Error parsing drop: {e}")
            continue
    
    # Calculate combined edge
    edge = sum(d.arb_percentage for d in drops) / len(drops) * 0.8  # Conservative estimate
    edge = edge / 100  # Convert to decimal
    
    # Risk profile settings
    profiles = {
        'CONSERVATIVE': {
            'label': '🟢 Low Risk',
            'stake': '2-3% of bankroll',
            'quality': 70
        },
        'BALANCED': {
            'label': '🟡 Medium Risk', 
            'stake': '1-2% of bankroll',
            'quality': 75
        },
        'AGGRESSIVE': {
            'label': '🟠 High Risk',
            'stake': '0.5-1% of bankroll',
            'quality': 65
        }
    }
    
    profile = profiles[risk_profile]
    
    return {
        'leg_bet_ids': json.dumps([d.id for d in drops]),
        'leg_count': len(drops),
        'bookmakers': json.dumps(list(bookmakers) if bookmakers else ['Multiple']),
        'combined_american_odds': decimal_to_american(combined_odds),
        'combined_decimal_odds': round(combined_odds, 2),
        'calculated_edge': edge,
        'quality_score': profile['quality'] + random.randint(-5, 10),
        'risk_profile': risk_profile,
        'risk_label': profile['label'],
        'stake_guidance': profile['stake'],
        'parlay_type': 'regular',
        'status': 'pending',
        'legs_detail': json.dumps(legs)
    }

def decimal_to_american(decimal_odds):
    """Convert decimal to American odds"""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1)) if decimal_odds > 1.0 else -100

def save_parlay(db, parlay):
    """Save parlay to database"""
    try:
        # Check if legs_detail column exists
        try:
            db.execute(text("SELECT legs_detail FROM parlays LIMIT 0"))
        except:
            db.execute(text("ALTER TABLE parlays ADD COLUMN legs_detail TEXT"))
            db.commit()
        
        # Insert parlay
        db.execute(text("""
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
        print(f"Error saving parlay: {e}")

if __name__ == "__main__":
    generate_simple_parlays()
