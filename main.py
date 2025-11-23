import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from handlers import common, admin, player
from database.db import Database

logging.basicConfig(level=logging.INFO)

# Глобальная переменная с базой (самый простой и надёжный способ)
db = None

async def main():
    global db
    
    print("Запускаем бота...")
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаемся к базе
    db = Database()
    await db.__aenter__()
    print("Подключено к PostgreSQL ✅")
    
    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(player.router)
    
    # Вшиваем базу в каждый роутер через dependency (aiogram 3.x так любит)
    common.router.message.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    common.router.callback_query.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    admin.router.message.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    admin.router.callback_query.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    player.router.message.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    player.router.callback_query.outer_middleware()(lambda handler, event, data: data.update(db=db) or handler(event, data))
    
    print("Bot Stock & Know запущен!")
    print(f"Админ ID: {ADMIN_ID}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
