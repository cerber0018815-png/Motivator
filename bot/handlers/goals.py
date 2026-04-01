import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from bot.database import SessionLocal, User
from bot.keyboards import main_menu_keyboard

router = Router()

class GoalsStates(StatesGroup):
    waiting_goals = State()

def _set_goals(telegram_id, goals_text):
    session = SessionLocal()
    try:
        user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one()
        user.goals = goals_text
        session.commit()
    finally:
        session.close()

@router.message(Command("set_goals"))
async def set_goals(message: types.Message, state: FSMContext):
    await state.set_state(GoalsStates.waiting_goals)
    await message.answer("Напиши свои цели (можно подробно). Я буду их учитывать в советах.")

@router.message(GoalsStates.waiting_goals)
async def save_goals(message: types.Message, state: FSMContext):
    await asyncio.to_thread(_set_goals, message.from_user.id, message.text)
    await state.clear()
    await message.answer(
        "✅ Цели сохранены! Теперь я буду их учитывать в ежедневных советах.\n\n"
        "Ты всегда можешь изменить цели командой /set_goals или через меню.",
        reply_markup=main_menu_keyboard()
    )