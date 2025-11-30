"""
DropEvent model to persist incoming arbitrage alerts (drops)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from database import Base


class DropEvent(Base):
    __tablename__ = "drop_events"
    id = Column(Integer, primary_key=True, index=True)
    # unique event id from source
    event_id = Column(String(100), unique=True, index=True, nullable=False)

    # quick-access fields
    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    bet_type = Column(String(20), index=True)  # arbitrage, middle, good_ev
    arb_percentage = Column(Float)
    match = Column(String(255))
    league = Column(String(255))
    market = Column(String(255))

    # full payload as JSON for later rendering
    payload = Column(JSON)

    __table_args__ = (
        UniqueConstraint('event_id', name='uq_drop_event_event_id'),
    )

    def __repr__(self) -> str:
        return f"<DropEvent(event_id={self.event_id}, arb={self.arb_percentage})>"
