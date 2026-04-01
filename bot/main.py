import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import settings
from bot.database import init_db
from bot.handlers import start, goals, messages, stats, callback
from bot.services.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(goals.router)
    dp.include_router(messages.router)
    dp.include_router(stats.router)
    dp.include_router(callback.router)

    setup_scheduler(bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())