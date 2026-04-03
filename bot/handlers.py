# handlers.py — все обработчики сообщений и колбэков

import asyncio
import logging
from datetime import date
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
    journal_help_button, help_back_button, confirm_entry_buttons,
    start_evening_summary_button, resetdb_confirm_buttons,
    menu_button, main_menu_keyboard, goals_menu_keyboard,
    goals_list_for_edit_keyboard, goals_list_for_delete_keyboard,
    confirm_change_keyboard, confirm_delete_keyboard
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
    # в data будут goal_id, old_text, new_text

# --- Вспомогательная функция для отправки сообщений с меню (опционально) ---
async def send_with_menu(chat_id: int, text: str, reply_markup=None):
    from main import bot
    if reply_markup is None:
        reply_markup = menu_button()
    await bot.send_message(chat_id, text, reply_markup=reply_markup)

# --- Обработчик команды /start ---
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
            "Ты уже определил свои цели. Продолжаем вести дневник.\n\n"
            "Записать событие в дневник: просто напиши текст и отправь.",
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
            "• Раз в неделю (скоро) будет мини-сессия с более глубоким разбором\n"
            "• В любой момент можно изменить или дополнить цели\n\n"
            "🎯 *Первый шаг — определим твои цели.*\n"
            "Это мини-сессия, которая займёт *15 минут*. За это время ты можешь просто описывать свою ситуацию, мечты, трудности, а я помогу сформулировать конкретные цели.\n\n"
            "Пожалуйста, выдели 15 минут спокойного времени, когда тебя никто не отвлекает.\n\n"
            "Готов? Нажми на кнопку ниже, когда будешь готов начать."
        )
        await message.answer(welcome, parse_mode="Markdown", reply_markup=start_goals_button())

# --- Запуск сессии целей ---
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
            from main import bot
            await bot.send_message(telegram_id,
                f"⏰ Время опроса вышло. Мы успели наметить такие цели:\n\n{goals_text}\n\n"
                "Если захочешь изменить или добавить цели, ты всегда можешь это сделать через меню.\n\n"
                "Я сохранил эти цели. Теперь мы будем вести дневник.\n\n"
                "Записать событие в дневник: просто напиши текст и отправь.",
                reply_markup=menu_button()
            )
        else:
            await state.set_state(Journal.waiting_for_entry)
            from main import bot
            await bot.send_message(telegram_id,
                "⏰ Время опроса вышло, но мы не успели определить ни одной цели. "
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
            "Пока не определено ни одной цели. Напиши что-нибудь о своих желаниях, и я помогу сформулировать.",
            reply_markup=goal_session_buttons()
        )
        await callback.answer()
        return
    goals_text = "\n".join(f"• {g}" for g in temp_goals)
    await callback.message.edit_text(
        f"Отлично! Вот какие цели мы с тобой наметили:\n\n{goals_text}\n\n"
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
        "✨ Цели сохранены. Ты всегда сможешь изменить их или добавить новые через меню.\n\n"
        "Теперь мы будем каждый день: записывать события, подводить вечерний итог, а утром я буду предлагать маленькие шаги.\n\n"
        "Записать событие в дневник: просто напиши текст и отправь.",
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
        "Сессия прервана. Ты можешь начать определение целей позже через /start.",
        reply_markup=start_goals_button()
    )
    await callback.answer()

