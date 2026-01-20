# backend/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from .database import Base

class Visitor(Base):
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    sender = Column(String)
    text = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())