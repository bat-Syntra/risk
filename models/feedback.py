"""
User feedback and vouch models
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, Text, DateTime, Boolean, Date, ForeignKey
from sqlalchemy.sql import func
from database import Base


class UserFeedback(Base):
    """User feedback on bets or system"""
    __tablename__ = 'user_feedbacks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    bet_id = Column(Integer, nullable=True)  # Optional: related bet
    feedback_type = Column(String(20), nullable=False)  # 'good' or 'bad'
    message = Column(Text, nullable=True)  # Optional user message
    bet_type = Column(String(20), nullable=True)  # 'middle', 'arbitrage', 'good_ev'
    bet_amount = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    match_info = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    seen_by_admin = Column(Boolean, default=False)


class UserVouch(Base):
    """User vouch for winning bets"""
    __tablename__ = 'user_vouches'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    bet_id = Column(Integer, nullable=False)
    bet_type = Column(String(20), nullable=False)  # 'middle', 'arbitrage', 'good_ev'
    bet_amount = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    match_info = Column(Text, nullable=False)  # Match name/description
    match_date = Column(Date, nullable=True)
    sport = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    seen_by_admin = Column(Boolean, default=False)
