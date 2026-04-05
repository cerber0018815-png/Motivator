# handlers.py — все обработчики сообщений и колбэков

import asyncio
import logging
import pytz
from datetime import date, datetime, time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import ADMINS
from bot.database import Database
from bot.deepseek_client import extract_goals_from_conversation, generate_evening_analysis
from bot.keyboards import (
    start_goals_button, goal_session_buttons, goal_summary_buttons,
    confirm_entry_buttons, start_evening_summary_button, resetdb_confirm_buttons,
    menu_button, entry_added_keyboard, main_menu_keyboard, goals_menu_keyboard,
    goals_list_for_edit_keyboard, goals_list_for_delete_keyboard,
    confirm_change_keyboard, confirm_delete_keyboard,
    entries_menu_keyboard, entries_list_for_edit_keyboard, entries_list_for_delete_keyboard,
    confirm_change_entry_keyboard, confirm_delete_entry_keyboard,
    help_keyboard, cancel_add_keyboard, evening_menu_keyboard,
    dates_list_keyboard, summary_view_keyboard,
    morning_dream_buttons, cancel_dream_button, dream_saved_buttons,
    dreams_list_keyboard, dream_view_keyboard
)

router = Router()
db: Database = None
active_timers = {}

# --- Состояния FSM ---
class GoalSession(StatesGroup):
    active = State()

class Journal(StatesGroup):
    waiting_for_entry = State()

class AddingGoal(StatesGroup):
    waiting_for_goal = State()

class EditingGoal(StatesGroup):
    waiting_for_new_text = State()

class AddingEntry(StatesGroup):
    waiting_for_entry_text = State()

class EditingEntry(StatesGroup):
    waiting_for_new_text = State()

class DreamAnalysis(StatesGroup):
    waiting_for_dream = State()    


# --- Вспомогательная функция ---
async def send_with_menu(chat_id: int, text: str, reply_markup=None):
    from bot.main import bot
    if reply_markup is None:
        reply_markup = menu_button()
    await bot.send_message(chat_id, text, reply_markup=reply_markup)

async def send_morning_message(telegram_id: int, suggestions: str):
    """Отправляет утренние рекомендации и предложение записать сон."""
    from bot.main import bot
    await bot.send_message(telegram_id, suggestions)
    await bot.send_message(
        telegram_id,
        "🌙 *Если ты запомнил свой сон, можешь написать его, и я сделаю разбор.*\n"
        "(Разбор сна — это не научный подход, а просто интерпретация для размышлений.)",
        parse_mode="Markdown",
        reply_markup=morning_dream_buttons()
    )    


# ==================== ОСНОВНАЯ КОМАНДА /start ====================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    db_user_id = await db.add_user(
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    goals = await db.get_active_goals(db_user_id)
    if goals:
        await message.answer(
            "👋 С возвращением!\n"
            "Ты уже определил свои цели и желания. Продолжаем вести дневник.\n\n"
            "Чтобы записать событие или мысль в дневник, просто напиши текст и отправь.",
            reply_markup=menu_button()
        )
        await state.set_state(Journal.waiting_for_entry)
    else:
        welcome = (
            "🌱 *Привет! Я — твой бережный дневник-мотиватор.*\n\n"
            "Я помогаю медленно и без давления приближаться к тому, что для тебя по-настоящему важно.\n\n"
            "📌 *Что я умею:*\n"
            "• Помогаю определить твои истинные желания и цели\n"
            "• Каждое утро предлагаю 2–3 маленьких, комфортных шага к ним\n"
            "• Ты ведёшь дневник — записываешь любые события, мысли, наблюдения\n"
            "• Вечером мы вместе подводим итог дня: я даю тёплый разбор и вопросы для рефлексии\n"
            "• В любой момент можно изменить или дополнить цели и записи через меню\n\n"
            "🎯 *Первый шаг — определим твои цели и желания.*\n"
            "Это мини-сессия, которая займёт *15 минут*. За это время ты можешь просто описывать свою ситуацию, мечты, трудности, а я помогу сформулировать конкретные цели и желания.\n\n"
            "Пожалуйста, выдели 15 минут спокойного времени, когда тебя никто не отвлекает.\n\n"
            "Готов? Нажми на кнопку ниже, когда будешь готов начать."
        )
        await message.answer(welcome, parse_mode="Markdown", reply_markup=start_goals_button())


