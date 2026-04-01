from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from aiogram import Bot
from sqlalchemy import select
from bot.database import SessionLocal, User, DailyEntry
from bot.services.deepseek import generate_morning_suggestions, generate_evening_analysis
from bot.utils.helpers import get_user_context
import asyncio

scheduler = AsyncIOScheduler()
bot: Bot = None

def setup_scheduler(bot_instance: Bot):
    global bot
    bot = bot_instance
    scheduler.add_job(morning_job, CronTrigger(hour=8, minute=0))
    scheduler.add_job(evening_job, CronTrigger(hour=20, minute=0))
    scheduler.start()

async def morning_job():
    # Получаем всех пользователей (синхронно)
    def _get_all_users():
        session = SessionLocal()
        try:
            return session.execute(select(User)).scalars().all()
        finally:
            session.close()
    users = await asyncio.to_thread(_get_all_users)

    for user in users:
        try:
            # Получаем контекст
            context = await asyncio.to_thread(get_user_context, user.id)

            # Генерируем утренние предложения
            suggestions = await generate_morning_suggestions(user.telegram_id, context)

            # Сохраняем в daily_entries (синхронно)
            def _save_morning_suggestions(user_id, suggestions_text):
                session = SessionLocal()
                try:
                    today = datetime.utcnow().date()
                    entry = session.execute(
                        select(DailyEntry).where(DailyEntry.user_id == user_id, DailyEntry.date == today)
                    ).scalar_one_or_none()
                    if not entry:
                        entry = DailyEntry(user_id=user_id, date=today)
                        session.add(entry)
                    entry.morning_suggestions = suggestions_text
                    session.commit()
                finally:
                    session.close()
            await asyncio.to_thread(_save_morning_suggestions, user.id, suggestions)

            # Отправляем сообщение
            await bot.send_message(
                user.telegram_id,
                f"🌅 Доброе утро!\n\n{suggestions}\n\nКак настроение? (напиши кратко)"
            )
        except Exception as e:
            print(f"Error in morning_job for {user.telegram_id}: {e}")

async def evening_job():
    def _get_all_users():
        session = SessionLocal()
        try:
            return session.execute(select(User)).scalars().all()
        finally:
            session.close()
    users = await asyncio.to_thread(_get_all_users)

    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "🌙 Вечер. Расскажи, как прошёл твой день?\n- Что удалось сделать?\n- С какими трудностями столкнулся?\n- Как оцениваешь день от 1 до 10?"
            )
        except Exception as e:
            print(f"Error in evening_job for {user.telegram_id}: {e}")