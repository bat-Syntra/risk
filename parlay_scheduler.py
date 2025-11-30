#!/usr/bin/env python3
"""
Parlay Scheduler - Runs every hour to generate fresh parlays
"""
import asyncio
import logging
from datetime import datetime
from simple_parlay_generator import generate_simple_parlays

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_scheduler():
    """Run parlay generation every hour"""
    logger.info("🚀 Starting Parlay Scheduler")
    
    while True:
        try:
            # Generate parlays
            logger.info(f"⏰ Running generation at {datetime.now()}")
            generate_simple_parlays()
            
            # Wait 1 hour
            logger.info("💤 Waiting 1 hour until next generation...")
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            await asyncio.sleep(300)  # Wait 5 min on error

if __name__ == "__main__":
    print("=" * 50)
    print("PARLAY SCHEDULER - Generates parlays every hour")
    print("=" * 50)
    print("\nPress Ctrl+C to stop\n")
    
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\n✋ Scheduler stopped")
