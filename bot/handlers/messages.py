import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.database import SessionLocal, User, Message, DailyEntry
from bot.services.deepseek import get_deepseek_response, build_system_message
from bot.utils.helpers import get_user_context
from bot.states import ReportStates
from datetime import datetime

router = Router()

# ---------- Синхронные функции для работы с БД ----------
def _save_user_message(telegram_id, text):
    session = SessionLocal()
    try:
        user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one()
        msg = Message(user_id=user.id, role='user', text=text)
        session.add(msg)
        session.commit()
        return user.id
    finally:
        session.close()

def _save_bot_message(user_id, text):
    session = SessionLocal()
    try:
        msg = Message(user_id=user_id, role='assistant', text=text)
        session.add(msg)
        session.commit()
    finally:
        session.close()

def _save_evening_report(user_id, report_text):
    session = SessionLocal()
    try:
        today = datetime.utcnow().date()
        entry = session.execute(
            select(DailyEntry).where(DailyEntry.user_id == user_id, DailyEntry.date == today)
        ).scalar_one_or_none()
        if not entry:
            entry = DailyEntry(user_id=user_id, date=today)
            session.add(entry)
        entry.evening_report = report_text
        session.commit()
    finally:
        session.close()

def _get_user_id(telegram_id):
    session = SessionLocal()
    try:
        user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one()
        return user.id
    finally:
        session.close()

# --------------------------------------------------------

@router.message()
async def handle_message(message: types.Message, state: FSMContext):
    user_text = message.text
    telegram_id = message.from_user.id

    current_state = await state.get_state()
    if current_state == ReportStates.waiting_evening.state:
        await process_evening_report(message, state, user_text)
        return

    # 1. Сохраняем сообщение пользователя
    user_id = await asyncio.to_thread(_save_user_message, telegram_id, user_text)

    # 2. Получаем контекст
    context = await asyncio.to_thread(get_user_context, user_id)
    if not context:
        await message.answer("Произошла ошибка. Попробуйте позже.")
        return

    # 3. Формируем промпт и вызываем DeepSeek
    system_content = build_system_message(context)
    messages_for_api = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_text}
    ]
    bot_reply = await get_deepseek_response(messages_for_api)

    # 4. Сохраняем ответ бота
    await asyncio.to_thread(_save_bot_message, user_id, bot_reply)

    # 5. Отправляем ответ пользователю
    await message.answer(bot_reply)

async def process_evening_report(message: types.Message, state: FSMContext, report_text: str):
    telegram_id = message.from_user.id

    # Получаем user_id
    user_id = await asyncio.to_thread(_get_user_id, telegram_id)

    # Сохраняем отчёт
    await asyncio.to_thread(_save_evening_report, user_id, report_text)

    # Получаем контекст для анализа
    context = await asyncio.to_thread(get_user_context, user_id)

    # Генерируем анализ через DeepSeek
    system_content = build_system_message(context)
    messages_for_api = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Вот мой вечерний отчёт: {report_text}\n\nПожалуйста, дай обратную связь, помоги проанализировать день и предложи, что можно сделать завтра, если нужно."}
    ]
    analysis = await get_deepseek_response(messages_for_api)

    # Сохраняем анализ как сообщение ассистента
    await asyncio.to_thread(_save_bot_message, user_id, analysis)

    await state.clear()
    await message.answer(analysis)