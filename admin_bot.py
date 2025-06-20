import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "admin"])
async def start_admin(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await message.reply("❌ Доступ запрещен.")
        return
    await message.reply("🤖 Панель администратора активна. Команды:\n" +
                        "/last — последние 5 входов\n" +
                        "/logins — последние 100 логов\n" +
                        "/users — список пользователей")

@dp.message_handler(commands=["last"])
async def get_last_logins(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, platform, ip, geo, timestamp FROM logins ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    text = "\n\n".join([f"👤 @{r[0]} | {r[1]} | {r[2]}\n🌍 {r[3]}\n🕒 {r[4]}" for r in rows])
    await message.reply("🕵️‍♂️ Последние входы:\n\n" + text)

@dp.message_handler(commands=["logins"])
async def get_all_logins(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT username, ip, timestamp FROM logins ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    text = "\n".join([f"@{r[0]} | {r[1]} | {r[2]}" for r in rows])
    await message.reply("📋 Лог входов:\n\n" + text[:4096])

@dp.message_handler(commands=["users"])
async def unique_users(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("analytics.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id, username FROM logins")
    users = c.fetchall()
    conn.close()
    text = "\n".join([f"<b>{u[1]}</b> — {u[0]}" for u in users])
    await message.reply(f"👥 Уникальных пользователей: {len(users)}\n\n" + text[:4096])

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
