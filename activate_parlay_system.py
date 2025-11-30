#!/usr/bin/env python3
"""
Activate the REAL parlay system - Connect everything together
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from database import SessionLocal
from sqlalchemy import text
from utils.correlation_parlay_builder import CorrelatedParlayBuilder
from utils.hybrid_odds_tracker import HybridOddsTracker
from utils.risk_profile_system import RiskProfileClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealParlaySystem:
    """The REAL production parlay system"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.correlation_builder = CorrelatedParlayBuilder()
        self.odds_tracker = HybridOddsTracker()
        self.risk_system = RiskProfileClassifier()
        
    async def generate_parlays_from_drops(self):
        """Generate real parlays from actual drops"""
        
        # 1. Get today's drops (arbitrage, middle, good_ev)
        drops = self.db.execute(text("""
            SELECT * FROM drop_events 
            WHERE date(received_at) = date('now')
            AND bet_type IN ('arbitrage', 'middle', 'good_ev')
            AND arb_percentage > 2.0
            ORDER BY arb_percentage DESC
        """)).fetchall()
        
        logger.info(f"Found {len(drops)} drops to analyze")
        
        if not drops:
            logger.warning("No drops available for parlay generation")
            return []
        
        # 2. Extract games from drops
        games = []
        for drop in drops:
            try:
                payload = json.loads(drop.payload) if isinstance(drop.payload, str) else drop.payload
                
                game = {
                    'id': drop.id,
                    'teams': drop.match or 'Unknown',
                    'sport': drop.league or 'Unknown',
                    'commence_time': payload.get('commence_time', ''),
                    'outcomes': payload.get('outcomes', []),
                    'arb_percentage': drop.arb_percentage,
                    'bet_type': drop.bet_type
                }
                games.append(game)
            except Exception as e:
                logger.error(f"Error parsing drop {drop.id}: {e}")
                
        # 3. Find correlations
        correlated_sets = await self.correlation_builder.find_correlations(games)
        logger.info(f"Found {len(correlated_sets)} correlation patterns")
        
        # 4. Build parlays
        parlays = []
        for correlation in correlated_sets:
            # Calculate combined odds
            combined_odds = 1.0
            legs = []
            
            for game_id in correlation['game_ids']:
                game = next((g for g in games if g['id'] == game_id), None)
                if game:
                    # Extract best outcome
                    if game['outcomes']:
                        best_outcome = max(game['outcomes'], key=lambda x: x.get('odds', 0))
                        odds = best_outcome.get('decimal_odds', 2.0)
                        combined_odds *= odds
                        
                        legs.append({
                            'match': game['teams'],
                            'market': best_outcome.get('label', 'Unknown'),
                            'odds': odds,
                            'american_odds': best_outcome.get('odds', 100),
                            'bookmaker': best_outcome.get('book', 'Unknown')
                        })
            
            if len(legs) >= 2:
                # Apply correlation boost
                correlation_boost = correlation.get('strength', 1.0)
                combined_odds *= correlation_boost
                
                # Calculate edge
                fair_odds = combined_odds * 0.95  # Assume 5% vig
                edge = (combined_odds - fair_odds) / fair_odds
                
                # Determine risk profile
                risk_profile = self.risk_system.classify_parlay(
                    leg_count=len(legs),
                    combined_odds=combined_odds,
                    edge=edge
                )
                
                parlay = {
                    'leg_bet_ids': json.dumps([l['match'] for l in legs]),
                    'leg_count': len(legs),
                    'bookmakers': json.dumps(list(set(l['bookmaker'] for l in legs))),
                    'combined_american_odds': self._decimal_to_american(combined_odds),
                    'combined_decimal_odds': combined_odds,
                    'calculated_edge': edge,
                    'quality_score': correlation.get('quality_score', 50),
                    'risk_profile': risk_profile['profile'],
                    'risk_label': risk_profile['label'],
                    'stake_guidance': risk_profile['stake_guidance'],
                    'parlay_type': 'correlated' if correlation_boost > 1.0 else 'regular',
                    'status': 'pending',
                    'legs_detail': json.dumps(legs),
                    'correlation_pattern': correlation.get('pattern', 'unknown')
                }
                parlays.append(parlay)
                
        logger.info(f"Generated {len(parlays)} parlays")
        return parlays
    
    def _decimal_to_american(self, decimal_odds):
        """Convert decimal odds to American format"""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
    
    async def save_parlays(self, parlays):
        """Save generated parlays to database"""
        saved = 0
        for parlay in parlays:
            try:
                # Check if legs_detail column exists
                try:
                    self.db.execute(text("SELECT legs_detail FROM parlays LIMIT 0"))
                except:
                    self.db.execute(text("ALTER TABLE parlays ADD COLUMN legs_detail TEXT"))
                    self.db.execute(text("ALTER TABLE parlays ADD COLUMN correlation_pattern TEXT"))
                    self.db.commit()
                
                # Insert parlay
                self.db.execute(text("""
                    INSERT INTO parlays (
                        leg_bet_ids, leg_count, bookmakers,
                        combined_american_odds, combined_decimal_odds,
                        calculated_edge, quality_score, risk_profile,
                        risk_label, stake_guidance, parlay_type, status,
                        legs_detail, correlation_pattern
                    ) VALUES (
                        :leg_bet_ids, :leg_count, :bookmakers,
                        :combined_american_odds, :combined_decimal_odds,
                        :calculated_edge, :quality_score, :risk_profile,
                        :risk_label, :stake_guidance, :parlay_type, :status,
                        :legs_detail, :correlation_pattern
                    )
                """), parlay)
                saved += 1
                
            except Exception as e:
                logger.error(f"Error saving parlay: {e}")
                
        self.db.commit()
        logger.info(f"Saved {saved} parlays to database")
        return saved
    
    async def track_parlay_results(self, parlay_id, result):
        """Track parlay win/loss for ML training"""
        try:
            self.db.execute(text("""
                UPDATE parlays 
                SET status = :status,
                    actual_result = :result,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :parlay_id
            """), {
                'parlay_id': parlay_id,
                'status': 'completed',
                'result': result  # 'won' or 'lost'
            })
            self.db.commit()
            
            # Log for ML training data
            logger.info(f"Parlay {parlay_id} result: {result}")
            
            # Export to training data
            await self.export_training_data()
            
        except Exception as e:
            logger.error(f"Error tracking result: {e}")
    
    async def export_training_data(self):
        """Export parlay data for ML/LLM training"""
        try:
            # Get completed parlays with results
            results = self.db.execute(text("""
                SELECT * FROM parlays
                WHERE status = 'completed'
                AND actual_result IS NOT NULL
            """)).fetchall()
            
            training_data = []
            for parlay in results:
                training_data.append({
                    'legs': json.loads(parlay.legs_detail) if parlay.legs_detail else [],
                    'edge': parlay.calculated_edge,
                    'risk_profile': parlay.risk_profile,
                    'correlation': parlay.correlation_pattern,
                    'result': parlay.actual_result,
                    'odds': parlay.combined_decimal_odds
                })
            
            # Save to JSON for training
            with open('parlay_training_data.json', 'w') as f:
                json.dump(training_data, f, indent=2)
                
            logger.info(f"Exported {len(training_data)} parlays for ML training")
            
        except Exception as e:
            logger.error(f"Error exporting training data: {e}")
    
    async def run_continuous(self):
        """Run continuously - generate parlays every hour"""
        while True:
            try:
                logger.info("🔄 Generating new parlays...")
                
                # Generate parlays from drops
                parlays = await self.generate_parlays_from_drops()
                
                if parlays:
                    # Save to database
                    saved = await self.save_parlays(parlays)
                    logger.info(f"✅ Generated and saved {saved} new parlays")
                    
                    # Notify users (TODO: implement notification system)
                    # await self.notify_users(parlays)
                else:
                    logger.info("No new parlays to generate")
                
                # Wait 1 hour before next generation
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                await asyncio.sleep(300)  # Wait 5 min on error

async def main():
    """Main entry point"""
    system = RealParlaySystem()
    
    # Generate initial parlays
    parlays = await system.generate_parlays_from_drops()
    
    if parlays:
        saved = await system.save_parlays(parlays)
        print(f"✅ System activated! Generated {saved} real parlays from drops")
    else:
        print("⚠️ No drops available to generate parlays")
        print("The system needs real arbitrage/middle/good_ev drops to work!")
    
    # Uncomment to run continuously
    # await system.run_continuous()

if __name__ == "__main__":
    asyncio.run(main())