# ==================== СЕССИЯ ОПРЕДЕЛЕНИЯ ЦЕЛЕЙ ====================
@router.callback_query(F.data == "start_goals")
async def start_goal_session(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GoalSession.active)
    await state.update_data(temp_goals=[], conversation_history=[])
    timer_task = asyncio.create_task(goal_session_timeout(callback.from_user.id, state))
    active_timers[callback.from_user.id] = timer_task
    await callback.message.edit_text(
        "🧠 Давай определим твои цели и желания. У нас есть 15 минут.\n\n"
        "Ты можешь просто написать, что у тебя сейчас в жизни происходит, что тебя волнует, что хочется изменить. "
        "Я помогу выделить главное и сформулировать цели.\n\n"
        "Пиши в свободной форме. Я буду отвечать и задавать вопросы. "
        "Когда почувствуешь, что цели определены, нажми кнопку «Завершить».\n\n"
        "Время пошло. Таймер: 15:00",
        reply_markup=goal_session_buttons()
    )
    await callback.answer()

async def goal_session_timeout(telegram_id: int, state: FSMContext):
    await asyncio.sleep(900)
    current_state = await state.get_state()
    if current_state == GoalSession.active:
        data = await state.get_data()
        temp_goals = data.get("temp_goals", [])
        if temp_goals:
            goals_text = "\n".join(f"• {g}" for g in temp_goals)
            await state.update_data(temp_goals=[])
            user_id = await db.get_user_id(telegram_id)
            for goal in temp_goals:
                await db.add_goal(user_id, goal)
            await state.set_state(Journal.waiting_for_entry)
            from bot.main import bot
            await bot.send_message(telegram_id,
                f"⏰ Время опроса вышло. Мы успели наметить такие цели:\n\n{goals_text}\n\n"
                "Если захочешь изменить или добавить цели или желания, ты всегда можешь это сделать через меню.\n\n"
                "Я сохранил эти цели. Теперь мы будем вести дневник.\n\n"
                "Чтобы записать событие или мысль в дневник, просто напиши текст и отправь.",
                reply_markup=menu_button()
            )
        else:
            await state.set_state(Journal.waiting_for_entry)
            from bot.main import bot
            await bot.send_message(telegram_id,
                "⏰ Время опроса вышло, но мы не успели определить ни одной цели или желания. "
                "Ты всегда можешь начать заново через /start.",
                reply_markup=start_goals_button()
            )
    if telegram_id in active_timers:
        del active_timers[telegram_id]

