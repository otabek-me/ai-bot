import asyncio
import logging
from functools import wraps
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from config import settings
from database import Database
from memory import memory

logger = logging.getLogger(__name__)
router = Router()


# ── Admin tekshiruvi (decorator) ──────────────────────────────────────────

def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, **kwargs):
        if message.from_user.id not in settings.ADMIN_IDS:
            await message.answer("❌ Bu buyruq faqat adminlar uchun.")
            return
        return await handler(message, **kwargs)
    return wrapper


# ── /stats ────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
@admin_only
async def cmd_stats(message: Message, db: Database):
    stats = await db.get_stats()
    await message.answer(
        f"📊 <b>Statistika ({stats['date']})</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🟢 Bugun faol: <b>{stats['active_today']}</b>\n"
        f"🤖 Bugun API so'rovlar: <b>{stats['api_calls_today']}</b>\n"
        f"📦 Jami API so'rovlar: <b>{stats['total_api_calls']}</b>",
        parse_mode="HTML",
    )


# ── /setlimit ─────────────────────────────────────────────────────────────

@router.message(Command("setlimit"))
@admin_only
async def cmd_setlimit(message: Message, db: Database):
    """
    Ishlatish: /setlimit 123456789 50
    """
    args = message.text.split()[1:]
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await message.answer(
            "❌ Noto'g'ri format.\n\n"
            "✅ To'g'ri: <code>/setlimit USER_ID LIMIT</code>\n"
            "Misol: <code>/setlimit 123456789 50</code>",
            parse_mode="HTML",
        )
        return

    user_id = int(args[0])
    limit = int(args[1])

    await db.upsert_user(user_id, "", "")
    await db.set_custom_limit(user_id, limit)
    await message.answer(
        f"✅ Foydalanuvchi <code>{user_id}</code> uchun "
        f"kunlik limit <b>{limit}</b> ga o'rnatildi.",
        parse_mode="HTML",
    )
    logger.info(f"Admin {message.from_user.id} → setlimit {user_id}={limit}")


# ── /unlimit ──────────────────────────────────────────────────────────────

@router.message(Command("unlimit"))
@admin_only
async def cmd_unlimit(message: Message, db: Database):
    """
    Ishlatish: /unlimit 123456789
    Limitni cheksiz (-1) qilish
    """
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer(
            "❌ Noto'g'ri format.\n\n"
            "✅ To'g'ri: <code>/unlimit USER_ID</code>",
            parse_mode="HTML",
        )
        return

    user_id = int(args[0])
    await db.upsert_user(user_id, "", "")
    await db.set_custom_limit(user_id, -1)  # -1 = cheksiz
    await message.answer(
        f"✅ Foydalanuvchi <code>{user_id}</code> uchun limit <b>cheksiz</b> qilindi.",
        parse_mode="HTML",
    )
    logger.info(f"Admin {message.from_user.id} → unlimit {user_id}")


# ── /ban / /unban ─────────────────────────────────────────────────────────

@router.message(Command("ban"))
@admin_only
async def cmd_ban(message: Message, db: Database):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer("❌ Format: <code>/ban USER_ID</code>", parse_mode="HTML")
        return

    user_id = int(args[0])
    await db.ban_user(user_id)
    await message.answer(
        f"🚫 Foydalanuvchi <code>{user_id}</code> bloklandi.",
        parse_mode="HTML",
    )


@router.message(Command("unban"))
@admin_only
async def cmd_unban(message: Message, db: Database):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer("❌ Format: <code>/unban USER_ID</code>", parse_mode="HTML")
        return

    user_id = int(args[0])
    await db.unban_user(user_id)
    await message.answer(
        f"✅ Foydalanuvchi <code>{user_id}</code> blokdan chiqarildi.",
        parse_mode="HTML",
    )


# ── /resetuser ────────────────────────────────────────────────────────────

@router.message(Command("resetuser"))
@admin_only
async def cmd_reset_user(message: Message, db: Database):
    """Ma'lum foydalanuvchining suhbat tarixini tozalash."""
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer(
            "❌ Format: <code>/resetuser USER_ID</code>", parse_mode="HTML"
        )
        return

    user_id = int(args[0])
    memory.clear(user_id)
    await message.answer(
        f"✅ Foydalanuvchi <code>{user_id}</code> suhbat tarixi tozalandi.",
        parse_mode="HTML",
    )


# ── /broadcast ────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
@admin_only
async def cmd_broadcast(message: Message, bot: Bot, db: Database):
    """
    Ishlatish: /broadcast Xabar matni bu yerda
    """
    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer(
            "❌ Format: <code>/broadcast Xabar matni</code>", parse_mode="HTML"
        )
        return

    users = await db.get_all_users()
    total = len(users)
    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"📤 Broadcast boshlandi...\n"
        f"Jami foydalanuvchilar: <b>{total}</b>",
        parse_mode="HTML",
    )

    for user_row in users:
        try:
            await bot.send_message(user_row["user_id"], text, parse_mode="HTML")
            sent += 1
        except Exception as exc:
            failed += 1
            logger.warning(f"Broadcast yuborib bo'lmadi {user_row['user_id']}: {exc}")

        # Rate limiting: Telegram 30 msg/sek limiti
        await asyncio.sleep(0.05)

        # Har 50 ta da progress yangilash
        if (sent + failed) % 50 == 0:
            await status_msg.edit_text(
                f"📤 Yuborilmoqda...\n"
                f"✅ Yuborildi: <b>{sent}</b>\n"
                f"❌ Xato: <b>{failed}</b>",
                parse_mode="HTML",
            )

    await status_msg.edit_text(
        f"✅ <b>Broadcast tugadi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborib bo'lmadi: <b>{failed}</b>\n"
        f"📊 Jami: <b>{total}</b>",
        parse_mode="HTML",
    )
    logger.info(f"Broadcast: sent={sent}, failed={failed}, total={total}")


# ── /users ────────────────────────────────────────────────────────────────

@router.message(Command("users"))
@admin_only
async def cmd_users(message: Message, db: Database):
    """
    Barcha foydalanuvchilarni ro'yxatini ko'rsatish
    """
    users = await db.get_all_users_with_details()
    total = len(users)

    if not users:
        await message.answer("❌ Hech qanday foydalanuvchi topilmadi.")
        return

    # Ro'yxatni format qilish
    user_list = []
    for user in users:
        user_id = user["user_id"]
        username = f"@{user['username']}" if user["username"] else "Noma'lum"
        full_name = user["full_name"] or "Noma'lum"
        status = "🚫 Bloklangan" if user["is_banned"] else "✅ Faol"
        limit = f"Limit: {user['custom_limit']}" if user["custom_limit"] else "Limit: Default"
        created = user["created_at"]

        user_info = (
            f"👤 <b>{full_name}</b> ({username})\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 Ro'yxatdan: {created}\n"
            f"📊 {limit} | {status}\n"
            f"{'─' * 30}"
        )
        user_list.append(user_info)

    # Xabarlarni bo'lib yuborish (Telegram limit 4096)
    response = f"📋 <b>Foydalanuvchilar ro'yxati</b> ({total} ta)\n\n"
    current_length = len(response)

    for user_info in user_list:
        if current_length + len(user_info) > 4000:  # Yangi xabar
            await message.answer(response, parse_mode="HTML")
            response = ""
            current_length = 0

        response += user_info + "\n"
        current_length += len(user_info) + 1

    if response.strip():
        await message.answer(response, parse_mode="HTML")
