import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID
from database.db import Database
from handlers import common, admin, player
from utils.game_logic import GameManager

db = Database()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Инициализация БД
    await db.__aenter__()
        # Регистрируем обработчики
        dp.include_router(common.router)
        dp.include_router(admin.router)
        dp.include_router(player.router)
        
        # Передаём зависимости
        for router in [common.router, admin.router, player.router]:
            for handler in router.handlers:
                if hasattr(handler, 'callback'):
                    handler.callback.bot = bot
                    handler.callback.db = db
        
        # Запуск бота
        print("🤖 Бот Stock & Know запущен!")
        print(f"👑 Админ ID: {ADMIN_ID}")
        
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
