from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from bot.config import settings

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    goals = Column(Text, nullable=True)
    timezone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class DailyEntry(Base):
    __tablename__ = 'daily_entries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow().date)
    morning_mood = Column(String(50), nullable=True)
    morning_suggestions = Column(Text, nullable=True)
    evening_report = Column(Text, nullable=True)
    actions_done = Column(Text, nullable=True)
    obstacles = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' или 'assistant'
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Синхронный движок и фабрика сессий
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(engine)