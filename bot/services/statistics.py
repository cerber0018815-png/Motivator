from sqlalchemy import select, func
from datetime import datetime, timedelta
from bot.database import AsyncSessionLocal, DailyEntry, User

async def get_weekly_stats(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            return "Пользователь не найден."

        week_ago = datetime.utcnow() - timedelta(days=7)
        entries = await session.execute(
            select(DailyEntry)
            .where(DailyEntry.user_id == user.id, DailyEntry.date >= week_ago)
            .order_by(DailyEntry.date)
        )
        entries = entries.scalars().all()
        if not entries:
            return "За последнюю неделю нет записей."

        lines = []
        for e in entries:
            date_str = e.date.strftime('%d.%m')
            if e.actions_done:
                lines.append(f"{date_str}: {e.actions_done[:100]}")
            else:
                lines.append(f"{date_str}: нет данных")
        return "📊 **Что удалось за неделю:**\n" + "\n".join(lines)