import aiosqlite
import asyncio
from typing import List, Optional
from .models import User, Game, Round, PlayerAnswer
from config import DATABASE_URL

class Database:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.db = None
    
    async def __aenter__(self):
        self.db = await aiosqlite.connect(self.db_url)
        await self._create_tables()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()
    
    async def _create_tables(self):
        """Создаёт необходимые таблицы"""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_ready BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_active BOOLEAN DEFAULT 1,
                current_round INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                round_number INTEGER,
                question TEXT,
                is_active BOOLEAN DEFAULT 0,
                hint1 TEXT DEFAULT '',
                hint2 TEXT DEFAULT '',
                hint3 TEXT DEFAULT '',
                winner_id INTEGER,
                FOREIGN KEY (game_id) REFERENCES games (id)
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                round_id INTEGER,
                answer TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (round_id) REFERENCES rounds (id)
            )
        """)
        
        await self.db.commit()
    
    async def get_or_create_user(self, user_id: int, username: str, first_name: str) -> User:
        """Получить или создать пользователя"""
        cursor = await self.db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return User(id=row[0], username=row[1], first_name=row[2], 
                       is_ready=row[3], is_admin=row[4])
        
        await self.db.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await self.db.commit()
        
        return User(id=user_id, username=username, first_name=first_name)
    
    async def set_user_ready(self, user_id: int, is_ready: bool = True):
        """Установить готовность пользователя"""
        await self.db.execute(
            "UPDATE users SET is_ready = ? WHERE id = ?",
            (is_ready, user_id)
        )
        await self.db.commit()
    
    async def create_game(self) -> Game:
        """Создать новую игру"""
        cursor = await self.db.execute(
            "INSERT INTO games (is_active, current_round) VALUES (1, 0)",
            ()
        )
        game_id = cursor.lastrowid
        await self.db.commit()
        
        return Game(id=game_id, is_active=True, current_round=0)
    
    async def get_active_game(self) -> Optional[Game]:
        """Получить активную игру"""
        cursor = await self.db.execute(
            "SELECT * FROM games WHERE is_active = 1 LIMIT 1",
            ()
        )
        row = await cursor.fetchone()
        if row:
            return Game(id=row[0], is_active=row[1], current_round=row[2])
        return None
    
    async def create_round(self, game_id: int, round_number: int, question: str) -> Round:
        """Создать новый раунд"""
        cursor = await self.db.execute(
            "INSERT INTO rounds (game_id, round_number, question, is_active) VALUES (?, ?, ?, 1)",
            (game_id, round_number, question)
        )
        round_id = cursor.lastrowid
        await self.db.commit()
        
        return Round(id=round_id, game_id=game_id, round_number=round_number, 
                    question=question, is_active=True)
    
    async def get_current_round(self, game_id: int) -> Optional[Round]:
        """Получить текущий раунд игры"""
        cursor = await self.db.execute(
            "SELECT * FROM rounds WHERE game_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
            (game_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Round(
                id=row[0], game_id=row[1], round_number=row[2], question=row[3],
                is_active=row[4], hint1=row[5], hint2=row[6], hint3=row[7], winner_id=row[8]
            )
        return None
    
    async def set_hint(self, round_id: int, hint_num: int, hint_text: str):
        """Установить подсказку"""
        column = f"hint{hint_num}"
        await self.db.execute(
            f"UPDATE rounds SET {column} = ? WHERE id = ?",
            (hint_text, round_id)
        )
        await self.db.commit()
    
    async def submit_answer(self, user_id: int, round_id: int, answer: str) -> PlayerAnswer:
        """Принять ответ игрока"""
        cursor = await self.db.execute(
            "INSERT INTO player_answers (user_id, round_id, answer) VALUES (?, ?, ?)",
            (user_id, round_id, answer)
        )
        answer_id = cursor.lastrowid
        await self.db.commit()
        
        return PlayerAnswer(id=answer_id, user_id=user_id, round_id=round_id, answer=answer)
    
    async def get_round_answers(self, round_id: int) -> List[PlayerAnswer]:
        """Получить все ответы раунда"""
        cursor = await self.db.execute("""
            SELECT pa.*, u.username, u.first_name 
            FROM player_answers pa 
            JOIN users u ON pa.user_id = u.id 
            WHERE pa.round_id = ? 
            ORDER BY u.first_name
        """, (round_id,))
        
        rows = await cursor.fetchall()
        return [
            PlayerAnswer(id=row[0], user_id=row[1], round_id=row[2], answer=row[3])
            for row in rows
        ]
    
    async def set_round_winner(self, round_id: int, winner_id: int):
        """Установить победителя раунда"""
        await self.db.execute(
            "UPDATE rounds SET winner_id = ?, is_active = 0 WHERE id = ?",
            (winner_id, round_id)
        )
        await self.db.commit()
    
    async def get_ready_players(self) -> List[User]:
        """Получить готовых игроков"""
        cursor = await self.db.execute(
            "SELECT * FROM users WHERE is_ready = 1",
            ()
        )
        rows = await cursor.fetchall()
        return [
            User(id=row[0], username=row[1], first_name=row[2], 
                is_ready=row[3], is_admin=row[4])
            for row in rows
        ]
    
    async def reset_game_state(self):
        """Сбросить состояние игры (для новой игры)"""
        await self.db.execute("UPDATE users SET is_ready = 0")
        await self.db.execute("UPDATE games SET is_active = 0")
        await self.db.execute("UPDATE rounds SET is_active = 0")
        await self.db.commit()