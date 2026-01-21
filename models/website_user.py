"""
Website User model for storing web registration data
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WebsiteUser(Base):
    __tablename__ = 'website_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_verified = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<WebsiteUser(id={self.id}, telegram_id={self.telegram_id}, email='{self.email}')>"
