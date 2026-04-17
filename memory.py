import time
from collections import defaultdict
from typing import TypedDict


class Message(TypedDict):
    role: str   # "user" | "model"
    parts: list[dict]


class ConversationMemory:
    """
    Har bir foydalanuvchi uchun so'nggi N ta xabar tarixini saqlaydi.
    TTL o'tib ketgan suhbatlar avtomatik tozalanadi.
    """

    def __init__(self, max_history: int = 10, ttl_seconds: int = 86400):
        self.max_history = max_history
        self.ttl = ttl_seconds
        # { user_id: {"history": [...], "last_active": timestamp} }
        self._store: dict[int, dict] = defaultdict(
            lambda: {"history": [], "last_active": time.time()}
        )

    def _is_expired(self, user_id: int) -> bool:
        entry = self._store.get(user_id)
        if not entry:
            return True
        return (time.time() - entry["last_active"]) > self.ttl

    def get(self, user_id: int) -> list[Message]:
        if self._is_expired(user_id):
            self.clear(user_id)
            return []
        return self._store[user_id]["history"]

    def add(self, user_id: int, role: str, text: str):
        if self._is_expired(user_id):
            self.clear(user_id)

        history = self._store[user_id]["history"]
        history.append({"role": role, "parts": [{"text": text}]})

        # Oxirgi max_history ta xabarni saqlash
        if len(history) > self.max_history:
            self._store[user_id]["history"] = history[-self.max_history :]

        self._store[user_id]["last_active"] = time.time()

    def clear(self, user_id: int):
        self._store.pop(user_id, None)

    def cleanup_expired(self):
        """Muddati o'tgan suhbatlarni xotiradan tozalash."""
        expired = [uid for uid in self._store if self._is_expired(uid)]
        for uid in expired:
            del self._store[uid]
        return len(expired)


# Global instance — butun loyiha bo'ylab ishlatiladi
memory = ConversationMemory()
