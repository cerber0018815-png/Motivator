from aiogram import Router, types
from aiogram.filters import Command
from bot.database import AsyncSessionLocal, User

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    async with AsyncSessionLocal() as session:
        # Проверяем, существует ли пользователь
        from sqlalchemy import select
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            session.add(user)
            await session.commit()

    await message.answer(
        "Привет! Я твой мягкий мотиватор. Я помогу тебе двигаться к твоим целям.\n\n"
        "Сначала расскажи, чего ты хочешь достичь? Напиши свои долгосрочные цели или просто опиши, что для тебя важно.\n"
        "Можешь использовать команду /set_goals, чтобы указать или изменить цели.\n"
        "Для статистики используй /stats."
    )