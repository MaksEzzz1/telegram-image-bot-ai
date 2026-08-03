# database.py
# -----------------------------------------------------------------------------
# Простое хранилище пользователей и статистики на SQLite (через aiosqlite,
# чтобы не блокировать asyncio event loop).
# -----------------------------------------------------------------------------

import time
from typing import Optional

import aiosqlite

from config import DB_PATH


CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id      INTEGER PRIMARY KEY,
    username     TEXT,
    first_name   TEXT,
    joined_at    INTEGER,
    last_request INTEGER DEFAULT 0,
    requests_count INTEGER DEFAULT 0
);
"""


class Database:
    """
    Небольшая обёртка над SQLite.
    Каждый метод сам открывает/закрывает соединение — для бота такого масштаба
    этого достаточно и это безопаснее, чем держать одно общее соединение
    между корутинами.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init(self) -> None:
        """Создаёт таблицы, если их ещё нет. Вызывается один раз при старте."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_USERS_TABLE)
            await db.commit()

    async def add_user(self, user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
        """Регистрирует нового пользователя (или игнорирует, если уже есть)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, joined_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name
                """,
                (user_id, username, first_name, int(time.time())),
            )
            await db.commit()

    async def get_last_request_time(self, user_id: int) -> int:
        """Возвращает unix-время последнего запроса пользователя (0, если не было)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT last_request FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def update_last_request(self, user_id: int) -> None:
        """Обновляет время последнего запроса и увеличивает счётчик генераций."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET last_request = ?, requests_count = requests_count + 1
                WHERE user_id = ?
                """,
                (int(time.time()), user_id),
            )
            await db.commit()

    async def get_stats(self, user_id: int) -> dict:
        """Возвращает статистику пользователя (сколько картинок сгенерировал и т.д.)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT requests_count, joined_at FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return {"requests_count": 0, "joined_at": 0}
            return {"requests_count": row[0], "joined_at": row[1]}

    async def get_total_users(self) -> int:
        """Общее число пользователей бота (для админ-статистики)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0


# Единый экземпляр базы данных, который импортируют остальные модули
db = Database()
