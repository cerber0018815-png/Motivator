# main.py — точка входа, инициализация бота, планировщик

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz

from bot.config import TOKEN, DATABASE_URL
from bot.database import Database
from bot.deepseek_client import generate_morning_suggestions
from bot.keyboards import evening_menu_keyboard

bot = None

async def morning_job(bot_instance: Bot):
    from bot import handlers
    async with handlers.db.pool.acquire() as conn:
        users = await conn.fetch('SELECT id, telegram_id FROM users')
    for user in users:
        user_id = user['id']
        tg_id = user['telegram_id']
        goals = await handlers.db.get_active_goals(user_id)
        if not goals:
            continue
        today = datetime.now().date()
        existing = await handlers.db.get_morning_suggestion_for_day(user_id, today)
        if existing:
            continue
        entries = []
        for i in range(1, 4):
            day = today - timedelta(days=i)
            entries.extend(await handlers.db.get_journal_entries_for_day(user_id, day))
        try:
            suggestions = await generate_morning_suggestions(goals, entries)
        except Exception:
            suggestions = "🌱 Сегодня просто обрати внимание: что забирает силы, а что наполняет. Сделай одно маленькое дело для себя."
        await handlers.db.add_morning_suggestion(user_id, suggestions, today)
        # Передаём bot_instance в функцию
        await handlers.send_morning_message(bot_instance, tg_id, suggestions)

async def evening_job(bot_instance: Bot):
    """Вечерняя задача: напоминает подвести итог дня (если ещё не подводили)."""
    from bot import handlers
    async with handlers.db.pool.acquire() as conn:
        users = await conn.fetch('SELECT id, telegram_id FROM users')
    for user in users:
        tg_id = user['telegram_id']
        today = datetime.now().date()
        summary = await handlers.db.get_evening_summary_for_day(user['id'], today)
        if summary:
            continue
        await bot_instance.send_message(
            tg_id,
            "🌙 Вечернее время.\n\nТы можешь добавить ещё одну запись за сегодня или сразу подвести итог дня.\n\nЧто выберешь?",
            reply_markup=evening_menu_keyboard()
        )

async def main():
    global bot
    logging.basicConfig(level=logging.INFO)
    
    from bot import handlers
    db_instance = Database(DATABASE_URL)
    await db_instance.init()
    handlers.db = db_instance
    
    bot = Bot(token=TOKEN)
    
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(handlers.router)
    
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(morning_job, "cron", hour=8, minute=0, args=(bot,))
    scheduler.add_job(evening_job, "cron", hour=20, minute=0, args=(bot,))
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())