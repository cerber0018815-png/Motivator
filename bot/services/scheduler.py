from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from aiogram import Bot
from sqlalchemy import select
from bot.database import AsyncSessionLocal, User, DailyEntry
from bot.services.deepseek import generate_morning_suggestions, generate_evening_analysis
from bot.utils.helpers import get_user_context

scheduler = AsyncIOScheduler()
bot: Bot = None

def setup_scheduler(bot_instance: Bot):
    global bot
    bot = bot_instance
    # Ежедневные задачи: утро и вечер
    scheduler.add_job(morning_job, CronTrigger(hour=8, minute=0))   # UTC 08:00
    scheduler.add_job(evening_job, CronTrigger(hour=20, minute=0))  # UTC 20:00
    scheduler.start()

async def morning_job():
    async with AsyncSessionLocal() as session:
        # Получаем всех пользователей
        users = await session.execute(select(User))
        users = users.scalars().all()
        for user in users:
            try:
                # Получаем контекст
                context = await get_user_context(session, user.id)
                # Генерируем утренние предложения
                suggestions = await generate_morning_suggestions(user.telegram_id, context)
                # Сохраняем в daily_entries (сегодня)
                today = datetime.utcnow().date()
                stmt = select(DailyEntry).where(DailyEntry.user_id == user.id, DailyEntry.date == today)
                entry = (await session.execute(stmt)).scalar_one_or_none()
                if not entry:
                    entry = DailyEntry(user_id=user.id, date=today)
                    session.add(entry)
                entry.morning_suggestions = suggestions
                await session.commit()
                # Отправляем пользователю
                await bot.send_message(user.telegram_id,
                                       f"🌅 Доброе утро!\n\n{suggestions}\n\nКак настроение? (напиши кратко)")
            except Exception as e:
                print(f"Error in morning_job for {user.telegram_id}: {e}")

async def evening_job():
    async with AsyncSessionLocal() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()
        for user in users:
            try:
                await bot.send_message(user.telegram_id,
                                       "🌙 Вечер. Расскажи, как прошёл твой день?\n- Что удалось сделать?\n- С какими трудностями столкнулся?\n- Как оцениваешь день от 1 до 10?")
                # Здесь можно установить состояние FSM, но для простоты мы будем обрабатывать ответы в messages.py
            except Exception as e:
                print(f"Error in evening_job for {user.telegram_id}: {e}")