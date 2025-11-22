from typing import List, Dict, Optional
from database.models import User, Round, PlayerAnswer
from database.db import Database

class GameManager:
    def __init__(self, db: Database):
        self.db = db
        self.active_game: Optional[Dict] = None
    
    async def start_new_game(self) -> bool:
        """Начать новую игру"""
        # Сбрасываем старое состояние
        await self.db.reset_game_state()
        
        # Создаём новую игру
        game = await self.db.create_game()
        self.active_game = {"id": game.id, "current_round": 0}
        
        return True
    
    async def get_ready_players_count(self) -> int:
        """Получить количество готовых игроков"""
        players = await self.db.get_ready_players()
        return len(players)
    
    async def start_round(self, question: str) -> bool:
        """Начать новый раунд"""
        if not self.active_game:
            return False
        
        current_round = self.active_game["current_round"] + 1
        if current_round > 7:
            return False
        
        # Создаём раунд
        round_obj = await self.db.create_round(
            game_id=self.active_game["id"], 
            round_number=current_round, 
            question=question
        )
        
        self.active_game["current_round"] = current_round
        return True
    
    async def all_players_answered(self, round_id: int) -> bool:
        """Проверить, ответили ли все игроки"""
        # Получаем текущий раунд
        round_obj = await self.db.get_current_round(self.active_game["id"])
        if not round_obj or round_obj.id != round_id:
            return False
        
        # Считаем ответы
        cursor = await self.db.db.execute(
            "SELECT COUNT(*) FROM player_answers WHERE round_id = ?", (round_id,)
        )
        answer_count = (await cursor.fetchone())[0]
        
        # Считаем готовых игроков
        ready_count = await self.get_ready_players_count()
        
        return answer_count >= ready_count
    
    async def set_hint(self, round_id: int, hint_num: int, hint_text: str) -> bool:
        """Установить подсказку"""
        await self.db.set_hint(round_id, hint_num, hint_text)
        return True
    
    async def get_round_answers_formatted(self, round_id: int) -> List[Dict]:
        """Получить отформатированные ответы для админа"""
        answers = await self.db.get_round_answers(round_id)
        formatted_answers = []
        
        for answer in answers:
            formatted = {
                "id": answer.id,
                "user_id": answer.user_id,
                "answer": answer.answer,
                "username": f"Игрок_{answer.user_id}"  # Будет обновлено в handlers
            }
            formatted_answers.append(formatted)
        
        return formatted_answers
    
    async def select_winner(self, round_id: int, winner_id: Optional[int] = None) -> bool:
        """Выбрать победителя раунда"""
        if winner_id:
            await self.db.set_round_winner(round_id, winner_id)
        else:
            # Отмечаем раунд как завершённый без победителя
            await self.db.db.execute(
                "UPDATE rounds SET is_active = 0 WHERE id = ?", (round_id,)
            )
            await self.db.db.commit()
        
        return True
    
    async def is_game_completed(self) -> bool:
        """Проверить, завершена ли игра"""
        return self.active_game and self.active_game["current_round"] >= 7