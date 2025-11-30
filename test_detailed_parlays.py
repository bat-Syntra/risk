#!/usr/bin/env python3
"""
Create detailed test parlays with actual match information
"""
import json
from datetime import datetime, timedelta
from database import SessionLocal
from sqlalchemy import text

def create_detailed_parlays():
    """Create test parlays with real match details"""
    db = SessionLocal()
    
    try:
        # Clear existing test parlays
        db.execute(text("DELETE FROM parlays WHERE created_at >= date('now')"))
        db.commit()
        
        # Create detailed parlays with match info
        test_parlays = [
            {
                'leg_bet_ids': json.dumps([1, 2]),
                'leg_count': 2,
                'bookmakers': json.dumps(['BET99']),
                'combined_american_odds': 250,
                'combined_decimal_odds': 3.5,
                'calculated_edge': 0.15,
                'quality_score': 75,
                'risk_profile': 'BALANCED',
                'risk_label': '🟡 Medium Risk',
                'stake_guidance': '1-2% of bankroll',
                'parlay_type': 'regular',
                'status': 'pending',
                'legs_detail': json.dumps([
                    {
                        'match': 'Toronto Maple Leafs vs Montreal Canadiens',
                        'market': 'Total Goals Over 5.5',
                        'odds': 1.85,
                        'american_odds': -117,
                        'time': '19:00 EST'
                    },
                    {
                        'match': 'Edmonton Oilers vs Calgary Flames', 
                        'market': 'Connor McDavid Anytime Goal',
                        'odds': 1.89,
                        'american_odds': -112,
                        'time': '21:00 EST'
                    }
                ])
            },
            {
                'leg_bet_ids': json.dumps([3, 4, 5]),
                'leg_count': 3,
                'bookmakers': json.dumps(['Betsson']),
                'combined_american_odds': 450,
                'combined_decimal_odds': 5.5,
                'calculated_edge': 0.22,
                'quality_score': 82,
                'risk_profile': 'AGGRESSIVE',
                'risk_label': '🟠 High Risk',
                'stake_guidance': '0.5-1% of bankroll',
                'parlay_type': 'correlated',
                'status': 'pending',
                'legs_detail': json.dumps([
                    {
                        'match': 'Boston Bruins vs New York Rangers',
                        'market': 'Bruins Win + Over 5.5',
                        'odds': 2.20,
                        'american_odds': 120,
                        'time': '19:30 EST'
                    },
                    {
                        'match': 'Colorado Avalanche vs Vegas Golden Knights',
                        'market': 'Nathan MacKinnon 2+ Points',
                        'odds': 1.75,
                        'american_odds': -133,
                        'time': '20:00 EST'
                    },
                    {
                        'match': 'Tampa Bay Lightning vs Florida Panthers',
                        'market': 'Both Teams Score 3+ Goals',
                        'odds': 1.43,
                        'american_odds': -233,
                        'time': '20:30 EST'
                    }
                ])
            },
            {
                'leg_bet_ids': json.dumps([6, 7]),
                'leg_count': 2,
                'bookmakers': json.dumps(['bet365', 'Pinnacle']),
                'combined_american_odds': 180,
                'combined_decimal_odds': 2.8,
                'calculated_edge': 0.10,
                'quality_score': 65,
                'risk_profile': 'CONSERVATIVE',
                'risk_label': '🟢 Low Risk',
                'stake_guidance': '2-3% of bankroll',
                'parlay_type': 'regular',
                'status': 'pending',
                'legs_detail': json.dumps([
                    {
                        'match': 'LA Lakers vs Golden State Warriors',
                        'market': 'Total Points Over 225.5',
                        'odds': 1.91,
                        'american_odds': -110,
                        'time': '22:30 EST'
                    },
                    {
                        'match': 'Milwaukee Bucks vs Boston Celtics',
                        'market': 'Giannis Antetokounmpo Over 29.5 Points',
                        'odds': 1.47,
                        'american_odds': -213,
                        'time': '19:00 EST'
                    }
                ])
            }
        ]
        
        for parlay in test_parlays:
            # First check if legs_detail column exists
            try:
                db.execute(text("SELECT legs_detail FROM parlays LIMIT 0"))
            except:
                # Add column if it doesn't exist
                db.execute(text("ALTER TABLE parlays ADD COLUMN legs_detail TEXT"))
                db.commit()
            
            # Insert with all fields including legs_detail
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
        
        db.commit()
        print(f"✅ Created {len(test_parlays)} DETAILED parlays with real match info!")
        
    except Exception as e:
        print(f"❌ Error creating detailed parlays: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_detailed_parlays()
