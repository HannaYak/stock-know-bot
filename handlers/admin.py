from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
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
from aiogram.filters import StateFilter

router = Router()

class AdminStates(StatesGroup):
    waiting_hint1 = State()
    waiting_hint2 = State()
    waiting_hint3 = State()
    waiting_questions_file = State()

@router.message(Command("admin"))
async def admin_panel(message: Message, db: Database):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Доступ запрещён. Только для админа.")
        return
    keyboard = get_admin_start_keyboard()
    await message.answer(
        "🎮 **Панель администратора Stock & Know**\n\n"
        "Нажмите кнопку для запуска игры:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_start_game")
async def start_new_game(callback: CallbackQuery, state: FSMContext, db: Database):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещён.")
        return
    game_manager = GameManager(db)
    
    if await game_manager.start_new_game():
        players_count = await game_manager.get_ready_players_count()
        
        await callback.message.edit_text(
            ADMIN_GAME_STARTED.format(count=players_count),
            parse_mode="Markdown"
        )
        
        # Загружаем вопрос из базы для первого раунда
        questions = await db.get_questions(1)
        if questions:
            question = questions[0].question
            await game_manager.start_round(question)
            await send_question_to_players(callback.bot, db, game_manager, question)
        
        await state.set_state(AdminStates.waiting_hint1)
        
    else:
        await callback.answer("Ошибка при запуске игры")

# Команда загрузки вопросов
@router.message(Command("loadquestions"))
async def cmd_load_questions(message: Message, db: Database):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "Пришли мне файл questions.json с вопросами\n"
        "(можно просто переслать как документ)"
    )
    await AdminStates.waiting_questions_file.set()

@router.message(AdminStates.waiting_questions_file, F.document)
async def receive_questions_file(message: Message, db: Database, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not message.document.file_name.endswith(".json"):
        await message.answer("Пожалуйста, пришли файл с расширением .json")
        return
    
    await message.answer("Файл получен! Загружаю вопросы в базу...")
    
    # Скачиваем файл
    file = await message.bot.download(message.document)
    
    # Загружаем в базу
    count = await db.load_questions_from_file(file.name)
    
    await message.answer(f"Готово! Загружено {count} вопросов в базу.\nТеперь можно начинать игру!")
    await state.clear()

# Остальные хендлеры (подсказки, ответы, победитель) — как в твоём текущем коде
@router.callback_query(F.data.startswith("admin_hint"), F.from_user.id == ADMIN_ID)
async def admin_set_hint(callback: CallbackQuery, state: FSMContext, db: Database):
    _, hint_type, round_id = callback.data.split("_")
    
    hint_num = int(hint_type[-1])  # 1, 2 или 3
    
    if hint_num == 1:
        await state.set_state(AdminStates.waiting_hint1)
    elif hint_num == 2:
        await state.set_state(AdminStates.waiting_hint2)
    elif hint_num == 3:
        await state.set_state(AdminStates.waiting_hint3)
    
    await callback.message.edit_text(
        f"💡 **Подсказка {hint_num}/3**\n\n"
        f"Напишите текст подсказки для раунда {round_id}:",
        parse_mode="Markdown"
    )

@router.message(StateFilter(AdminStates.waiting_hint1, AdminStates.waiting_hint2, AdminStates.waiting_hint3), F.from_user.id == ADMIN_ID)
async def receive_admin_hint(message: Message, state: FSMContext, db: Database, bot: Bot):
    state_data = await state.get_data()
    round_id = state_data.get("current_round_id", 1)
    current_state = await state.get_state()
    
    if not round_id:
        await message.answer("Ошибка: ID раунда не найден")
        await state.clear()
        return
    
    if current_state == AdminStates.waiting_hint1.state:
        hint_num = 1
    elif current_state == AdminStates.waiting_hint2.state:
        hint_num = 2
    else:
        hint_num = 3
    
    await db.set_hint(round_id, hint_num, message.text)
    
    ready_players = await db.get_ready_players()
    for player in ready_players:
        try:
            await bot.send_message(
                player.id,
                f"💡 **Подсказка {hint_num}/3**\n\n{message.text}",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await message.answer(f"✅ Подсказка {hint_num} отправлена!")
    
    if hint_num < 3:
        next_state = getattr(AdminStates, f"waiting_hint{hint_num+1}")
        await state.set_state(next_state)
    else:
        await state.clear()

# ... (остальные хендлеры для показа ответов, выбора победителя, следующего раунда — они уже в твоём коде, добавь их, если нужно)
