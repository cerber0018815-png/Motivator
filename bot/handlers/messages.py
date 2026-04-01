from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.database import AsyncSessionLocal, User, Message, DailyEntry
from bot.services.deepseek import get_deepseek_response, build_system_message
from bot.utils.helpers import get_user_context
from bot.states import ReportStates
import datetime

router = Router()

@router.message()
async def handle_message(message: types.Message, state: FSMContext):
    user_text = message.text
    telegram_id = message.from_user.id

    # Проверяем состояние FSM: если ожидаем вечерний отчёт
    current_state = await state.get_state()
    if current_state == ReportStates.waiting_evening.state:
        await process_evening_report(message, state, user_text)
        return

    # Обычная обработка
    async with AsyncSessionLocal() as session:
        # Получаем пользователя
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            await message.answer("Пожалуйста, сначала введите /start")
            return

        # Сохраняем сообщение пользователя
        user_msg = Message(user_id=user.id, role='user', text=user_text)
        session.add(user_msg)
        await session.commit()

        # Получаем контекст
        context = await get_user_context(session, user.id)

        # Формируем системный промпт и отправляем в DeepSeek
        system_content = build_system_message(context)
        messages_for_api = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_text}
        ]
        bot_reply = await get_deepseek_response(messages_for_api)

        # Сохраняем ответ
        bot_msg = Message(user_id=user.id, role='assistant', text=bot_reply)
        session.add(bot_msg)
        await session.commit()

    await message.answer(bot_reply)

async def process_evening_report(message: types.Message, state: FSMContext, report_text: str):
    """Обрабатывает вечерний отчёт, сохраняет в БД и даёт обратную связь."""
    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            await message.answer("Ошибка.")
            await state.clear()
            return

        today = datetime.datetime.utcnow().date()
        stmt = select(DailyEntry).where(DailyEntry.user_id == user.id, DailyEntry.date == today)
        entry = (await session.execute(stmt)).scalar_one_or_none()
        if not entry:
            entry = DailyEntry(user_id=user.id, date=today)
            session.add(entry)

        entry.evening_report = report_text
        # Простой парсинг для извлечения rating и действий
        # Здесь можно попросить DeepSeek распарсить, но для простоты сохраним целиком
        # В реальности лучше вызвать отдельный парсинг
        await session.commit()

        # Получаем контекст и генерируем анализ
        context = await get_user_context(session, user.id)
        analysis = await generate_evening_analysis(user.telegram_id, context, report_text)

        # Сохраняем анализ как сообщение ассистента
        bot_msg = Message(user_id=user.id, role='assistant', text=analysis)
        session.add(bot_msg)
        await session.commit()

    await state.clear()
    await message.answer(analysis)