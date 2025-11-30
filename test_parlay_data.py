#!/usr/bin/env python3
"""
Generate test parlays for testing the system
"""
import json
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

def create_test_parlays():
    """Create some test parlays in the database"""
    db = SessionLocal()
    
    try:
        # Create test parlays
        test_parlays = [
            {
                'leg_bet_ids': json.dumps([1, 2]),
                'leg_count': 2,
                'bookmakers': json.dumps(['BET99', 'Betsson']),
                'combined_american_odds': 250,
                'combined_decimal_odds': 3.5,
                'calculated_edge': 0.15,
                'quality_score': 75,
                'risk_profile': 'BALANCED',
                'risk_label': '🟡 Medium Risk',
                'stake_guidance': '1-2% of bankroll',
                'parlay_type': 'regular',
                'status': 'pending'
            },
            {
                'leg_bet_ids': json.dumps([3, 4, 5]),
                'leg_count': 3,
                'bookmakers': json.dumps(['bet365', 'Pinnacle', 'LeoVegas']),
                'combined_american_odds': 450,
                'combined_decimal_odds': 5.5,
                'calculated_edge': 0.22,
                'quality_score': 82,
                'risk_profile': 'AGGRESSIVE',
                'risk_label': '🟠 High Risk',
                'stake_guidance': '0.5-1% of bankroll',
                'parlay_type': 'correlated',
                'status': 'pending'
            },
            {
                'leg_bet_ids': json.dumps([6, 7]),
                'leg_count': 2,
                'bookmakers': json.dumps(['Sports Interaction', 'BetVictor']),
                'combined_american_odds': 180,
                'combined_decimal_odds': 2.8,
                'calculated_edge': 0.10,
                'quality_score': 65,
                'risk_profile': 'CONSERVATIVE',
                'risk_label': '🟢 Low Risk',
                'stake_guidance': '2-3% of bankroll',
                'parlay_type': 'regular',
                'status': 'pending'
            }
        ]
        
        for parlay in test_parlays:
            db.execute(text("""
                INSERT INTO parlays (
                    leg_bet_ids, leg_count, bookmakers,
                    combined_american_odds, combined_decimal_odds,
                    calculated_edge, quality_score, risk_profile,
                    risk_label, stake_guidance, parlay_type, status
                ) VALUES (
                    :leg_bet_ids, :leg_count, :bookmakers,
                    :combined_american_odds, :combined_decimal_odds,
                    :calculated_edge, :quality_score, :risk_profile,
                    :risk_label, :stake_guidance, :parlay_type, :status
                )
            """), parlay)
        
        db.commit()
        print(f"✅ Created {len(test_parlays)} test parlays!")
        
    except Exception as e:
        print(f"❌ Error creating test parlays: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_parlays()
