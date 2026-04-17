import time
import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message

from config import settings
from database import Database

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """
    Bir foydalanuvchi juda tez-tez xabar yuborganida cheklash.
    `rate` soniyada bir xabar (default: 0.5 sek).
    """

    def __init__(self, rate: float = 0.5):
        self.rate = rate
        self._last_message: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()
        last = self._last_message.get(user_id, 0)

        if now - last < self.rate:
            return  # Xabarni e'tiborsiz qoldir

        self._last_message[user_id] = now
        return await handler(event, data)


class LimitMiddleware(BaseMiddleware):
    """
    Kunlik so'rovlar limitini tekshiradi.
    Limit tugagan bo'lsa Gemini'ga so'rov YUBORILMAYDI.
    """

    def __init__(self, db: Database, daily_limit: int):
        self.db = db
        self.daily_limit = daily_limit

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        # /start, /help, admin buyruqlari limitga tushmasin
        if event.text and event.text.startswith("/"):
            return await handler(event, data)

        # Foydalanuvchini bazaga qo'shish (yangi bo'lsa)
        await self.db.upsert_user(
            user_id=user_id,
            username=event.from_user.username or "",
            full_name=event.from_user.full_name or "",
        )

        # Ban tekshiruvi
        if await self.db.is_banned(user_id):
            await event.answer("Siz botdan bloklandingiz. Admin bilan bog'laning.")
            return

        # Limit tekshiruvi
        if await self.db.is_limit_reached(user_id, self.daily_limit):
            usage = await self.db.get_today_usage(user_id)
            limit = await self.db.get_user_limit(user_id, self.daily_limit)
            await event.answer(
                f"⚠️ Kunlik limitingiz tugadi ({usage}/{limit}).\n\n"
                "Ertaga qayta urinib ko'ring yoki admin bilan bog'laning.",
                parse_mode="HTML",
            )
            return

        return await handler(event, data)
