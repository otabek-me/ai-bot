import aiosqlite
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Ma'lumotlar bazasi ulandi: {self.db_path}")

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _create_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                is_banned   INTEGER DEFAULT 0,
                custom_limit INTEGER DEFAULT NULL,
                created_at  TEXT DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id     INTEGER NOT NULL,
                usage_date  TEXT NOT NULL,
                count       INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );

            CREATE TABLE IF NOT EXISTS api_stats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        await self._conn.commit()

    # ── Foydalanuvchi ──────────────────────────────────────────────────────

    async def upsert_user(self, user_id: int, username: str, full_name: str):
        await self._conn.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
            """,
            (user_id, username or "", full_name or ""),
        )
        await self._conn.commit()

    async def get_user(self, user_id: int) -> Optional[aiosqlite.Row]:
        async with self._conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone()

    async def get_all_users(self) -> list[aiosqlite.Row]:
        async with self._conn.execute(
            "SELECT user_id FROM users WHERE is_banned = 0"
        ) as cur:
            return await cur.fetchall()

    async def get_all_users_with_details(self) -> list[dict]:
        async with self._conn.execute(
            """
            SELECT user_id, username, full_name, is_banned, custom_limit, created_at
            FROM users
            ORDER BY created_at DESC
            """
        ) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def ban_user(self, user_id: int):
        await self._conn.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        await self._conn.commit()

    async def unban_user(self, user_id: int):
        await self._conn.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        await self._conn.commit()

    async def is_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user["is_banned"])

    # ── Limit boshqaruvi ───────────────────────────────────────────────────

    async def get_today_usage(self, user_id: int) -> int:
        today = str(date.today())
        async with self._conn.execute(
            "SELECT count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today),
        ) as cur:
            row = await cur.fetchone()
            return row["count"] if row else 0

    async def increment_usage(self, user_id: int):
        today = str(date.today())
        await self._conn.execute(
            """
            INSERT INTO daily_usage (user_id, usage_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1
            """,
            (user_id, today),
        )
        await self._conn.commit()

    async def get_user_limit(self, user_id: int, default_limit: int) -> int:
        user = await self.get_user(user_id)
        if user and user["custom_limit"] is not None:
            return user["custom_limit"]
        return default_limit

    async def set_custom_limit(self, user_id: int, limit: int):
        await self._conn.execute(
            "UPDATE users SET custom_limit = ? WHERE user_id = ?",
            (limit, user_id),
        )
        await self._conn.commit()

    async def remove_custom_limit(self, user_id: int):
        await self._conn.execute(
            "UPDATE users SET custom_limit = NULL WHERE user_id = ?",
            (user_id,),
        )
        await self._conn.commit()

    async def is_limit_reached(
        self, user_id: int, default_limit: int
    ) -> bool:
        limit = await self.get_user_limit(user_id, default_limit)
        if limit == -1:  # cheksiz
            return False
        usage = await self.get_today_usage(user_id)
        return usage >= limit

    # ── Statistika ─────────────────────────────────────────────────────────

    async def log_api_call(self, user_id: int, tokens: int = 0):
        await self._conn.execute(
            "INSERT INTO api_stats (user_id, tokens_used) VALUES (?, ?)",
            (user_id, tokens),
        )
        await self._conn.commit()

    async def get_stats(self) -> dict:
        today = str(date.today())

        async with self._conn.execute(
            "SELECT COUNT(DISTINCT user_id) as cnt FROM daily_usage WHERE usage_date = ?",
            (today,),
        ) as cur:
            row = await cur.fetchone()
            active_today = row["cnt"] if row else 0

        async with self._conn.execute(
            "SELECT COUNT(*) as cnt FROM api_stats WHERE date(created_at) = ?",
            (today,),
        ) as cur:
            row = await cur.fetchone()
            api_calls_today = row["cnt"] if row else 0

        async with self._conn.execute(
            "SELECT COUNT(*) as cnt FROM users"
        ) as cur:
            row = await cur.fetchone()
            total_users = row["cnt"] if row else 0

        async with self._conn.execute(
            "SELECT COUNT(*) as cnt FROM api_stats"
        ) as cur:
            row = await cur.fetchone()
            total_api_calls = row["cnt"] if row else 0

        return {
            "active_today": active_today,
            "api_calls_today": api_calls_today,
            "total_users": total_users,
            "total_api_calls": total_api_calls,
            "date": today,
        }
