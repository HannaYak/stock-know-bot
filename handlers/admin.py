from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID
from keyboards.admin_kb import (
    get_admin_start_keyboard, get_round_control_keyboard, 
    get_next_round_keyboard, get_winner_selection_keyboard
)
from utils.messages import (
    ADMIN_GAME_STARTED, ADMIN_ALL_ANSWERED, ADMIN_ROUND_COMPLETED, ADMIN_NO_WINNER
)
from utils.game_logic import GameManager
from database.db import Database
import asyncio

router = Router()

class AdminStates(StatesGroup):
    waiting_question = State()
    waiting_hint1 = State()
    waiting_hint2 = State()
    waiting_hint3 = State()

@router.message(F.from_user.id == ADMIN_ID, F.text == "/admin")
async def admin_panel(message: Message, state: FSMContext):
    """Панель администратора"""
    keyboard = get_admin_start_keyboard()
    await message.answer(
        "🎮 **Панель администратора Stock & Know**\n\n"
        "Нажмите кнопку для запуска игры:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_start_game", F.from_user.id == ADMIN_ID)
async def start_new_game(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    """Начать новую игру"""
    game_manager = GameManager(db)
    
    if await game_manager.start_new_game():
        players_count = await game_manager.get_ready_players_count()
        
        await callback.message.edit_text(
            ADMIN_GAME_STARTED.format(count=players_count),
            parse_mode="Markdown"
        )
        
        # Отправляем вопрос всем игрокам
        await state.set_state(AdminStates.waiting_question)
        await send_question_to_players(bot, db, game_manager)
        
        # Ждём ответы
        await wait_for_all_answers(bot, db, game_manager)
        
    else:
        await callback.answer("Ошибка при запуске игры")

async def send_question_to_players(bot: Bot, db: Database, game_manager: GameManager):
    """Отправить вопрос всем игрокам"""
    # Здесь будет логика отправки вопроса
    # Для примера используем заглушку
    question = "Сколько километров от Земли до Луны?"
    
    # Создаём раунд
    if game_manager.active_game:
        round_obj = await db.create_round(
            game_id=game_manager.active_game["id"],
            round_number=game_manager.active_game["current_round"],
            question=question
        )
        
        # Отправляем вопрос всем готовым игрокам
        ready_players = await db.get_ready_players()
        
        for player in ready_players:
            try:
                await bot.send_message(
                    player.id,
                    PLAYER_QUESTION_MESSAGE.format(
                        round_num=game_manager.active_game["current_round"],
                        question=question
                    ),
                    parse_mode="Markdown"
                )
                
                # Устанавливаем состояние ожидания ответа
                # Это делается через FSM или глобальное состояние
            except Exception as e:
                print(f"Не удалось отправить вопрос игроку {player.id}: {e}")

@router.callback_query(F.data.startswith("admin_hint"), F.from_user.id == ADMIN_ID)
async def admin_set_hint(callback: CallbackQuery, state: FSMContext, db: Database):
    """Админ устанавливает подсказку"""
    _, hint_type, round_id = callback.data.split("_")
    
    hint_num = int(hint_type[-1])  # 1, 2 или 3
    
    if hint_num == 1:
        await state.set_state(AdminStates.waiting_hint1)
        state_data = await state.get_data()
        state_data["current_round_id"] = int(round_id)
        await state.set_data(state_data)
    elif hint_num == 2:
        await state.set_state(AdminStates.waiting_hint2)
    elif hint_num == 3:
        await state.set_state(AdminStates.waiting_hint3)
    
    await callback.message.edit_text(
        f"💡 **Подсказка {hint_num}/3**\n\n"
        f"Напишите текст подсказки для раунда {round_id}:",
        parse_mode="Markdown"
    )

@router.message(StateFilter(AdminStates.waiting_hint1 | AdminStates.waiting_hint2 | AdminStates.waiting_hint3), 
                F.from_user.id == ADMIN_ID)
async def receive_admin_hint(message: Message, state: FSMContext, db: Database, bot: Bot):
    """Получить подсказку от админа"""
    state_data = await state.get_data()
    round_id = state_data.get("current_round_id")
    current_state = await state.get_state()
    
    if not round_id:
        await message.answer("Ошибка: ID раунда не найден")
        await state.clear()
        return
    
    # Определяем номер подсказки
    if current_state == AdminStates.waiting_hint1.state:
        hint_num = 1
    elif current_state == AdminStates.waiting_hint2.state:
        hint_num = 2
    else:
        hint_num = 3
    
    # Сохраняем подсказку
    await db.set_hint(round_id, hint_num, message.text)
    
    # Отправляем подсказку всем игрокам
    ready_players = await db.get_ready_players()
    for player in ready_players:
        try:
            await bot.send_message(
                player.id,
                PLAYER_HINT_MESSAGE.format(
                    hint_num=hint_num,
                    hint_text=message.text
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Не удалось отправить подсказку игроку {player.id}: {e}")
    
    # Обновляем клавиатуру админа
    keyboard = get_round_control_keyboard(round_id)
    await message.answer(
        f"✅ Подсказка {hint_num} отправлена всем игрокам!",
        reply_markup=keyboard
    )
    
    # Переходим к следующему состоянию
    if hint_num < 3:
        next_state = getattr(AdminStates, f"waiting_hint{hint_num+1}")
        await state.set_state(next_state)
    else:
        await state.clear()

@router.callback_query(F.data.startswith("admin_show_answers"), F.from_user.id == ADMIN_ID)
async def show_answers_to_admin(callback: CallbackQuery, db: Database):
    """Показать ответы админу"""
    _, _, round_id = callback.data.split("_")
    round_id = int(round_id)
    
    game_manager = GameManager(db)
    answers = await game_manager.get_round_answers_formatted(round_id)
    
    if not answers:
        await callback.answer("Ответов пока нет")
        return
    
    # Форматируем сообщение с ответами
    answers_text = "📝 **Ответы игроков:**\n\n"
    for i, answer in enumerate(answers, 1):
        answers_text += f"{i}. {answer['username']}: {answer['answer']}\n"
    
    keyboard = get_winner_selection_keyboard(answers)
    
    await callback.message.edit_text(
        f"{answers_text}\n**Выберите победителя:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_select_winner"), F.from_user.id == ADMIN_ID)
async def select_winner(callback: CallbackQuery, db: Database, bot: Bot):
    """Выбрать победителя"""
    _, _, answer_id = callback.data.split("_")
    answer_id = int(answer_id)
    
    # Получаем данные победителя
    cursor = await db.db.execute("""
        SELECT pa.user_id, pa.answer, u.username, u.first_name 
        FROM player_answers pa 
        JOIN users u ON pa.user_id = u.id 
        WHERE pa.id = ?
    """, (answer_id,))
    
    row = await cursor.fetchone()
    if not row:
        await callback.answer("Ошибка: ответ не найден")
        return
    
    winner_id, answer, username, first_name = row
    
    # Определяем номер раунда
    cursor = await db.db.execute(
        "SELECT round_number FROM rounds r JOIN player_answers pa ON r.id = pa.round_id WHERE pa.id = ?",
        (answer_id,)
    )
    round_num = (await cursor.fetchone())[0]
    
    # Устанавливаем победителя
    await db.set_round_winner(round_id=await get_round_id_by_answer(answer_id), winner_id=winner_id)
    
    # Объявляем всем
    ready_players = await db.get_ready_players()
    for player in ready_players:
        try:
            winner_mention = username or first_name
            await bot.send_message(
                player.id,
                PLAYER_WINNER_ANNOUNCEMENT.format(
                    round_num=round_num,
                    username=winner_mention
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Не удалось отправить объявление игроку {player.id}: {e}")
    
    # Показываем админу результат
    keyboard = get_next_round_keyboard(round_num)
    await callback.message.edit_text(
        ADMIN_ROUND_COMPLETED.format(
            round_num=round_num,
            username=username or first_name
        ),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_no_winner", F.from_user.id == ADMIN_ID)
async def no_winner_selected(callback: CallbackQuery, db: Database):
    """Без победителя"""
    # Получаем текущий раунд
    cursor = await db.db.execute(
        "SELECT round_number FROM rounds WHERE is_active = 1 LIMIT 1"
    )
    row = await cursor.fetchone()
    
    if row:
        round_num = row[0]
        await db.db.execute("UPDATE rounds SET is_active = 0 WHERE is_active = 1")
        await db.db.commit()
        
        keyboard = get_next_round_keyboard(round_num)
        await callback.message.edit_text(
            f"{ADMIN_NO_WINNER}\n\nРаунд {round_num} завершён.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("admin_next_round"), F.from_user.id == ADMIN_ID)
async def start_next_round(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    """Начать следующий раунд"""
    _, _, round_num = callback.data.split("_")
    round_num = int(round_num)
    
    if round_num > 7:
        # Игра завершена
        ready_players = await db.get_ready_players()
        for player in ready_players:
            try:
                await bot.send_message(player.id, PLAYER_GAME_END, parse_mode="Markdown")
            except:
                pass
        
        await callback.message.edit_text(
            "🏁 **Игра завершена!**\n\n"
            "Все 7 раундов пройдены.\n"
            "Спасибо за организацию игры!",
            parse_mode="Markdown"
        )
        return
    
    # Отправляем следующий вопрос
    await state.set_state(AdminStates.waiting_question)
    await send_question_to_players(bot, db, GameManager(db))
    
    await callback.answer(f"Раунд {round_num} начат!")

async def wait_for_all_answers(bot: Bot, db: Database, game_manager: GameManager):
    """Ждать ответы всех игроков"""
    # Проверяем каждые 10 секунд
    while True:
        await asyncio.sleep(10)
        
        current_round = await db.get_current_round(game_manager.active_game["id"])
        if current_round and await game_manager.all_players_answered(current_round.id):
            # Все ответили!
            await bot.send_message(
                ADMIN_ID,
                ADMIN_ALL_ANSWERED,
                parse_mode="Markdown"
            )
            
            # Показываем кнопки управления
            keyboard = get_round_control_keyboard(current_round.id)
            await bot.send_message(
                ADMIN_ID,
                "🎮 **Управление раундом**",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            break

async def get_round_id_by_answer(answer_id: int, db: Database) -> int:
    """Получить ID раунда по ID ответа"""
    cursor = await db.db.execute(
        "SELECT round_id FROM player_answers WHERE id = ?", (answer_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0
