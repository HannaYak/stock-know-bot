from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import GAME_RULES
from keyboards.player_kb import get_player_start_keyboard
from database.db import Database
from database.models import User

router = Router()

class PlayerStates(StatesGroup):
    waiting_for_ready = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    """Обработка команды /start"""
    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "Без имени"
    )
    
    if user.is_admin:
        await message.answer(
            "👋 Добро пожаловать, администратор!\n"
            "Используйте /admin для управления игрой.",
            reply_markup=get_player_start_keyboard()
        )
    else:
        await message.answer(
            GAME_RULES + "\n\nНажмите кнопку ниже, чтобы подтвердить готовность!",
            reply_markup=get_player_start_keyboard(),
            parse_mode="Markdown"
        )
    
    await state.set_state(PlayerStates.waiting_for_ready)

@router.message(F.text == "✅ Я готов играть!")
async def player_ready(message: Message, state: FSMContext, db: Database):
    """Игрок готов к игре"""
    await db.set_user_ready(message.from_user.id, True)
    
    await message.answer(
        "✅ Отлично! Вы готовы к игре.\n"
        "Ожидайте начала первого раунда от ведущего.",
        reply_markup=None  # Убираем клавиатуру
    )
    
    await state.clear()