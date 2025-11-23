import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID
from handlers import common, admin, player
from database.db import Database

logging.basicConfig(level=logging.INFO)

async def main():
    print("Запускаем бота...")
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем базу
    db = Database()
    await db.__aenter__()
    print("Подключено к PostgreSQL ✅")
    
    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(player.router)
    
    # Передаём db в хендлеры (если нужно — можно через Middleware, но пока так)
    for router in [common, admin, player]:
        if hasattr(router, 'router'):
            router.router['db'] = db
    
    print(f"Bot Stock & Know запущен!")
    print(f"Админ ID: {ADMIN_ID}")
    
    await dp.start_polling(bot, db=db)

if __name__ == "__main__":
    asyncio.run(main())
