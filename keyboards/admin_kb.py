from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

def get_admin_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для админа в начале"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Начать игру (7 раундов)", callback_data="admin_start_game")]
    ])
    return keyboard

def get_round_control_keyboard(round_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления раундом"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 Подсказка 1", callback_data=f"admin_hint1_{round_id}"),
            InlineKeyboardButton(text="💡 Подсказка 2", callback_data=f"admin_hint2_{round_id}")
        ],
        [
            InlineKeyboardButton(text="💡 Подсказка 3", callback_data=f"admin_hint3_{round_id}"),
            InlineKeyboardButton(text="📝 Показать ответы", callback_data=f"admin_show_answers_{round_id}")
        ],
        [InlineKeyboardButton(text="⏭️ Пропустить раунд", callback_data=f"admin_skip_round_{round_id}")]
    ])
    return keyboard

def get_next_round_keyboard(game_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после раунда"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"▶️ Начать раунд {game_id + 1}/7", 
                callback_data=f"admin_next_round_{game_id}"
            )
        ],
        [InlineKeyboardButton(text="🏁 Завершить игру", callback_data="admin_end_game")]
    ])
    return keyboard

def get_winner_selection_keyboard(answers: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора победителя"""
    inline_keyboard = []
    
    for answer in answers:
        username = answer.get('username', f"Игрок {answer['user_id']}")
        callback_data = f"admin_select_winner_{answer['id']}"
        button = InlineKeyboardButton(
            text=f"👑 {username}: {answer['answer']}", 
            callback_data=callback_data
        )
        inline_keyboard.append([button])
    
    inline_keyboard.append([InlineKeyboardButton(text="❌ Без победителя", callback_data="admin_no_winner")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)