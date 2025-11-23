import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from config import DATABASE_URL

Base = declarative_base()

# Модели (оставляем как есть)
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    is_ready = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=True)
    current_round = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

class Round(Base):
    __tablename__ = 'rounds'
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'))
    round_number = Column(Integer)
    question = Column(Text)
    is_active = Column(Boolean, default=True)
    hint1 = Column(Text, default="")
    hint2 = Column(Text, default="")
    hint3 = Column(Text, default="")
    winner_id = Column(Integer, nullable=True)

class PlayerAnswer(Base):
    __tablename__ = 'player_answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    answer = Column(Text)
    submitted_at = Column(DateTime, default=func.now())

class Database:
    def __init__(self):
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        self.engine = create_async_engine(db_url, echo=False, future=True)
        self.AsyncSession = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def __aenter__(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()

    async def get_session(self):
        async with self.AsyncSession() as session:
            yield session