@router.message(GoalSession.active, F.text)
async def goal_session_message(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_goals = data.get("temp_goals", [])
    conversation_history = data.get("conversation_history", [])
    conversation_history.append(message.text)
    if len(conversation_history) > 10:
        conversation_history = conversation_history[-10:]
    try:
        result = await extract_goals_from_conversation(conversation_history, temp_goals)
        new_goals = result['goals']
        reply_text = result['reply']
        await state.update_data(temp_goals=new_goals, conversation_history=conversation_history)
    except Exception as e:
        logging.exception("Goal extraction failed")
        reply_text = "Спасибо. Расскажи ещё, что для тебя важно."
    await message.answer(reply_text, reply_markup=goal_session_buttons())

@router.callback_query(F.data == "finish_goal_session")
async def finish_goal_session(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp_goals = data.get("temp_goals", [])
    if not temp_goals:
        await callback.message.edit_text(
            "Пока не определено ни одной цели или желания. Напиши что-нибудь о своих желаниях, и я помогу сформулировать.",
            reply_markup=goal_session_buttons()
        )
        await callback.answer()
        return
    goals_text = "\n".join(f"• {g}" for g in temp_goals)
    await callback.message.edit_text(
        f"Отлично! Вот какие цели и желания мы с тобой наметили:\n\n{goals_text}\n\n"
        "Всё верно? Ты можешь добавить ещё или подтвердить, и мы перейдём к дневнику.",
        reply_markup=goal_summary_buttons()
    )
    await callback.answer()

@router.callback_query(F.data == "add_more_goals")
async def add_more_goals(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Хорошо, продолжаем. Пиши, что ещё важно для тебя.\n\n"
        "Время сессии продолжается.",
        reply_markup=goal_session_buttons()
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_goals")
async def confirm_goals(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp_goals = data.get("temp_goals", [])
    if not temp_goals:
        await callback.message.edit_text("Нет целей для сохранения.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    db_user_id = await db.get_user_id(user_id)
    for goal in temp_goals:
        await db.add_goal(db_user_id, goal)
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "✨ Цели и желания сохранены. Ты всегда сможешь изменить их или добавить новые через меню.\n\n"
        "Теперь мы будем каждый день: записывать события, подводить вечерний итог, а утром я буду предлагать маленькие шаги.\n\n"
        "Чтобы записать событие или мысль в дневник, просто напиши текст и отправь.",
        reply_markup=menu_button()
    )
    await callback.answer()

@router.callback_query(F.data == "abort_goal_session")
async def abort_goal_session(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    await state.clear()
    await callback.message.edit_text(
        "Сессия прервана. Ты можешь начать определение целей и желаний позже через /start.",
        reply_markup=start_goals_button()
    )
    await callback.answer()


# ==================== УПРАВЛЕНИЕ ЦЕЛЯМИ ====================
@router.callback_query(F.data == "my_goals_menu")
async def my_goals_menu(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    if not goals_with_ids:
        await callback.message.edit_text(
            "У тебя пока нет ни одной цели или желания. Ты можешь добавить цель или желание с помощью кнопки ниже.",
            reply_markup=goals_menu_keyboard()
        )
    else:
        goals_text = "\n".join(f"• {goal_text}" for _, goal_text in goals_with_ids)
        await callback.message.edit_text(
            f"🎯 *Твои текущие цели:*\n\n{goals_text}\n\nЧто хочешь сделать?",
            parse_mode="Markdown",
            reply_markup=goals_menu_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "add_goal_start")
async def add_goal_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddingGoal.waiting_for_goal)
    await callback.message.edit_text(
        "➕ *Добавление цели*\n\nНапиши новую цель или желание. Это может быть что угодно, что для тебя сейчас важно.\n\n"
        "Ты можешь отправить сообщение с текстом, а я сохраню его как новую цель или желание.\n\n"
        "Если передумал, нажми кнопку «В начало».",
        parse_mode="Markdown",
        reply_markup=cancel_add_keyboard()
    )
    await callback.answer()

@router.message(AddingGoal.waiting_for_goal, F.text)
async def add_goal_receive(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    new_goal = message.text.strip()
    if not new_goal:
        await message.answer("Пожалуйста, напиши непустую цель или желание.")
        return
    user_id = await db.get_user_id(message.from_user.id)
    await db.add_new_goal(user_id, new_goal)
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await message.answer(
        f"✅ Цель/желание добавлено: «{new_goal}»\n\nТы можешь продолжать вести дневник или вернуться в меню.",
        reply_markup=menu_button()
    )

@router.callback_query(F.data == "edit_goal_list")
async def edit_goal_list(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    if not goals_with_ids:
        await callback.message.edit_text(
            "У тебя нет целей/желаний для изменения. Сначала добавь цель или желание через «Добавить цель».",
            reply_markup=goals_menu_keyboard()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "✏️ *Выбери цель/желание, которые хочешь изменить:*",
        parse_mode="Markdown",
        reply_markup=goals_list_for_edit_keyboard(goals_with_ids)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_goal_"))
async def edit_goal_selected(callback: CallbackQuery, state: FSMContext):
    goal_id = int(callback.data.split("_")[-1])
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    old_text = next((text for gid, text in goals_with_ids if gid == goal_id), None)
    if not old_text:
        await callback.message.edit_text("Цель/желание не найдено. Возвращаю в меню.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await state.set_state(EditingGoal.waiting_for_new_text)
    await state.update_data(goal_id=goal_id, old_text=old_text)
    await callback.message.edit_text(
        f"✏️ *Изменение цели/желания*\n\nСтарая цель/желание: «{old_text}»\n\nНапиши новый текст цели/желания:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(EditingGoal.waiting_for_new_text, F.text)
async def edit_goal_receive(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    new_text = message.text.strip()
    if not new_text:
        await message.answer("Пожалуйста, напиши непустой текст цели/желания.")
        return
    data = await state.get_data()
    goal_id = data['goal_id']
    old_text = data['old_text']
    await state.update_data(new_text=new_text)
    await message.answer(
        f"⚠️ *Подтверждение изменения*\n\nСтарая цель/желание: «{old_text}»\nНовая цель/желание: «{new_text}»\n\nВсё верно?",
        parse_mode="Markdown",
        reply_markup=confirm_change_keyboard(goal_id)
    )

@router.callback_query(F.data.startswith("confirm_edit_"))
async def edit_goal_confirm(callback: CallbackQuery, state: FSMContext):
    goal_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    new_text = data.get('new_text')
    if not new_text:
        await callback.message.edit_text("Ошибка: не найден новый текст. Попробуй снова.", reply_markup=menu_button())
        await state.clear()
        await callback.answer()
        return
    await db.update_goal(goal_id, new_text)
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        f"✅ Цель/желание успешно изменено.\n\nТеперь оно звучит: «{new_text}»",
        reply_markup=menu_button()
    )
    await callback.answer()

@router.callback_query(F.data == "delete_goal_list")
async def delete_goal_list(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    if not goals_with_ids:
        await callback.message.edit_text(
            "У тебя нет целей для удаления.",
            reply_markup=goals_menu_keyboard()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "🗑 *Выбери цель/желание, которые хочешь удалить:*",
        parse_mode="Markdown",
        reply_markup=goals_list_for_delete_keyboard(goals_with_ids)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_goal_"))
async def delete_goal_confirm_prompt(callback: CallbackQuery):
    goal_id = int(callback.data.split("_")[-1])
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    goal_text = next((text for gid, text in goals_with_ids if gid == goal_id), None)
    if not goal_text:
        await callback.message.edit_text("Цель/желание не найдено.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text(
        f"⚠️ *Подтверждение удаления*\n\nТы действительно хочешь удалить цель/желание: «{goal_text}»?\n\nЭто действие необратимо.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_keyboard(goal_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_goal_confirm(callback: CallbackQuery):
    goal_id = int(callback.data.split("_")[-1])
    await db.delete_goal(goal_id)
    await callback.message.edit_text(
        "✅ Цель удалена.\n\nТы можешь продолжить вести дневник.",
        reply_markup=menu_button()
    )
    await callback.answer()


# ==================== УПРАВЛЕНИЕ ЗАПИСЯМИ ДНЕВНИКА ====================
@router.callback_query(F.data == "my_entries_menu")
async def my_entries_menu(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    entries = await db.get_journal_entries_with_ids_for_day(user_id, today)
    if not entries:
        await callback.message.edit_text(
            "📭 У тебя пока нет записей за сегодня.\n\nТы можешь добавить запись с помощью кнопки ниже.",
            reply_markup=entries_menu_keyboard()
        )
    else:
        entries_text = "\n\n".join([f"📌 {e['content']}" for e in entries])
        await callback.message.edit_text(
            f"📝 *Твои записи за сегодня ({today.strftime('%d.%m.%Y')}):*\n\n{entries_text}\n\nЧто хочешь сделать?",
            parse_mode="Markdown",
            reply_markup=entries_menu_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "add_entry_start")
async def add_entry_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddingEntry.waiting_for_entry_text)
    await state.update_data(source="journal")
    await callback.message.edit_text(
        "➕ *Добавление записи*\n\nНапиши текст новой записи. Это может быть событие, мысль, наблюдение.\n\n"
        "Если передумал, нажми кнопку «В начало».",
        parse_mode="Markdown",
        reply_markup=cancel_add_keyboard()
    )
    await callback.answer()

@router.message(AddingEntry.waiting_for_entry_text, F.text)
async def add_entry_receive(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    content = message.text.strip()
    if not content:
        await message.answer("Пожалуйста, напиши непустую запись.")
        return
    user_id = await db.get_user_id(message.from_user.id)
    await db.add_journal_entry(user_id, content)
    data = await state.get_data()
    source = data.get("source", "journal")
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    if source == "evening":
        await message.answer(
            f"✅ Запись добавлена в дневник.\n\n«{content}»\n\nТы можешь добавить ещё или подвести итог дня.",
            reply_markup=evening_menu_keyboard()
        )
    else:
        await message.answer(
            f"✅ Запись добавлена в дневник.\n\n«{content}»",
            reply_markup=entry_added_keyboard()
        )

@router.callback_query(F.data == "edit_entry_list")
async def edit_entry_list(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    entries = await db.get_journal_entries_with_ids_for_day(user_id, today)
    if not entries:
        await callback.message.edit_text(
            "Нет записей за сегодня для изменения. Сначала добавь запись.",
            reply_markup=entries_menu_keyboard()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "✏️ *Выбери запись, которую хочешь изменить:*",
        parse_mode="Markdown",
        reply_markup=entries_list_for_edit_keyboard(entries)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_entry_"))
async def edit_entry_selected(callback: CallbackQuery, state: FSMContext):
    entry_id = int(callback.data.split("_")[-1])
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    entries = await db.get_journal_entries_with_ids_for_day(user_id, today)
    entry = next((e for e in entries if e['id'] == entry_id), None)
    if not entry:
        await callback.message.edit_text("Запись не найдена.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await state.set_state(EditingEntry.waiting_for_new_text)
    await state.update_data(entry_id=entry_id, old_text=entry['content'])
    await callback.message.edit_text(
        f"✏️ *Изменение записи*\n\nСтарый текст:\n«{entry['content']}»\n\nНапиши новый текст:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(EditingEntry.waiting_for_new_text, F.text)
async def edit_entry_receive(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    new_text = message.text.strip()
    if not new_text:
        await message.answer("Пожалуйста, напиши непустой текст.")
        return
    data = await state.get_data()
    entry_id = data['entry_id']
    old_text = data['old_text']
    await state.update_data(new_text=new_text)
    await message.answer(
        f"⚠️ *Подтверждение изменения*\n\nСтарый текст:\n«{old_text}»\n\nНовый текст:\n«{new_text}»\n\nВсё верно?",
        parse_mode="Markdown",
        reply_markup=confirm_change_entry_keyboard(entry_id)
    )

@router.callback_query(F.data.startswith("confirm_edit_entry_"))
async def edit_entry_confirm(callback: CallbackQuery, state: FSMContext):
    entry_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    new_text = data.get('new_text')
    if not new_text:
        await callback.message.edit_text("Ошибка: не найден новый текст.", reply_markup=menu_button())
        await state.clear()
        await callback.answer()
        return
    await db.update_journal_entry(entry_id, new_text)
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        f"✅ Запись успешно изменена.\n\nНовый текст:\n«{new_text}»",
        reply_markup=menu_button()
    )
    await callback.answer()

@router.callback_query(F.data == "delete_entry_list")
async def delete_entry_list(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    entries = await db.get_journal_entries_with_ids_for_day(user_id, today)
    if not entries:
        await callback.message.edit_text(
            "Нет записей за сегодня для удаления.",
            reply_markup=entries_menu_keyboard()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "🗑 *Выбери запись, которую хочешь удалить:*",
        parse_mode="Markdown",
        reply_markup=entries_list_for_delete_keyboard(entries)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_entry_"))
async def delete_entry_confirm_prompt(callback: CallbackQuery):
    entry_id = int(callback.data.split("_")[-1])
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    entries = await db.get_journal_entries_with_ids_for_day(user_id, today)
    entry = next((e for e in entries if e['id'] == entry_id), None)
    if not entry:
        await callback.message.edit_text("Запись не найдена.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text(
        f"⚠️ *Подтверждение удаления*\n\nТы действительно хочешь удалить эту запись?\n\n«{entry['content']}»\n\nЭто действие необратимо.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_entry_keyboard(entry_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_entry_"))
async def delete_entry_confirm(callback: CallbackQuery):
    entry_id = int(callback.data.split("_")[-1])
    await db.delete_journal_entry(entry_id)
    await callback.message.edit_text(
        "✅ Запись удалена.\n\nТы можешь продолжить вести дневник.",
        reply_markup=menu_button()
    )
    await callback.answer()


# ==================== ОСНОВНОЙ РЕЖИМ ДНЕВНИКА ====================
@router.message(Journal.waiting_for_entry, F.text)
async def handle_journal_entry(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    await state.update_data(pending_entry=message.text)
    await message.answer(
        "Записать это в дневник?",
        reply_markup=confirm_entry_buttons()
    )

@router.callback_query(F.data == "confirm_entry")
async def confirm_entry(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("pending_entry")
    if not text:
        await callback.message.edit_text("Нечего записывать. Напиши что-нибудь.", reply_markup=menu_button())
        await callback.answer()
        return
    user_id = await db.get_user_id(callback.from_user.id)
    await db.add_journal_entry(user_id, text)
    await callback.message.edit_text(
        f"✅ Запись добавлена в дневник.\n\n«{text}»",
        reply_markup=entry_added_keyboard()
    )
    await state.set_state(Journal.waiting_for_entry)
    await callback.answer()

@router.callback_query(F.data == "cancel_entry")
async def cancel_entry(callback: CallbackQuery, state: FSMContext):
    await state.update_data(pending_entry=None)
    await callback.message.edit_text("Запись отменена. Можешь написать что-то ещё.", reply_markup=menu_button())
    await state.set_state(Journal.waiting_for_entry)
    await callback.answer()


# ==================== ВЕЧЕРНИЙ ИТОГ ====================
@router.callback_query(F.data == "start_evening_summary")
async def start_evening_summary(callback: CallbackQuery):
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz)
    current_time = now.time()
    if current_time >= time(20, 0) or current_time < time(7, 0):
        user_id = await db.get_user_id(callback.from_user.id)
        today = now.date()
        existing = await db.get_evening_summary_for_day(user_id, today)
        if existing:
            await callback.message.edit_text(
                f"📜 *Итог за сегодня ({today.strftime('%d.%m.%Y')}) уже был подведён:*\n\n{existing}\n\n"
                "Ты можешь посмотреть итоги за другие дни через меню «Мои вечерние итоги».",
                parse_mode="Markdown",
                reply_markup=summary_view_keyboard()
            )
            await callback.answer()
            return

        entries = await db.get_journal_entries_for_day(user_id, today)
        goals = await db.get_active_goals(user_id)
        await callback.message.edit_text("🌙 Подвожу итог дня... Это займёт несколько секунд.")
        try:
            analysis = await generate_evening_analysis(entries, goals)
        except Exception as e:
            logging.exception("DeepSeek error")
            analysis = "Извини, не удалось сейчас сгенерировать анализ. Попробуй позже."
        await db.add_evening_summary(user_id, analysis, today)
        await callback.message.edit_text(analysis)
        await callback.message.answer(
            "Завтра утром я пришлю тебе несколько идей на день.\nХорошего вечера! 🌙",
            reply_markup=menu_button()
        )
    else:
        await callback.message.edit_text(
            "📅 Подвести итог дня можно только с 20:00 вечера до 7:00 утра.\n"
            "Сейчас уже утро. Давай начнём новый день? Напиши что-нибудь в дневник или дождись вечера.",
            reply_markup=menu_button()
        )
    await callback.answer()


# ==================== ПРОСМОТР ВЕЧЕРНИХ ИТОГОВ ЗА ПРОШЛЫЕ ДНИ ====================
@router.callback_query(F.data == "my_evening_summaries")
async def my_evening_summaries(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    dates = await db.get_all_evening_summary_dates(user_id)
    if not dates:
        await callback.message.edit_text(
            "У тебя пока нет сохранённых вечерних итогов. Подведи итог сегодняшнего дня после 20:00.",
            reply_markup=menu_button()
        )
    else:
        await callback.message.edit_text(
            "📜 *Выбери дату, чтобы посмотреть итог:*",
            parse_mode="Markdown",
            reply_markup=dates_list_keyboard(dates)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("show_summary_"))
async def show_summary(callback: CallbackQuery):
    date_str = callback.data.split("_")[-1]
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await callback.message.edit_text("Неверная дата.", reply_markup=menu_button())
        await callback.answer()
        return
    user_id = await db.get_user_id(callback.from_user.id)
    summary = await db.get_evening_summary_for_day(user_id, selected_date)
    if not summary:
        await callback.message.edit_text(
            f"Итог за {selected_date.strftime('%d.%m.%Y')} не найден.",
            reply_markup=menu_button()
        )
    else:
        await callback.message.edit_text(
            f"📜 *Итог за {selected_date.strftime('%d.%m.%Y')}:*\n\n{summary}",
            parse_mode="Markdown",
            reply_markup=summary_view_keyboard()
        )
    await callback.answer()


# ==================== ВЕЧЕРНЕЕ ДОБАВЛЕНИЕ ЗАПИСИ ====================
@router.callback_query(F.data == "evening_add_entry")
async def evening_add_entry_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddingEntry.waiting_for_entry_text)
    await state.update_data(source="evening")
    await callback.message.edit_text(
        "➕ *Добавление записи*\n\nНапиши текст новой записи. Это может быть событие, мысль, наблюдение.\n\n"
        "После сохранения ты сможешь сразу подвести итог дня.",
        parse_mode="Markdown",
        reply_markup=cancel_add_keyboard()
    )
    await callback.answer()


# ==================== ОТМЕНА ДОБАВЛЕНИЯ ====================
@router.callback_query(F.data == "cancel_add_back")
async def cancel_add_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    source = data.get("source", "journal")
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    if source == "evening":
        await callback.message.edit_text(
            "📝 Возврат в вечернее меню.\n\nТы можешь добавить запись или подвести итог дня.",
            reply_markup=evening_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "📝 *Дневник*\n\nЧтобы записать событие или мысль в дневник, просто напиши текст и отправь.",
            parse_mode="Markdown",
            reply_markup=menu_button()
        )
    await callback.answer()


# ==================== ГЛАВНОЕ МЕНЮ И СПРАВКА ====================
@router.callback_query(F.data == "show_main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 *Главное меню*\n\nВыбери нужное действие:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "help_menu")
async def show_help_menu(callback: CallbackQuery):
    help_text = (
        "📖 *Справка*\n\n"
        "Я — твой бережный дневник-мотиватор. Вот что я умею:\n\n"
        "📝 *Дневник*\n"
        "• Ты можешь в любой момент написать текст — это будет запись в дневнике.\n"
        "• Я спрошу, нужно ли её сохранить. После сохранения ты увидишь кнопки «Мои записи» и «В начало».\n"
        "• Все записи хранятся по дням.\n\n"
        "🌙 *Вечерний итог*\n"
        "• Каждый вечер в 20:00 я напоминаю подвести итог дня.\n"
        "• Ты можешь добавить запись перед итогом или сразу подвести итог.\n"
        "• Итог можно подвести только с 20:00 до 7:00 утра. Один раз за день.\n"
        "• Все итоги сохраняются, их можно просмотреть в разделе «Мои вечерние итоги».\n\n"
        "☀️ *Утренние советы*\n"
        "• Каждое утро в 8:00 я присылаю несколько маленьких, комфортных шагов к твоим целям.\n"
        "• Они основаны на твоих целях и недавних записях.\n"
        "• После советов я предлагаю записать сон — ты можешь получить его интерпретацию и сохранить в раздел «Мои сны».\n\n"
        "🎯 *Мои цели/желания*\n"
        "• Через меню ты можешь посмотреть все свои цели и желания, добавить новые, изменить или удалить.\n"
        "• Первые цели и желания определяются в 15-минутной сессии при первом запуске.\n\n"
        "📋 *Мои записи*\n"
        "• В меню ты можешь посмотреть все записи за сегодня.\n"
        "• Также можно добавить новую запись, изменить или удалить существующую.\n\n"
        "📜 *Мои вечерние итоги*\n"
        "• Просмотр всех сохранённых итогов за прошлые дни.\n\n"
        "💭 *Мои сны*\n"
        "• Просмотр всех сохранённых разборов снов по датам.\n"
        "• Можно удалить ненужную запись.\n\n"
        "🛠 *Другие команды*\n"
        "• /start — перезапустить бота (если нужно начать заново).\n"
        "• /resetdb — для администратора: полная очистка базы данных (необратимо).\n\n"
        "Я создан чтобы давать поддержку и задавать вопросы, чтобы ты лучше понимал(а) себя.\n"
        "Ты всегда можешь вернуться в дневник через кнопку «В начало»."
    )
    await callback.message.edit_text(help_text, parse_mode="Markdown", reply_markup=help_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_journal")
async def back_to_journal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "📝 *Дневник*\n\nЧтобы записать событие или мысль в дневник, просто напиши текст и отправь.",
        parse_mode="Markdown",
        reply_markup=menu_button()
    )
    await callback.answer()


# ==================== АДМИНИСТРАТИВНАЯ КОМАНДА /resetdb ====================
@router.message(Command("resetdb"))
async def resetdb_command(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    await message.answer(
        "⚠️ *ВНИМАНИЕ!* ⚠️\n\nВы собираетесь полностью очистить базу данных.\n"
        "Будут удалены все пользователи, цели, записи дневника, утренние советы и вечерние итоги.\n"
        "Это действие необратимо.\n\nВы уверены?",
        parse_mode="Markdown",
        reply_markup=resetdb_confirm_buttons()
    )

@router.callback_query(F.data == "confirm_resetdb")
async def confirm_resetdb(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет прав", show_alert=True)
        return
    async with db.pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE users, goals, journal_entries, evening_summaries, morning_suggestions CASCADE")
        await conn.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE goals_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE journal_entries_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE evening_summaries_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE morning_suggestions_id_seq RESTART WITH 1")
    await callback.message.edit_text(
        "✅ База данных полностью очищена.\nВсе пользователи, цели и записи удалены.\nБот готов к новому старту."
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_resetdb")
async def cancel_resetdb(callback: CallbackQuery):
    await callback.message.edit_text("❌ Очистка отменена.")
    await callback.answer()


# ==================== АНАЛИЗ СНОВ ====================
@router.callback_query(F.data == "dream_analysis_start")
async def dream_analysis_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DreamAnalysis.waiting_for_dream)
    await callback.message.edit_text(
        "💭 *Расскажи свой сон одним сообщением.*\n\n"
        "Опиши всё, что запомнил: образы, эмоции, события.",
        parse_mode="Markdown",
        reply_markup=cancel_dream_button()
    )
    await callback.answer()

@router.callback_query(F.data == "skip_dream")
async def skip_dream(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "📝 *Дневник*\n\nЗаписать событие в дневник: просто напиши текст и отправь.",
        parse_mode="Markdown",
        reply_markup=menu_button()
    )
    await callback.answer()

@router.message(DreamAnalysis.waiting_for_dream, F.text)
async def receive_dream(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    dream_text = message.text.strip()
    if not dream_text:
        await message.answer("Пожалуйста, напиши свой сон (не пустое сообщение).", reply_markup=cancel_dream_button())
        return
    await message.answer("🔮 Разбираю сон... Это займёт несколько секунд.")
    try:
        analysis = await analyze_dream(dream_text)
    except Exception as e:
        logging.exception("Dream analysis error")
        analysis = "Извини, не удалось сейчас разобрать сон. Попробуй позже."
    await state.update_data(dream_text=dream_text, analysis=analysis)
    await message.answer(
        f"💭 *Твой сон:*\n{dream_text}\n\n🔮 *Разбор:*\n{analysis}",
        parse_mode="Markdown",
        reply_markup=dream_saved_buttons()
    )

async def analyze_dream(dream_text: str) -> str:
    """Запрос к DeepSeek для разбора сна."""
    from bot.deepseek_client import _call_deepseek
    user_prompt = f"Разбери сон (не научный подход, а мягкая интерпретация для размышлений):\n{dream_text}"
    return await _call_deepseek(user_prompt)

@router.callback_query(F.data == "save_dream_only")
async def save_dream_only(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dream_text = data.get('dream_text')
    analysis = data.get('analysis')
    if not dream_text or not analysis:
        await callback.message.edit_text("Ошибка: не найден сон или разбор.", reply_markup=menu_button())
        await state.clear()
        await callback.answer()
        return
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
    await db.add_dream_analysis(user_id, dream_text, analysis, today)
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "✅ Разбор сна сохранён в раздел «Мои сны».\n\n"
        "Ты можешь продолжить вести дневник.",
        reply_markup=menu_button()
    )
    await callback.answer()

# ==================== ПРОСМОТР СНОВ ====================
@router.callback_query(F.data == "my_dreams")
async def my_dreams(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    dates = await db.get_dream_analyses_dates(user_id)
    if not dates:
        await callback.message.edit_text(
            "У тебя пока нет сохранённых снов. Запиши сон утром после рекомендаций.",
            reply_markup=menu_button()
        )
    else:
        await callback.message.edit_text(
            "💭 *Выбери дату, чтобы посмотреть сон и его разбор:*",
            parse_mode="Markdown",
            reply_markup=dreams_list_keyboard(dates)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("show_dream_"))
async def show_dream(callback: CallbackQuery):
    date_str = callback.data.split("_")[-1]
    try:
        dream_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await callback.message.edit_text("Неверная дата.", reply_markup=menu_button())
        await callback.answer()
        return
    user_id = await db.get_user_id(callback.from_user.id)
    dream_data = await db.get_dream_analysis_by_date(user_id, dream_date)
    if not dream_data:
        await callback.message.edit_text(f"Сон за {dream_date.strftime('%d.%m.%Y')} не найден.", reply_markup=menu_button())
    else:
        text = f"💭 *Сон за {dream_date.strftime('%d.%m.%Y')}:*\n\n{dream_data['dream_text']}\n\n🔮 *Разбор:*\n{dream_data['analysis_text']}"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=dream_view_keyboard(dream_date)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_dream_"))
async def delete_dream(callback: CallbackQuery):
    date_str = callback.data.split("_")[-1]
    try:
        dream_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await callback.message.edit_text("Неверная дата.", reply_markup=menu_button())
        await callback.answer()
        return
    user_id = await db.get_user_id(callback.from_user.id)
    await db.delete_dream_analysis(user_id, dream_date)
    await callback.message.edit_text(
        f"✅ Сон за {dream_date.strftime('%d.%m.%Y')} удалён.",
        reply_markup=menu_button()
    )
    await callback.answer()


# ==================== ЗАГЛУШКА ДЛЯ /change_goal ====================
@router.message(Command("change_goal"))
async def change_goal(message: Message):
    await message.answer(
        "Изменить цели можно через меню (кнопка «Меню» → «Мои цели» → «Изменить цель»)."
    )