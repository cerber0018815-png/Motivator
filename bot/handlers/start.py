import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from bot.database import SessionLocal, User
from bot.keyboards import main_menu_keyboard

router = Router()

def _get_or_create_user(telegram_id, username, full_name):
    session = SessionLocal()
    try:
        user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            session.add(user)
            session.commit()
        return user
    finally:
        session.close()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await asyncio.to_thread(
        _get_or_create_user,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    text = (
        "🌟 *Привет! Я твой мягкий мотиватор и психологический помощник.*\n\n"
        "Я здесь, чтобы поддерживать тебя на пути к твоим целям. "
        "Мы будем общаться каждый день, я буду давать мягкие советы, помогать анализировать прогресс и корректировать планы.\n\n"
        "📌 *Как это работает:*\n"
        "• Ты рассказываешь мне о своих долгосрочных целях (команда /set_goals или кнопка ниже).\n"
        "• Каждое утро я буду присылать тебе 2–3 варианта действий на день.\n"
        "• Вечером я спрошу, как прошёл день, и помогу проанализировать успехи и трудности.\n"
        "• В любой момент ты можешь просто написать мне – я поддержу и посоветую.\n\n"
        "✨ *Твои данные надёжно хранятся, я помню всю историю, чтобы советы были максимально полезными.*\n\n"
        "С чего начнём? Выбери действие:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())