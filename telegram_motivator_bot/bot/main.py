import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import settings
from bot.database import init_db
from bot.handlers import start, goals, messages, stats
from bot.services.scheduler import setup_scheduler
from bot.services.scheduler import bot as scheduler_bot

logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация БД
    await init_db()

    # Создание бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(goals.router)
    dp.include_router(messages.router)
    dp.include_router(stats.router)

    # Настройка планировщика (передаём бота)
    setup_scheduler(bot)

    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())