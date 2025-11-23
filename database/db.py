import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, select, update, Sequence
from sqlalchemy.sql import func
from config import DATABASE_URL

Base = declarative_base()

# === МОДЕЛИ ===
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    is_ready = Column(Boolean, default=False)

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=True)
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

# НОВАЯ ТАБЛИЦА ДЛЯ ВОПРОСОВ — РАБОТАЕТ В POSTGRESQL
class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, server_default=Sequence('questions_id_seq').next_value())
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    hint1 = Column(Text)
    hint2 = Column(Text)
    hint3 = Column(Text)

class Database:
        def __init__(self):
            db_url = DATABASE_URL
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        self.engine = create_async_engine(db_url, echo=False, future=True)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def __aenter__(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()

    # === МЕТОДЫ ===
    async def get_or_create_user(self, user_id: int, username: str | None, first_name: str):
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(id=user_id, username=username, first_name=first_name)
                session.add(user)
                await session.commit()
            return user

    async def set_user_ready(self, user_id: int, ready: bool = True):
        async with self.session_factory() as session:
            await session.execute(update(User).where(User.id == user_id).values(is_ready=ready))
            await session.commit()

    async def create_game(self):
        async with self.session_factory() as session:
            game = Game(is_active=True)
            session.add(game)
            await session.commit()
            await session.refresh(game)
            return game.id

    async def get_active_game(self):
        async with self.session_factory() as session:
            result = await session.execute(select(Game).where(Game.is_active == True))
            return result.scalar_one_or_none()

    async def create_round(self, game_id: int, round_number: int, question: str):
        async with self.session_factory() as session:
            rnd = Round(game_id=game_id, round_number=round_number, question=question, is_active=True)
            session.add(rnd)
            await session.commit()
            await session.refresh(rnd)
            return rnd

    async def get_current_round(self, game_id: int):
        async with self.session_factory() as session:
            result = await session.execute(select(Round).where(Round.game_id == game_id, Round.is_active == True))
            return result.scalar_one_or_none()

    async def set_hint(self, round_id: int, hint_num: int, text: str):
        async with self.session_factory() as session:
            await session.execute(update(Round).where(Round.id == round_id).values(**{f"hint{hint_num}": text}))
            await session.commit()

    async def submit_answer(self, user_id: int, round_id: int, answer: str):
        async with self.session_factory() as session:
            ans = PlayerAnswer(user_id=user_id, round_id=round_id, answer=answer)
            session.add(ans)
            await session.commit()

    async def get_round_answers(self, round_id: int):
        async with self.session_factory() as session:
            result = await session.execute(
                select(PlayerAnswer.answer, User.first_name)
                .join(User)
                .where(PlayerAnswer.round_id == round_id)
            )
            return result.all()

    async def set_round_winner(self, round_id: int, winner_id: int | None = None):
        async with self.session_factory() as session:
            await session.execute(update(Round).where(Round.id == round_id).values(is_active=False, winner_id=winner_id))
            await session.commit()

    async def get_ready_players(self):
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.is_ready == True))
            return result.scalars().all()

    async def reset_game_state(self):
        async with self.session_factory() as session:
            await session.execute(update(Round).where(Round.is_active == True).values(is_active=False))
            await session.execute(update(Game).where(Game.is_active == True).values(is_active=False))
            await session.execute(update(User).values(is_ready=False))
            await session.execute("DELETE FROM player_answers")
            await session.commit()

    # Загрузка вопросов из JSON
    async def load_questions(self, questions_list):
        async with self.session_factory() as session:
            for q in questions_list:
                question = Question(
                    question=q["question"],
                    answer=q["answer"],
                    hint1=q["hints"][0],
                    hint2=q["hints"][1],
                    hint3=q["hints"][2]
                )
                session.add(question)
            await session.commit()

    async def get_random_questions(self, count=7):
        async with self.session_factory() as session:
            result = await session.execute(select(Question).order_by(func.random()).limit(count))
            return result.scalars().all()
