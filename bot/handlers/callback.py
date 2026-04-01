from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from bot.handlers.goals import GoalsStates
from bot.services.statistics import get_weekly_stats
import asyncio

router = Router()

@router.callback_query(lambda c: c.data == "set_goals")
async def callback_set_goals(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Установить цели'"""
    await callback.answer()
    await state.set_state(GoalsStates.waiting_goals)
    await callback.message.answer(
        "Напиши свои цели (можно подробно). Я буду их учитывать в советах.\n"
        "Например: «Хочу выучить английский до уровня B2 за полгода» или «Стать более продуктивным в работе»."
    )

@router.callback_query(lambda c: c.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    """Обработчик кнопки 'Статистика'"""
    await callback.answer()
    stats = await asyncio.to_thread(get_weekly_stats, callback.from_user.id)
    await callback.message.answer(stats, parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "help")
async def callback_help(callback: types.CallbackQuery):
    """Обработчик кнопки 'Помощь'"""
    await callback.answer()
    help_text = (
        "🆘 *Помощь*\n\n"
        "• /start – начать работу (показывает это меню).\n"
        "• /set_goals – установить или изменить свои цели.\n"
        "• /stats – посмотреть статистику за последнюю неделю.\n\n"
        "📅 *Расписание:*\n"
        "• Утром (8:00 UTC) я присылаю варианты дел на день.\n"
        "• Вечером (20:00 UTC) спрашиваю, как прошёл день.\n\n"
        "💬 *Общение:*\n"
        "Просто пиши мне в любое время – я отвечу, дам совет или просто поддержу.\n\n"
        "⚠️ *Важно:* Я не заменяю профессионального психолога. Если ты испытываешь серьёзные трудности, обратись к специалисту."
    )
    await callback.message.answer(help_text, parse_mode="Markdown")