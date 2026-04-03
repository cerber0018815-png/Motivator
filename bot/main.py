# main.py — точка входа, инициализация бота, планировщик

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz

from config import TOKEN, DATABASE_URL
from database import Database
from handlers import router, db as handlers_db
from deepseek_client import generate_morning_suggestions
from keyboards import start_evening_summary_button

bot = None

async def morning_job(bot_instance: Bot):
    async with handlers_db.pool.acquire() as conn:
        users = await conn.fetch('SELECT id, telegram_id FROM users')
    for user in users:
        user_id = user['id']
        tg_id = user['telegram_id']
        goals = await handlers_db.get_active_goals(user_id)
        if not goals:
            continue
        today = datetime.now().date()
        existing = await handlers_db.get_morning_suggestion_for_day(user_id, today)
        if existing:
            continue
        entries = []
        for i in range(1, 4):
            day = today - timedelta(days=i)
            entries.extend(await handlers_db.get_journal_entries_for_day(user_id, day))
        try:
            suggestions = await generate_morning_suggestions(goals, entries)
        except Exception:
            suggestions = "🌱 Сегодня просто обрати внимание: что забирает силы, а что наполняет. Сделай одно маленькое дело для себя."
        await handlers_db.add_morning_suggestion(user_id, suggestions, today)
        await bot_instance.send_message(tg_id, suggestions)

async def evening_job(bot_instance: Bot):
    async with handlers_db.pool.acquire() as conn:
        users = await conn.fetch('SELECT id, telegram_id FROM users')
    for user in users:
        tg_id = user['telegram_id']
        today = datetime.now().date()
        summary = await handlers_db.get_evening_summary_for_day(user['id'], today)
        if summary:
            continue
        await bot_instance.send_message(
            tg_id,
            "🌙 Как прошёл твой день?\nНажми на кнопку, чтобы подвести итог.",
            reply_markup=start_evening_summary_button()
        )

async def main():
    global bot
    logging.basicConfig(level=logging.INFO)
    global handlers_db
    handlers_db = Database(DATABASE_URL)
    await handlers_db.init()
    import handlers
    handlers.db = handlers_db
    bot = Bot(token=TOKEN)
    handlers.bot = bot
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(morning_job, "cron", hour=8, minute=0, args=(bot,))
    scheduler.add_job(evening_job, "cron", hour=20, minute=0, args=(bot,))
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())