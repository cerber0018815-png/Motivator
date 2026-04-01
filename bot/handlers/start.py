import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from bot.database import SessionLocal, User

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
    await message.answer(
        "Привет! Я твой мягкий мотиватор. Я помогу тебе двигаться к твоим целям.\n\n"
        "Сначала расскажи, чего ты хочешь достичь? Напиши свои долгосрочные цели или просто опиши, что для тебя важно.\n"
        "Можешь использовать команду /set_goals, чтобы указать или изменить цели.\n"
        "Для статистики используй /stats."
    )