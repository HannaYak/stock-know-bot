from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_player_start_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для игрока в начале"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Я готов играть!")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard