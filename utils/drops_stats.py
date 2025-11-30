from __future__ import annotations
from datetime import datetime, date, time
from typing import Tuple

from core.tiers import TierManager, TierLevel as CoreTierLevel
from database import SessionLocal
from models.drop_event import DropEvent


def record_drop(drop: dict) -> int:
    """Persist or update a drop in the database for later retrieval.

    Ensures calculators and 'Last Calls' work even after process restarts.
    
    Returns:
        int: The drop_event_id (database ID) or None if failed
    """
    if not drop:
        return None
    try:
        eid = str(drop.get("event_id") or "").strip()
        if not eid:
            return None
        db = SessionLocal()
        try:
            ev = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
            now = datetime.now()
            bet_type = str(drop.get("bet_type") or "arbitrage")
            if ev is None:
                ev = DropEvent(
                    event_id=eid,
                    bet_type=bet_type,
                    arb_percentage=float(drop.get("arb_percentage") or 0.0),
                    match=str(drop.get("match") or ""),
                    league=str(drop.get("league") or ""),
                    market=str(drop.get("market") or ""),
                    payload=drop,
                )
                ev.received_at = now
                db.add(ev)
            else:
                # Update core fields, keep existing bet_type unless a new one is explicitly provided
                if "bet_type" in drop and drop.get("bet_type"):
                    ev.bet_type = bet_type
                ev.arb_percentage = float(drop.get("arb_percentage") or ev.arb_percentage or 0.0)
                ev.match = str(drop.get("match") or ev.match or "")
                ev.league = str(drop.get("league") or ev.league or "")
                ev.market = str(drop.get("market") or ev.market or "")
                ev.payload = drop
                ev.received_at = now
            db.commit()
            
            # Refresh to get the ID
            db.refresh(ev)
            drop_id = ev.id
            
            return drop_id
        finally:
            db.close()
    except Exception:
        # Do not crash on persistence errors; calculator will fallback to memory
        return None


def get_today_stats_for_tier(tier: CoreTierLevel) -> Tuple[int, float]:
    """
    Return (count, sum_arbitrage_percentage) for drops visible to the given tier today.
    Pulls data from the persistent DropEvent table so it survives restarts.
    """
    start_of_day = datetime.combine(date.today(), time.min)
    db = SessionLocal()
    try:
        events = db.query(DropEvent).filter(DropEvent.received_at >= start_of_day).all()
        count = 0
        total_pct = 0.0
        for ev in events:
            try:
                arb = float(ev.arb_percentage or 0)
            except Exception:
                arb = 0.0
            if TierManager.can_view_alert(tier, arb):
                count += 1
                total_pct += arb
        return count, round(total_pct, 2)
    finally:
        db.close()
