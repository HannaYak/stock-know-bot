import asyncio
from typing import List, Optional
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from config import DATABASE_URL

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String)
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
    is_active = Column(Boolean, default=False)
    hint1 = Column(Text, default="")
    hint2 = Column(Text, default="")
    hint3 = Column(Text, default="")
    winner_id = Column(Integer, ForeignKey('users.id'))

class PlayerAnswer(Base):
    __tablename__ = 'player_answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    answer = Column(Text)
    submitted_at = Column(DateTime, default=func.now())

class Database:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.engine = None
        self.sessionmaker = None
    
    async def __aenter__(self):
        # Для PostgreSQL добавляем параметры
        if self.db_url.startswith('postgresql'):
            self.db_url += f"?server_settings=TimeZone=UTC"
        
        self.engine = create_async_engine(
            self.db_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False,
            future=True
        )
        self.sessionmaker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        
        # Создаём таблицы
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.engine:
            await self.engine.dispose()
    
    async def get_session(self) -> AsyncSession:
        return self.sessionmaker()
    
    async def get_or_create_user(self, user_id: int, username: str, first_name: str) -> User:
        async with self.get_session() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                if not user:
                    user = User(id=user_id, username=username, first_name=first_name)
                    session.add(user)
                    await session.flush()
                return user
    
    async def set_user_ready(self, user_id: int, is_ready: bool = True):
        async with self.get_session() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                if user:
                    user.is_ready = is_ready
    
    async def create_game(self) -> Game:
        async with self.get_session() as session:
            async with session.begin():
                game = Game(is_active=True, current_round=0)
                session.add(game)
                await session.flush()
                return game
    
    async def get_active_game(self) -> Optional[Game]:
        async with self.get_session() as session:
            async with session.begin():
                result = await session.execute(
                    "SELECT * FROM games WHERE is_active = true LIMIT 1"
                )
                row = result.fetchone()
                if row:
                    return Game(id=row.id, is_active=row.is_active, current_round=row.current_round)
                return None
    
    async def create_round(self, game_id: int, round_number: int, question: str) -> Round:
        async with self.get_session() as session:
            async with session.begin():
                round_obj = Round(game_id=game_id, round_number=round_number, 
                                question=question, is_active=True)
                session.add(round_obj)
                await session.flush()
                return round_obj
    
    async def get_current_round(self, game_id: int) -> Optional[Round]:
        async with self.get_session() as session:
            async with session.begin():
                result = await session.execute("""
                    SELECT * FROM rounds 
                    WHERE game_id = :game_id AND is_active = true 
                    ORDER BY id DESC LIMIT 1
                """, {"game_id": game_id})
                row = result.fetchone()
                if row:
                    return Round(
                        id=row.id, game_id=row.game_id, round_number=row.round_number,
                        question=row.question, is_active=row.is_active,
                        hint1=row.hint1, hint2=row.hint2, hint3=row.hint3
                    )
                return None
    
    async def set_hint(self, round_id: int, hint_num: int, hint_text: str):
        async with self.get_session() as session:
            async with session.begin():
                column = f"hint{hint_num}"
                await session.execute(
                    f"UPDATE rounds SET {column} = :hint WHERE id = :round_id",
                    {"hint": hint_text, "round_id": round_id}
                )
    
    async def submit_answer(self, user_id: int, round_id: int, answer: str) -> PlayerAnswer:
        async with self.get_session() as session:
            async with session.begin():
                player_answer = PlayerAnswer(user_id=user_id, round_id=round_id, answer=answer)
                session.add(player_answer)
                await session.flush()
                return player_answer
    
    async def get_round_answers(self, round_id: int) -> List[PlayerAnswer]:
        async with self.get_session() as session:
            async with session.begin():
                result = await session.execute("""
                    SELECT pa.*, u.username, u.first_name 
                    FROM player_answers pa 
                    JOIN users u ON pa.user_id = u.id 
                    WHERE pa.round_id = :round_id 
                    ORDER BY u.first_name
                """, {"round_id": round_id})
                
                rows = result.fetchall()
                return [PlayerAnswer(
                    id=row.id, user_id=row.user_id, 
                    round_id=row.round_id, answer=row.answer
                ) for row in rows]
    
    async def set_round_winner(self, round_id: int, winner_id: Optional[int] = None):
        async with self.get_session() as session:
            async with session.begin():
                if winner_id:
                    await session.execute(
                        "UPDATE rounds SET winner_id = :winner_id, is_active = false WHERE id = :round_id",
                        {"winner_id": winner_id, "round_id": round_id}
                    )
                else:
                    await session.execute(
                        "UPDATE rounds SET is_active = false WHERE id = :round_id",
                        {"round_id": round_id}
                    )
    
    async def get_ready_players(self) -> List[User]:
        async with self.get_session() as session:
            async with session.begin():
                result = await session.execute("SELECT * FROM users WHERE is_ready = true")
                rows = result.fetchall()
                return [User(
                    id=row.id, username=row.username, first_name=row.first_name,
                    is_ready=row.is_ready, is_admin=row.is_admin
                ) for row in rows]
    
    async def reset_game_state(self):
        async with self.get_session() as session:
            async with session.begin():
                await session.execute("UPDATE users SET is_ready = false")
                await session.execute("UPDATE games SET is_active = false")
                await session.execute("UPDATE rounds SET is_active = false")
