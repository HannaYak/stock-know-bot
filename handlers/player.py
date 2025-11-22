from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.messages import (
    PLAYER_QUESTION_MESSAGE, PLAYER_ANSWER_ACCEPTED, 
    PLAYER_HINT_MESSAGE, PLAYER_WINNER_ANNOUNCEMENT, PLAYER_GAME_END
)
from database.db import Database
from utils.game_logic import GameManager

router = Router()

class PlayerGameStates(StatesGroup):
    waiting_answer = State()
    waiting_hints = State()

@router.message(StateFilter(PlayerGameStates.waiting_answer))
async def receive_player_answer(message: Message, state: FSMContext, db: Database):
    """Получить ответ игрока"""
    # Сохраняем ответ в состоянии для передачи в БД
    await state.update_data(answer=message.text)
    
    # Удаляем сообщение игрока через 2 секунды
    asyncio.create_task(delete_message_after_delay(message, 2))
    
    # Сохраняем в БД
    data = await state.get_data()
    current_round_id = data.get("current_round_id")
    
    if current_round_id:
        answer_obj = await db.submit_answer(
            user_id=message.from_user.id,
            round_id=current_round_id,
            answer=message.text
        )
        
        await message.answer(
            PLAYER_ANSWER_ACCEPTED,
            parse_mode="Markdown"
        )
        
        # Проверяем, все ли ответили
        game_manager = GameManager(db)
        if await game_manager.all_players_answered(current_round_id):
            # Уведомляем админа
            admin_message = await bot.send_message(
                ADMIN_ID,
                "📝 **Все ответы получены!**\n\nТеперь доступно управление раундом.",
                parse_mode="Markdown"
            )
    
    await state.set_state(PlayerGameStates.waiting_hints)

async def delete_message_after_delay(message, delay: int):
    """Удалить сообщение через указанное время"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

@router.message(StateFilter(PlayerGameStates.waiting_hints))
async def ignore_messages_during_hints(message: Message):
    """Игнорируем сообщения во время подсказок"""
    pass

@router.callback_query(F.data.startswith("hint_"))
async def show_hint_to_player(callback: CallbackQuery, state: FSMContext, db: Database):
    """Показать подсказку игроку"""
    _, hint_num, round_id = callback.data.split("_")
    hint_num = int(hint_num)
    
    # Получаем подсказку из БД
    cursor = await db.db.execute(
        f"SELECT hint{hint_num} FROM rounds WHERE id = ?", (round_id,)
    )
    row = await cursor.fetchone()
    
    if row and row[0]:
        await callback.message.edit_text(
            PLAYER_HINT_MESSAGE.format(
                hint_num=hint_num,
                hint_text=row[0]
            ),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Подсказка ещё не задана ведущим")