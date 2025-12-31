from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.core.database import Base
from datetime import datetime

class ActiveSession(Base):
    __tablename__ = "active_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
