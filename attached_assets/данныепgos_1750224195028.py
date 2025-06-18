# ─────────── BACKEND (FastAPI) ───────────
# Файл: backend.py
# Установить зависимости: pip install fastapi uvicorn requests

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import requests
import sqlite3

app = FastAPI()

CLIENT_ID = 'ВАШ_CLIENT_ID'
CLIENT_SECRET = 'ВАШ_CLIENT_SECRET'
REDIRECT_URI = 'https://yourdomain.ru/callback'
TOKEN_URL = 'https://esia.gosuslugi.ru/aas/oauth2/te'
USERINFO_URL = 'https://esia.gosuslugi.ru/rs/prns'

@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    tg_id = request.query_params.get("state")

    if not code or not tg_id:
        return {"error": "Missing code or Telegram ID (state)"}

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(TOKEN_URL, data=data, headers=headers)

    if token_response.status_code != 200:
        return {"error": "Token exchange failed", "details": token_response.text}

    tokens = token_response.json()
    access_token = tokens.get("access_token")

    user_response = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if user_response.status_code != 200:
        return {"error": "User info request failed", "details": user_response.text}

    user_info = user_response.json()

    # Сохраняем в базу
    conn = sqlite3.connect("auth_users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id TEXT PRIMARY KEY,
            full_name TEXT,
            inn TEXT,
            raw TEXT
        )
    """)
    c.execute("REPLACE INTO users (tg_id, full_name, inn, raw) VALUES (?, ?, ?, ?)", (
        tg_id,
        user_info.get("name", ""),
        user_info.get("inn", ""),
        str(user_info)
    ))
    conn.commit()
    conn.close()

    return RedirectResponse(url=f"https://t.me/YOUR_BOT_USERNAME")

# ─────────── TELEGRAM BOT ───────────
# Файл: bot.py
# Установить зависимости: pip install python-telegram-bot aiosqlite nest_asyncio

import nest_asyncio
nest_asyncio.apply()

import aiosqlite
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import urllib.parse

BOT_TOKEN = '7807810519:AAGlq6BQhrOiLJe1Obl0H0-nKoHk0KLfsmw'
CLIENT_ID = 'ВАШ_CLIENT_ID'
REDIRECT_URI = 'https://yourdomain.ru/callback'
AUTH_URL = (
    'https://esia.gosuslugi.ru/aas/oauth2/ac'
    f'?client_id={urllib.parse.quote(CLIENT_ID)}'
    '&scope=openid&response_type=code'
    f'&redirect_uri={urllib.parse.quote(REDIRECT_URI)}'
)

MAIN_KEYBOARD = [
    ['🔐 Войти через Госуслуги'],
    ['Передать показания', 'История показаний'],
    ['Замена счётчиков', 'Связаться с поддержкой'],
]
MAIN_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
CANCEL_MARKUP = ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
READING = 1

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    async with aiosqlite.connect("auth_users.db") as db:
        async with db.execute("SELECT full_name FROM users WHERE tg_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await update.message.reply_text(f"👋 Добро пожаловать, {row[0]}! Вы успешно авторизовались.", reply_markup=MAIN_MARKUP)
                return
    await update.message.reply_text('Привет! Я бот службы учёта. Выберите действие:', reply_markup=MAIN_MARKUP)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Навигация:\n'
        '• 🔐 Войти через Госуслуги — авторизация\n'
        '• Передать показания — отправить текущие значения\n'
        '• История показаний — просмотр предыдущих\n'
        '• Замена счётчиков — оформить заявку\n'
        '• Связаться с поддержкой — наши контакты',
        reply_markup=MAIN_MARKUP,
    )

async def gosuslugi_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = AUTH_URL + f"&state={user_id}"
    keyboard = [[InlineKeyboardButton("Перейти к авторизации", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Для авторизации через Госуслуги нажмите кнопку ниже:', reply_markup=reply_markup)

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('☎️ Поддержка: +372 600‑1234\n📧 support@example.com\n⌚ 09:00‑17:00 (пн‑пт)', reply_markup=MAIN_MARKUP)

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите текущие показания счётчика (только цифры):', reply_markup=CANCEL_MARKUP)
    return READING

async def save_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if not value.isdigit():
        await update.message.reply_text('❗ Пожалуйста, отправьте только цифры или нажмите «Отмена».')
        return READING
    await update.message.reply_text(f'✅ Спасибо! Показания ({value}) сохранены.', reply_markup=MAIN_MARKUP)
    return ConversationHandler.END

async def cancel_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Операция отменена.', reply_markup=MAIN_MARKUP)
    return ConversationHandler.END

async def meter_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🔧 Замена счётчиков:\n1. Позвоните: +372 600‑5678\n2. Согласуйте дату\n3. Специалист приедет к вам', reply_markup=MAIN_MARKUP)

async def history_readings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📊 История показаний:\n• 01.06.2025 — 1285\n• 01.05.2025 — 1240\n• 01.04.2025 — 1192', reply_markup=MAIN_MARKUP)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Выберите действие на клавиатуре ниже.', reply_markup=MAIN_MARKUP)

if __name__ == '__main__':
    from telegram.ext import ApplicationBuilder
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Передать показания$'), start_reading)],
        states={READING: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reading)]},
        fallbacks=[MessageHandler(filters.Regex('^Отмена$'), cancel_reading)],
    ))
    app.add_handler(MessageHandler(filters.Regex('^Связаться с поддержкой$'), contact_support))
    app.add_handler(MessageHandler(filters.Regex('^Замена счётчиков$'), meter_replacement))
    app.add_handler(MessageHandler(filters.Regex('^История показаний$'), history_readings))
    app.add_handler(MessageHandler(filters.Regex('^🔐 Войти через Госуслуги$'), gosuslugi_login))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    print('🤖 Бот запущен...')
    app.run_polling()