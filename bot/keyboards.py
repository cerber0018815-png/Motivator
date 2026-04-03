# keyboards.py — все инлайн-клавиатуры для бота

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def start_goals_button():
    """Кнопка для начала сессии определения целей."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать определение целей", callback_data="start_goals")]
    ])

def goal_session_buttons():
    """Кнопки во время активной сессии: завершить или прервать."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить и сохранить цели", callback_data="finish_goal_session"),
         InlineKeyboardButton(text="❌ Прервать сессию", callback_data="abort_goal_session")]
    ])

def goal_summary_buttons():
    """Кнопки после подведения итога целей: подтвердить или добавить ещё."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_goals"),
         InlineKeyboardButton(text="✏️ Добавить ещё", callback_data="add_more_goals")]
    ])

def journal_help_button():
    """Кнопка для вызова справки в режиме дневника."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Справка", callback_data="help")]
    ])

def help_back_button():
    """Кнопка возврата из справки в режим дневника."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_journal_from_help")]
    ])

def confirm_entry_buttons():
    """Кнопки подтверждения записи в дневник."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, записать", callback_data="confirm_entry"),
         InlineKeyboardButton(text="❌ Нет, удалить", callback_data="cancel_entry")]
    ])

def start_evening_summary_button():
    """Кнопка для запуска вечернего итога."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌙 Подвести итог дня", callback_data="start_evening_summary")]
    ])

def resetdb_confirm_buttons():
    """Кнопки подтверждения очистки базы данных (только для админов)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, ОЧИСТИТЬ ВСЁ", callback_data="confirm_resetdb"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_resetdb")]
    ])


# ---------- НОВЫЕ КЛАВИАТУРЫ ДЛЯ МЕНЮ И УПРАВЛЕНИЯ ЦЕЛЯМИ ----------

def menu_button():
    """Кнопка глобального меню, добавляется под каждым сообщением в режиме дневника."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Меню", callback_data="show_main_menu")]
    ])

def main_menu_keyboard():
    """Главное меню: Мои цели, В начало (дневник)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="my_goals_menu")],
        [InlineKeyboardButton(text="📝 В начало", callback_data="back_to_journal")]
    ])

def goals_menu_keyboard():
    """Меню управления целями после просмотра списка."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить цель", callback_data="add_goal_start")],
        [InlineKeyboardButton(text="✏️ Изменить цель", callback_data="edit_goal_list")],
        [InlineKeyboardButton(text="🗑 Удалить цель", callback_data="delete_goal_list")],
        [InlineKeyboardButton(text="📝 В начало", callback_data="back_to_journal")]
    ])

def goals_list_for_edit_keyboard(goals_with_ids):
    """
    Клавиатура для выбора цели на изменение.
    goals_with_ids: список кортежей (goal_id, goal_text)
    """
    keyboard = []
    for goal_id, goal_text in goals_with_ids:
        display_text = goal_text[:40] + "..." if len(goal_text) > 40 else goal_text
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"edit_goal_{goal_id}")])
    keyboard.append([InlineKeyboardButton(text="📝 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def goals_list_for_delete_keyboard(goals_with_ids):
    """
    Клавиатура для выбора цели на удаление.
    """
    keyboard = []
    for goal_id, goal_text in goals_with_ids:
        display_text = goal_text[:40] + "..." if len(goal_text) > 40 else goal_text
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"delete_goal_{goal_id}")])
    keyboard.append([InlineKeyboardButton(text="📝 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_change_keyboard(goal_id):
    """Кнопки подтверждения изменения цели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_edit_{goal_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])

def confirm_delete_keyboard(goal_id):
    """Кнопки подтверждения удаления цели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{goal_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])