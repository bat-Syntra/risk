"""
Admin Role System - Multi-level admin permissions
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class AdminAction(Base):
    """Pending admin actions that require super admin approval"""
    __tablename__ = 'admin_actions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, nullable=False, index=True)  # telegram_id of admin who requested
    action_type = Column(String(50), nullable=False)  # 'free_access', 'broadcast', 'ban', 'unban'
    target_user_id = Column(Integer, nullable=True)  # For user-specific actions
    details = Column(Text, nullable=True)  # JSON string with action details
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)  # telegram_id of super admin who reviewed
    notes = Column(Text, nullable=True)  # Rejection reason or notes
