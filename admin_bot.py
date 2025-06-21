import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import CommandObject

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(
    parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Команды администратора


@router.message(F.text.in_(["/start", "/admin"]))
async def start_admin(message: types.Message):
    print(f"📩 Команда: {message.text} от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        await message.reply("❌ Доступ запрещён.")
        return
    await message.reply("🤖 Панель администратора активна. Команды:\n" +
                        "/last — последние 5 входов\n" +
                        "/logins — последние 100 логов\n" +
                        "/users — список пользователей\n" +
                        "/whois @username — информация о пользователе")


@router.message(lambda m: m.text and m.text.startswith("/last"))
async def get_last_logins(message: types.Message):
    print(f"📩 Команда: {message.text} от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute(
        "SELECT username, platform, ip, geo, timestamp FROM logins ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.reply("⚠️ Нет данных.")
        return
    text = "\n\n".join(
        [f"👤 @{r[0]} | {r[1]} | {r[2]}\n🌍 {r[3]}\n🕒 {r[4]}" for r in rows])
    await message.reply("🕵️ Последние входы:\n\n" + text)


@router.message(lambda m: m.text and m.text.startswith("/logins"))
async def get_all_logins(message: types.Message):
    print(f"📩 Команда: {message.text} от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute(
        "SELECT username, ip, timestamp FROM logins ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.reply("⚠️ Логов нет.")
        return
    text = "\n".join([f"@{r[0]} | {r[1]} | {r[2]}" for r in rows])
    await message.reply("📋 Лог входов:\n\n" + text[:4096])


@router.message(lambda m: m.text and m.text.startswith("/users"))
async def unique_users(message: types.Message):
    print(f"📩 Команда: {message.text} от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id, username FROM logins")
    users = c.fetchall()
    conn.close()
    if not users:
        await message.reply("👥 Пользователей нет.")
        return
    text = "\n".join([f"<b>{u[1]}</b> — {u[0]}" for u in users])
    await message.reply(f"👥 Уникальных пользователей: {len(users)}\n\n" + text[:4096])


@router.message(F.text.regexp(r"^/whois @?\w+$"))
async def whois_user(message: types.Message):
    print(f"📩 Команда: {message.text} от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        return
    username = message.text.split()[-1].lstrip("@")
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, platform, ip, geo, browser, language, timezone, timestamp FROM logins WHERE username = ? ORDER BY id DESC LIMIT 1", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        await message.reply("❌ Пользователь не найден.")
        return
    user_id, username, full_name, platform, ip, geo, browser, lang, tz, ts = row
    text = f"<b>Информация о @{username}:</b>\n"
    text += f"👤 Имя: {full_name}\n"
    text += f"🆔 ID: <code>{user_id}</code>\n"
    text += f"📱 Платформа: {platform}\n"
    text += f"🌍 Локация: {geo} | {ip}\n"
    text += f"🖥 Браузер: {browser}\n"
    text += f"🌐 Язык: {lang}\n"
    text += f"🕒 Часовой пояс: {tz}\n"
    text += f"📅 Последний вход: {ts}"
    await message.reply(text.strip(), parse_mode="HTML")


@router.message(F.text == "/activity")
async def recent_activity(message: types.Message):
    print(f"📩 Команда: /activity от {message.chat.id}")
    if message.chat.id != ADMIN_CHAT_ID:
        return

    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, full_name, platform, ip, geo, browser, language, timezone, timestamp FROM logins ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await message.reply("⚠️ Нет данных.")
        return

    text = "🧾 <b>Последние действия:</b>\n\n"
    for row in rows:
        username, full_name, platform, ip, geo, browser, lang, tz, ts = row
        text += f"👤 <b>@{username or 'unknown'}</b> ({full_name or '-'})\n"
        text += f"🆔 Платформа: {platform or '—'}\n"
        text += f"🌍 {geo or '—'} | {ip or '—'}\n"
        text += f"🖥 {browser or '—'}\n"
        text += f"🌐 Язык: {lang or '—'}\n"
        text += f"🕒 Часовой пояс: {tz or '—'}\n"
        text += f"📅 {ts}\n\n"

    await message.reply(text.strip(), parse_mode="HTML")


@router.message()
async def fallback_handler(message: types.Message):
    print(
        f"❓ Получено неизвестное сообщение: {message.text} от {message.chat.id}")
    if message.chat.id == ADMIN_CHAT_ID:
        await message.reply("Команда не распознана. Проверьте синтаксис.")

# Основная функция


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
