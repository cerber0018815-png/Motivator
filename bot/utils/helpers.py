from datetime import datetime
from typing import Dict, List
from sqlalchemy import select, desc
from bot.database import SessionLocal, User, Message, DailyEntry

def get_user_context(user_id: int, limit: int = 20) -> Dict:
    """Синхронная версия – собирает контекст для DeepSeek."""
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if not user:
            return {"goals": "", "history": [], "today_entry": None, "date": datetime.utcnow().date().isoformat()}

        # Последние сообщения
        stmt = select(Message).where(Message.user_id == user_id).order_by(desc(Message.created_at)).limit(limit)
        result = session.execute(stmt)
        messages = result.scalars().all()
        history = [{"role": m.role, "text": m.text, "created_at": m.created_at.isoformat()} for m in reversed(messages)]

        # Запись за сегодня
        today = datetime.utcnow().date()
        stmt = select(DailyEntry).where(DailyEntry.user_id == user_id, DailyEntry.date == today)
        today_entry = session.execute(stmt).scalar_one_or_none()

        return {
            "goals": user.goals or "",
            "history": history,
            "today_entry": today_entry,
            "date": today.isoformat(),
            "timezone": user.timezone or "UTC"
        }
    finally:
        session.close()