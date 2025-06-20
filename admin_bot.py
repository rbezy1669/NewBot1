import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Команды администратора
@router.message(F.text.in_(["/start", "/admin"]))
async def start_admin(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await message.reply("❌ Доступ запрещён.")
        return
    await message.reply("🤖 Панель администратора активна. Команды:\n" +
                        "/last — последние 5 входов\n" +
                        "/logins — последние 100 логов\n" +
                        "/users — список пользователей")

@router.message(F.text == "/last")
async def get_last_logins(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, platform, ip, geo, timestamp FROM logins ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.reply("⚠️ Нет данных.")
        return
    text = "\n\n".join([f"👤 @{r[0]} | {r[1]} | {r[2]}\n🌍 {r[3]}\n🕒 {r[4]}" for r in rows])
    await message.reply("🕵️ Последние входы:\n\n" + text)

@router.message(F.text == "/logins")
async def get_all_logins(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, ip, timestamp FROM logins ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.reply("⚠️ Логов нет.")
        return
    text = "\n".join([f"@{r[0]} | {r[1]} | {r[2]}" for r in rows])
    await message.reply("📋 Лог входов:\n\n" + text[:4096])

@router.message(F.text == "/users")
async def unique_users(message: types.Message):
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


@router.message(F.text == "/activity")
async def recent_activity(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, platform, ip, geo, timestamp FROM logins ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await message.reply("⚠️ Нет данных.")
        return

    text = "🧾 <b>Последние действия:</b>\n\n"
    for row in rows:
        username, platform, ip, geo, ts = row
        username_str = f"@{username}" if username else "<i>Без имени</i>"
        platform_str = f"{platform}" if platform and platform != "unknown" else ""
        geo_str = f"{geo}" if geo and geo != "unknown" else ""
        ip_str = f"{ip}" if ip and ip != "unknown" else ""
        time_str = ts if ts else ""

        text += f"👤 {username_str}"
        if platform_str:
            text += f" | {platform_str}"
        if geo_str or ip_str:
            text += f"\n🌍"
            if geo_str:
                text += f" {geo_str}"
            if ip_str:
                text += f" | {ip_str}"
        if time_str:
            text += f"\n🕒 {time_str}"
        text += "\n\n"

    await message.reply(text.strip(), parse_mode="HTML")


# Основная функция
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