# --- Глобальное меню и управление целями ---
@router.callback_query(F.data == "show_main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 *Главное меню*\n\nВыбери нужное действие:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "my_goals_menu")
async def my_goals_menu(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    if not goals_with_ids:
        await callback.message.edit_text(
            "У тебя пока нет ни одной цели. Ты можешь добавить цель с помощью кнопки ниже.",
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
        "Ты можешь отправить сообщение с текстом, а я сохраню его как новую цель.",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddingGoal.waiting_for_goal, F.text)
async def add_goal_receive(message: Message, state: FSMContext):
    new_goal = message.text.strip()
    if not new_goal:
        await message.answer("Пожалуйста, напиши непустую цель.")
        return
    user_id = await db.get_user_id(message.from_user.id)
    await db.add_new_goal(user_id, new_goal)
    await state.clear()
    await state.set_state(Journal.waiting_for_entry)
    await message.answer(
        f"✅ Цель добавлена: «{new_goal}»\n\nТы можешь продолжать вести дневник или вернуться в меню.",
        reply_markup=menu_button()
    )

@router.callback_query(F.data == "edit_goal_list")
async def edit_goal_list(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    goals_with_ids = await db.get_all_active_goals_with_ids(user_id)
    if not goals_with_ids:
        await callback.message.edit_text(
            "У тебя нет целей для изменения. Сначала добавь цель через «Добавить цель».",
            reply_markup=goals_menu_keyboard()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "✏️ *Выбери цель, которую хочешь изменить:*",
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
        await callback.message.edit_text("Цель не найдена. Возвращаю в меню.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await state.set_state(EditingGoal.waiting_for_new_text)
    await state.update_data(goal_id=goal_id, old_text=old_text)
    await callback.message.edit_text(
        f"✏️ *Изменение цели*\n\nСтарая цель: «{old_text}»\n\nНапиши новый текст цели:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(EditingGoal.waiting_for_new_text, F.text)
async def edit_goal_receive(message: Message, state: FSMContext):
    new_text = message.text.strip()
    if not new_text:
        await message.answer("Пожалуйста, напиши непустой текст цели.")
        return
    data = await state.get_data()
    goal_id = data['goal_id']
    old_text = data['old_text']
    await state.update_data(new_text=new_text)
    await message.answer(
        f"⚠️ *Подтверждение изменения*\n\nСтарая цель: «{old_text}»\nНовая цель: «{new_text}»\n\nВсё верно?",
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
        f"✅ Цель успешно изменена.\n\nТеперь она звучит: «{new_text}»",
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
        "🗑 *Выбери цель, которую хочешь удалить:*",
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
        await callback.message.edit_text("Цель не найдена.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text(
        f"⚠️ *Подтверждение удаления*\n\nТы действительно хочешь удалить цель: «{goal_text}»?\n\nЭто действие необратимо.",
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

@router.callback_query(F.data == "back_to_journal")
async def back_to_journal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "📝 *Дневник*\n\nЗаписать событие в дневник: просто напиши текст и отправь.\n"
        "Если появятся вопросы, нажми «Справка».",
        parse_mode="Markdown",
        reply_markup=journal_help_button()
    )
    await callback.answer()

# --- Справка ---
@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    help_text = (
        "📖 *Справка*\n\n"
        "• *Дневник*: просто напиши что угодно — мысли, события, наблюдения. Я спрошу, записать ли это.\n"
        "• *Утренние советы*: каждое утро я присылаю 2–3 маленьких шага.\n"
        "• *Вечерний итог*: вечером я предложу подвести итог дня и дам тёплый разбор.\n"
        "• *Мои цели*: в меню ты можешь просмотреть, добавить, изменить или удалить цели.\n\n"
        "Я не даю давление — только поддержка и вопросы, чтобы ты лучше понимал себя."
    )
    await callback.message.edit_text(help_text, parse_mode="Markdown", reply_markup=help_back_button())
    await callback.answer()

@router.callback_query(F.data == "back_to_journal_from_help")
async def back_to_journal_from_help(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Journal.waiting_for_entry)
    await callback.message.edit_text(
        "Записать событие в дневник: просто напиши текст и отправь.",
        reply_markup=menu_button()
    )
    await callback.answer()

# --- Дневник: запись ---
@router.message(Journal.waiting_for_entry, F.text)
async def handle_journal_entry(message: Message, state: FSMContext):
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
    await callback.message.edit_text("✅ Запись добавлена в дневник.", reply_markup=menu_button())
    await state.set_state(Journal.waiting_for_entry)
    await callback.answer()

@router.callback_query(F.data == "cancel_entry")
async def cancel_entry(callback: CallbackQuery, state: FSMContext):
    await state.update_data(pending_entry=None)
    await callback.message.edit_text("Запись отменена. Можешь написать что-то ещё.", reply_markup=menu_button())
    await state.set_state(Journal.waiting_for_entry)
    await callback.answer()

# --- Вечерний итог ---
@router.callback_query(F.data == "start_evening_summary")
async def start_evening_summary(callback: CallbackQuery):
    user_id = await db.get_user_id(callback.from_user.id)
    today = date.today()
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
    await callback.answer()

# --- Административная команда /resetdb ---
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

# --- Заглушка для команды /change_goal (уже не нужна, так как цели управляются через меню) ---
@router.message(Command("change_goal"))
async def change_goal(message: Message):
    await message.answer(
        "Изменить цели можно через меню (кнопка «Меню» → «Мои цели» → «Изменить цель»)."
    )