from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def start_goals_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать определение целей и желаний", callback_data="start_goals")]
    ])

def goal_session_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить и сохранить цели", callback_data="finish_goal_session"),
         InlineKeyboardButton(text="❌ Прервать сессию", callback_data="abort_goal_session")]
    ])

def goal_summary_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_goals"),
         InlineKeyboardButton(text="✏️ Добавить ещё", callback_data="add_more_goals")]
    ])

def confirm_entry_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, записать", callback_data="confirm_entry"),
         InlineKeyboardButton(text="❌ Нет, удалить", callback_data="cancel_entry")]
    ])

def start_evening_summary_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌙 Подвести итог дня", callback_data="start_evening_summary")]
    ])

def resetdb_confirm_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, ОЧИСТИТЬ ВСЁ", callback_data="confirm_resetdb"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_resetdb")]
    ])

def menu_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Меню", callback_data="show_main_menu")]
    ])

def entry_added_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Мои записи", callback_data="my_entries_menu"),
         InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мои цели и желания", callback_data="my_goals_menu"),
         InlineKeyboardButton(text="📝 Мои записи", callback_data="my_entries_menu")],
        [InlineKeyboardButton(text="📜 Мои вечерние итоги", callback_data="my_evening_summaries"),
         InlineKeyboardButton(text="💭 Мои сны", callback_data="my_dreams")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="help_menu"),
         InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def goals_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить цель/желание", callback_data="add_goal_start")],
        [InlineKeyboardButton(text="✏️ Изменить цель/желание", callback_data="edit_goal_list")],
        [InlineKeyboardButton(text="🗑 Удалить цель/желание", callback_data="delete_goal_list")],
        [InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def goals_list_for_edit_keyboard(goals_with_ids):
    keyboard = []
    for goal_id, goal_text in goals_with_ids:
        display_text = goal_text[:40] + "..." if len(goal_text) > 40 else goal_text
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"edit_goal_{goal_id}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def goals_list_for_delete_keyboard(goals_with_ids):
    keyboard = []
    for goal_id, goal_text in goals_with_ids:
        display_text = goal_text[:40] + "..." if len(goal_text) > 40 else goal_text
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"delete_goal_{goal_id}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_change_keyboard(goal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_edit_{goal_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])

def confirm_delete_keyboard(goal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{goal_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])

def entries_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить запись", callback_data="add_entry_start")],
        [InlineKeyboardButton(text="✏️ Изменить запись", callback_data="edit_entry_list")],
        [InlineKeyboardButton(text="🗑 Удалить запись", callback_data="delete_entry_list")],
        [InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def entries_list_for_edit_keyboard(entries_with_ids):
    keyboard = []
    for entry in entries_with_ids:
        entry_id = entry['id']
        content = entry['content']
        display_text = content[:40] + "..." if len(content) > 40 else content
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"edit_entry_{entry_id}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def entries_list_for_delete_keyboard(entries_with_ids):
    keyboard = []
    for entry in entries_with_ids:
        entry_id = entry['id']
        content = entry['content']
        display_text = content[:40] + "..." if len(content) > 40 else content
        keyboard.append([InlineKeyboardButton(text=display_text, callback_data=f"delete_entry_{entry_id}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_change_entry_keyboard(entry_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_edit_entry_{entry_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])

def confirm_delete_entry_keyboard(entry_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_entry_{entry_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_journal")]
    ])

def help_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def cancel_add_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В начало", callback_data="cancel_add_back")]
    ])

def evening_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить запись", callback_data="evening_add_entry"),
         InlineKeyboardButton(text="🌙 Подвести итог дня", callback_data="start_evening_summary")]
    ])

def dates_list_keyboard(dates):
    keyboard = []
    for d in dates:
        keyboard.append([InlineKeyboardButton(text=f"📅 Итог за {d.strftime('%d.%m.%Y')}", callback_data=f"show_summary_{d.isoformat()}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def summary_view_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])

def morning_dream_buttons():
    """Кнопки после утренних рекомендаций: записать сон или отмена."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💭 Записать сон", callback_data="dream_analysis_start"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="skip_dream")]
    ])

def cancel_dream_button():
    """Кнопка отмены при записи сна."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="skip_dream")]
    ])

def dream_saved_buttons():
    """Кнопки после разбора сна: сохранить в раздел снов или отмена."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить сон", callback_data="save_dream_only"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="skip_dream")]
    ])

def dreams_list_keyboard(dates):
    """Клавиатура для выбора даты сна."""
    keyboard = []
    for d in dates:
        keyboard.append([InlineKeyboardButton(text=f"💭 Сон за {d.strftime('%d.%m.%Y')}", callback_data=f"show_dream_{d.isoformat()}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def dream_view_keyboard(dream_date):
    """Клавиатура для просмотра сна: удалить, назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить запись", callback_data=f"delete_dream_{dream_date.isoformat()}"),
         InlineKeyboardButton(text="🏠 В начало", callback_data="back_to_journal")]
    ])    