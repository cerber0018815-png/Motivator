import asyncpg
from datetime import date
from typing import List, Optional, Dict

class Database:
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
            # Проверяем и добавляем недостающие колонки
            columns = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            col_names = [c['column_name'] for c in columns]
            if 'first_name' not in col_names:
                await conn.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
            if 'last_name' not in col_names:
                await conn.execute('ALTER TABLE users ADD COLUMN last_name TEXT')
            if 'username' not in col_names:
                await conn.execute('ALTER TABLE users ADD COLUMN username TEXT')
            if 'created_at' not in col_names:
                await conn.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT NOW()')

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
                CREATE UNIQUE INDEX IF NOT EXISTS idx_evening_summaries_user_day 
                ON evening_summaries (user_id, day)
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
            await conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_morning_suggestions_user_day 
                ON morning_suggestions (user_id, day)
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS dream_analyses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    dream_text TEXT NOT NULL,
                    analysis_text TEXT NOT NULL,
                    dream_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, dream_date)
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

    # --- Цели ---
    async def add_goal(self, user_id: int, goal_text: str):
        await self.add_new_goal(user_id, goal_text)

    async def get_active_goals(self, user_id: int) -> List[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT goal_text FROM goals WHERE user_id = $1 AND is_active = TRUE ORDER BY created_at', user_id)
            return [row['goal_text'] for row in rows]

    async def add_new_goal(self, user_id: int, goal_text: str):
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO goals (user_id, goal_text, is_active) VALUES ($1, $2, TRUE)', user_id, goal_text)

    async def get_all_active_goals_with_ids(self, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, goal_text FROM goals WHERE user_id = $1 AND is_active = TRUE ORDER BY created_at', user_id)
            return [(row['id'], row['goal_text']) for row in rows]

    async def update_goal(self, goal_id: int, new_text: str):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE goals SET goal_text = $1, updated_at = NOW() WHERE id = $2', new_text, goal_id)

    async def delete_goal(self, goal_id: int):
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

    async def get_journal_entries_with_ids_for_day(self, user_id: int, day: date) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, content, created_at FROM journal_entries WHERE user_id = $1 AND day = $2 ORDER BY created_at', user_id, day)
            return [{'id': r['id'], 'content': r['content'], 'created_at': r['created_at']} for r in rows]

    async def update_journal_entry(self, entry_id: int, new_content: str):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE journal_entries SET content = $1 WHERE id = $2', new_content, entry_id)

    async def delete_journal_entry(self, entry_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM journal_entries WHERE id = $1', entry_id)

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

    async def get_all_evening_summary_dates(self, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT DISTINCT day FROM evening_summaries WHERE user_id = $1 ORDER BY day DESC', user_id)
            return [row['day'] for row in rows]

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

    # --- Сны ---
    async def add_dream_analysis(self, user_id: int, dream_text: str, analysis_text: str, dream_date: date):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO dream_analyses (user_id, dream_text, analysis_text, dream_date)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, dream_date) DO UPDATE SET
                    dream_text = EXCLUDED.dream_text,
                    analysis_text = EXCLUDED.analysis_text,
                    created_at = NOW()
            ''', user_id, dream_text, analysis_text, dream_date)

    async def get_dream_analyses_dates(self, user_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT DISTINCT dream_date FROM dream_analyses WHERE user_id = $1 ORDER BY dream_date DESC', user_id)
            return [row['dream_date'] for row in rows]

    async def get_dream_analysis_by_date(self, user_id: int, dream_date: date):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT dream_text, analysis_text, created_at FROM dream_analyses WHERE user_id = $1 AND dream_date = $2', user_id, dream_date)
            if row:
                return {'dream_text': row['dream_text'], 'analysis_text': row['analysis_text'], 'created_at': row['created_at']}
            return None

    async def delete_dream_analysis(self, user_id: int, dream_date: date):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM dream_analyses WHERE user_id = $1 AND dream_date = $2', user_id, dream_date)        