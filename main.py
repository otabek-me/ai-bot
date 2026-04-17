import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import settings
from database import Database
from middlewares import LimitMiddleware, ThrottleMiddleware
from handlers import user_router, admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    db = Database(settings.DB_PATH)
    await db.init()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Command menu qo'shish
    user_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="reset", description="Suhbat tarixini tozalash"),
        BotCommand(command="usage", description="Bugungi foydalanish"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        BotCommand(command="stats", description="Statistika"),
        BotCommand(command="setlimit", description="Limit o'rnatish"),
        BotCommand(command="unlimit", description="Cheksiz limit"),
        BotCommand(command="ban", description="Bloklash"),
        BotCommand(command="unban", description="Blokdan chiqarish"),
        BotCommand(command="resetuser", description="User tarixini tozalash"),
        BotCommand(command="broadcast", description="Barchaga xabar"),
        BotCommand(command="users", description="Foydalanuvchilar ro'yxati"),
    ]
    for admin_id in settings.ADMIN_IDS:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))

    # Middleware larni ulash
    dp.message.middleware(ThrottleMiddleware(rate=0.5))
    dp.message.middleware(LimitMiddleware(db=db, daily_limit=settings.DAILY_LIMIT))

    # Router larni ulash
    dp.include_router(admin_router)
    dp.include_router(user_router)

    # bot va db ni handlerlarga uzatish
    dp["db"] = db

    logger.info("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
