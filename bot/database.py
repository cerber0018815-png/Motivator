# database.py — работа с PostgreSQL через asyncpg

import asyncpg
from datetime import date
from typing import List, Optional, Dict

class Database:
    """Класс для управления подключением к БД и выполнения запросов."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def init(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        await self._create_tables()

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    goal_text TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    day DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS evening_summaries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    summary_text TEXT NOT NULL,
                    day DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS morning_suggestions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    suggestion_text TEXT NOT NULL,
                    day DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

    # --- Пользователи ---
    async def add_user(self, telegram_id: int, username: str, first_name: str, last_name: str) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
                RETURNING id
            ''', telegram_id, username, first_name, last_name)

    async def get_user_id(self, telegram_id: int) -> Optional[int]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
            return row['id'] if row else None

    # --- Цели (старые методы для совместимости) ---
    async def add_goal(self, user_id: int, goal_text: str):
        """Добавляет новую активную цель, не деактивируя старые."""
        await self.add_new_goal(user_id, goal_text)

    async def get_active_goals(self, user_id: int) -> List[str]:
        """Возвращает список текстов активных целей."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT goal_text FROM goals WHERE user_id = $1 AND is_active = TRUE ORDER BY created_at', user_id)
            return [row['goal_text'] for row in rows]

    # --- Новые методы для множественных целей ---
    async def add_new_goal(self, user_id: int, goal_text: str):
        """Добавляет новую активную цель, не деактивируя старые."""
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO goals (user_id, goal_text, is_active) VALUES ($1, $2, TRUE)', user_id, goal_text)

    async def get_all_active_goals_with_ids(self, user_id: int):
        """Возвращает список всех активных целей пользователя в виде кортежей (id, goal_text)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, goal_text FROM goals WHERE user_id = $1 AND is_active = TRUE ORDER BY created_at', user_id)
            return [(row['id'], row['goal_text']) for row in rows]

    async def update_goal(self, goal_id: int, new_text: str):
        """Обновляет текст цели по её id."""
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE goals SET goal_text = $1, updated_at = NOW() WHERE id = $2', new_text, goal_id)

    async def delete_goal(self, goal_id: int):
        """Физически удаляет цель из базы данных."""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM goals WHERE id = $1', goal_id)

    # --- Дневник ---
    async def add_journal_entry(self, user_id: int, content: str):
        day = date.today()
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO journal_entries (user_id, content, day) VALUES ($1, $2, $3)', user_id, content, day)

    async def get_journal_entries_for_day(self, user_id: int, day: date) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT content, created_at FROM journal_entries WHERE user_id = $1 AND day = $2 ORDER BY created_at', user_id, day)
            return [{'content': r['content'], 'created_at': r['created_at']} for r in rows]

    # --- Вечерние итоги ---
    async def add_evening_summary(self, user_id: int, summary_text: str, day: date):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO evening_summaries (user_id, summary_text, day)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, day) DO UPDATE SET summary_text = EXCLUDED.summary_text
            ''', user_id, summary_text, day)

    async def get_evening_summary_for_day(self, user_id: int, day: date) -> Optional[str]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT summary_text FROM evening_summaries WHERE user_id = $1 AND day = $2', user_id, day)
            return row['summary_text'] if row else None

    # --- Утренние советы ---
    async def add_morning_suggestion(self, user_id: int, suggestion_text: str, day: date):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO morning_suggestions (user_id, suggestion_text, day)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, day) DO UPDATE SET suggestion_text = EXCLUDED.suggestion_text
            ''', user_id, suggestion_text, day)

    async def get_morning_suggestion_for_day(self, user_id: int, day: date) -> Optional[str]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT suggestion_text FROM morning_suggestions WHERE user_id = $1 AND day = $2', user_id, day)
            return row['suggestion_text'] if row else None