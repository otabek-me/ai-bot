import logging
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType

from config import settings
from database import Database
from gemini_client import gemini
from memory import memory

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.full_name or "Do'stim"
    await message.answer(
        f"Salom, <b>{name}</b>! 👋\n\n"
        "Men sun'iy intellekt yordamchisiman. "
        "Menga istalgan savolingizni bering.\n\n"
        f"📊 Kunlik limitingiz: <b>{settings.DAILY_LIMIT} ta so'rov</b>\n"
        "🔄 /reset — suhbat tarixini tozalash\n"
        "📈 /usage — bugungi foydalanishingiz",
        parse_mode="HTML",
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    memory.clear(message.from_user.id)
    await message.answer("✅ Suhbat tarixi tozalandi. Yangi suhbat boshlashingiz mumkin.")


@router.message(Command("usage"))
async def cmd_usage(message: Message, db: Database):
    user_id = message.from_user.id
    usage = await db.get_today_usage(user_id)
    limit = await db.get_user_limit(user_id, settings.DAILY_LIMIT)
    limit_text = "Cheksiz ♾️" if limit == -1 else str(limit)
    remaining = "♾️" if limit == -1 else str(max(0, limit - usage))

    await message.answer(
        f"📊 <b>Bugungi foydalanish:</b>\n\n"
        f"Yuborilgan so'rovlar: <b>{usage}</b>\n"
        f"Kunlik limit: <b>{limit_text}</b>\n"
        f"Qolgan: <b>{remaining}</b>",
        parse_mode="HTML",
    )


# ── Guruh chat: faqat reply yoki mention da javob berish ─────────────────

def _is_bot_mentioned(message: Message, bot_username: str) -> bool:
    """Xabarda bot username'i tilga olinganligini tekshirish."""
    if not message.text:
        return False
    return f"@{bot_username}" in message.text


async def _should_respond_in_group(message: Message, bot: Bot) -> bool:
    me = await bot.get_me()

    # Reply qilingan bo'lsa
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == me.id
    ):
        return True

    # Mention qilingan bo'lsa
    if me.username and _is_bot_mentioned(message, me.username):
        return True

    return False


# ── Asosiy xabar handleri ─────────────────────────────────────────────────

@router.message(F.text & F.chat.type == ChatType.PRIVATE)
async def handle_private_message(message: Message, bot: Bot, db: Database):
    await _process_message(message, bot, db, is_group=False)


@router.message(F.text & F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_message(message: Message, bot: Bot, db: Database):
    if not await _should_respond_in_group(message, bot):
        return
    await _process_message(message, bot, db, is_group=True)


async def _process_message(
    message: Message, bot: Bot, db: Database, is_group: bool
):
    user_id = message.from_user.id
    text = message.text.strip()

    # Guruhda mention'ni matndan olib tashlash
    if is_group:
        me = await bot.get_me()
        if me.username:
            text = text.replace(f"@{me.username}", "").strip()

    if not text:
        return

    # Typing... ko'rsatish
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        reply, tokens = await gemini.ask(user_id, text)

        # Foydalanishni bazaga yozish
        await db.increment_usage(user_id)
        await db.log_api_call(user_id, tokens)

        # Javob uzun bo'lsa bo'lib yuborish (Telegram 4096 limit)
        if len(reply) <= 4096:
            await message.reply(reply, parse_mode="Markdown")
        else:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await message.reply(chunk, parse_mode="Markdown")

    except Exception as exc:
        logger.error(f"Xabar qayta ishlashda xato: {exc}")
        await message.reply(
            "⚠️ Hozircha server band. Bir ozdan keyin qayta urinib ko'ring."
        )
