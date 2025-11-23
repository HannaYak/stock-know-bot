from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class User:
    id: int
    username: Optional[str]
    first_name: str
    is_ready: bool = False
    is_admin: bool = False

@dataclass
class Game:
    id: int
    is_active: bool = True
    current_round: int = 0
    created_at: datetime = datetime.now()

@dataclass
class Round:
    id: int
    game_id: int
    round_number: int
    question: str = ""
    is_active: bool = False
    hint1: str = ""
    hint2: str = ""
    hint3: str = ""
    winner_id: Optional[int] = None

@dataclass
class PlayerAnswer:
    id: int
    user_id: int
    round_id: int
    answer: str
    submitted_at: datetime = datetime.now()

@dataclass
class Question:
    id: int
    question: str
    answer: str
    hint1: str
    hint2: str
    hint3: str
