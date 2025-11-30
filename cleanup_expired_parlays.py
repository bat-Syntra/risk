#!/usr/bin/env python3
"""
Cleanup expired parlays - removes parlays with matches that have started
Also regenerates parlays with only active matches
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
    Remove parlays that have legs with matches that have already started
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Get all active parlays
        result = db.execute(text("SELECT id, legs_json FROM parlays WHERE status = 'active'"))
        parlays = result.fetchall()
        
        expired_ids = []
        for parlay in parlays:
            parlay_id = parlay[0]
            legs_json = parlay[1]
            
            try:
                legs = json.loads(legs_json) if legs_json else []
            except:
                legs = []
            
            # Check each leg for expired matches
            for leg in legs:
                commence_time = leg.get('commence_time')
                if commence_time:
                    try:
                        match_time = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        if match_time < now:
                            expired_ids.append(parlay_id)
                            break
                    except:
                        pass
        
        # Mark expired parlays as expired
        if expired_ids:
            db.execute(
                text("UPDATE parlays SET status = 'expired' WHERE id IN :ids"),
                {"ids": tuple(expired_ids)}
            )
            db.commit()
            logger.info(f"🗑️ Marked {len(expired_ids)} expired parlays")
        else:
            logger.info("✅ No expired parlays found")
        
        return len(expired_ids)
        
    except Exception as e:
        logger.error(f"Error cleaning up parlays: {e}")
        return 0
    finally:
        db.close()

def regenerate_active_parlays():
    """Regenerate parlays with only active (future) matches"""
    from realtime_parlay_generator import on_drop_received
    
    # First cleanup expired
    expired_count = cleanup_expired_parlays()
    
    # Then regenerate
    logger.info("🔄 Regenerating parlays...")
    on_drop_received(0)
    
    return expired_count

if __name__ == "__main__":
    print("🧹 Cleaning up expired parlays...")
    expired = cleanup_expired_parlays()
    print(f"Done! {expired} parlays marked as expired")
