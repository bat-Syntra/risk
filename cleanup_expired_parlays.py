#!/usr/bin/env python3
"""
🧹 SMART PARLAY CLEANUP
- Supprime les legs expirés des parlays
- Si parlay a encore 2+ legs valides → garde avec nouveaux odds
- Si parlay a moins de 2 legs → supprime complètement
- Regenere de nouveaux parlays avec matchs actifs
"""
import json
from datetime import datetime, timezone
from database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_expired_parlays():
    """
    Smart cleanup:
    1. Check each parlay for expired legs
    2. Remove expired legs
    3. If 2+ legs remain → update parlay with new odds
    4. If <2 legs remain → mark as expired
    5. Regenerate new parlays
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Get all active parlays
        result = db.execute(text("SELECT id, legs_json, combined_odds, num_legs FROM parlays WHERE status = 'active'"))
        parlays = result.fetchall()
        
        updated_count = 0
        expired_count = 0
        
        for parlay in parlays:
            parlay_id = parlay[0]
            legs_json = parlay[1]
            
            try:
                legs = json.loads(legs_json) if legs_json else []
            except:
                legs = []
            
            # Filter out expired legs
            active_legs = []
            for leg in legs:
                commence_time = leg.get('commence_time')
                is_expired = False
                
                if commence_time:
                    try:
                        match_time = datetime.fromisoformat(str(commence_time).replace('Z', '+00:00'))
                        if match_time < now:
                            is_expired = True
                            logger.info(f"  ❌ Expired leg: {leg.get('match')} (started {match_time})")
                    except:
                        pass
                
                if not is_expired:
                    active_legs.append(leg)
            
            # Decide what to do with parlay
            if len(active_legs) == len(legs):
                # All legs still active, nothing to do
                continue
            elif len(active_legs) >= 2:
                # Still have 2+ legs, update parlay
                new_combined_odds = 1.0
                new_avg_edge = 0.0
                for leg in active_legs:
                    new_combined_odds *= leg.get('odds', 1.0)
                    new_avg_edge += leg.get('edge', 0.0)
                new_avg_edge = new_avg_edge / len(active_legs) if active_legs else 0
                
                # Update parlay
                db.execute(text("""
                    UPDATE parlays 
                    SET legs_json = :legs_json, 
                        combined_odds = :combined_odds,
                        num_legs = :num_legs,
                        avg_edge = :avg_edge
                    WHERE id = :id
                """), {
                    "id": parlay_id,
                    "legs_json": json.dumps(active_legs),
                    "combined_odds": new_combined_odds,
                    "num_legs": len(active_legs),
                    "avg_edge": new_avg_edge / 100  # Store as decimal
                })
                updated_count += 1
                logger.info(f"  ✅ Updated parlay #{parlay_id}: {len(legs)}→{len(active_legs)} legs, odds: {new_combined_odds:.2f}x")
            else:
                # Less than 2 legs, mark as expired
                db.execute(
                    text("UPDATE parlays SET status = 'expired' WHERE id = :id"),
                    {"id": parlay_id}
                )
                expired_count += 1
                logger.info(f"  🗑️ Expired parlay #{parlay_id}: only {len(active_legs)} leg(s) left")
        
        db.commit()
        
        if updated_count > 0 or expired_count > 0:
            logger.info(f"🧹 Cleanup done: {updated_count} updated, {expired_count} expired")
        else:
            logger.info("✅ All parlays still valid")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"Error cleaning up parlays: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db.close()

def regenerate_active_parlays():
    """Cleanup expired legs and regenerate new parlays"""
    from realtime_parlay_generator import on_drop_received
    
    # First cleanup expired
    logger.info("🧹 Step 1: Cleaning up expired legs...")
    expired_count = cleanup_expired_parlays()
    
    # Then regenerate new parlays
    logger.info("🔄 Step 2: Regenerating new parlays...")
    on_drop_received(0)
    
    return expired_count

if __name__ == "__main__":
    print("🧹 Smart Parlay Cleanup")
    print("=" * 40)
    expired = regenerate_active_parlays()
    print(f"\n✅ Done!")
