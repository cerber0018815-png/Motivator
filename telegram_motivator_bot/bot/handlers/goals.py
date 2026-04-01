from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database import AsyncSessionLocal, User
from sqlalchemy import select

router = Router()

class GoalsStates(StatesGroup):
    waiting_goals = State()

@router.message(Command("set_goals"))
async def set_goals(message: types.Message, state: FSMContext):
    await state.set_state(GoalsStates.waiting_goals)
    await message.answer("Напиши свои цели (можно подробно). Я буду их учитывать в советах.")

@router.message(GoalsStates.waiting_goals)
async def save_goals(message: types.Message, state: FSMContext):
    goals_text = message.text
    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user:
            user.goals = goals_text
            await session.commit()
    await state.clear()
    await message.answer("Цели сохранены! Теперь я буду их учитывать. Если захочешь изменить, снова используй /set_goals.")