# Telegram Service Bot with Gosuslugi OAuth placeholder and extended menu
# Note: OAuth requires a backend web server to handle redirects
# This bot only demonstrates simulated OAuth flow and menu expansion

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import urllib.parse

BOT_TOKEN = '7807810519:AAFg7_mETm_HTjhzwCvKPhzdZLawytSCtOc'
CLIENT_ID = 'ВАШ_CLIENT_ID_ОТ_ГОСУСЛУГ'
REDIRECT_URI = 'https://yourdomain.ru/callback'  # Ваш backend должен обрабатывать эту ссылку
AUTH_URL = (
    'https://esia.gosuslugi.ru/aas/oauth2/ac'
    f'?client_id={urllib.parse.quote(CLIENT_ID)}'
    '&scope=openid&response_type=code'
    f'&redirect_uri={urllib.parse.quote(REDIRECT_URI)}'
)

# ──────────────── UI MARKUPS ────────────────
MAIN_KEYBOARD = [
    ['🔐 Войти через Госуслуги'],
    ['Передать показания', 'История показаний'],
    ['Замена счётчиков', 'Связаться с поддержкой'],
]
MAIN_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

CANCEL_KEYBOARD = [['Отмена']]
CANCEL_MARKUP = ReplyKeyboardMarkup(CANCEL_KEYBOARD, resize_keyboard=True)

# ──────────────── STATES ────────────────
READING = 1

# ──────────────── HANDLERS ────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет! Я бот службы учёта. Выберите действие:',
        reply_markup=MAIN_MARKUP,
    )

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
    keyboard = [[InlineKeyboardButton("Перейти к авторизации", url=AUTH_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Для авторизации через Госуслуги нажмите кнопку ниже:',
        reply_markup=reply_markup
    )

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '☎️ Поддержка: +372 600‑1234\n📧 support@example.com\n⌚ 09:00‑17:00 (пн‑пт)',
        reply_markup=MAIN_MARKUP,
    )

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Введите текущие показания счётчика (только цифры):',
        reply_markup=CANCEL_MARKUP,
    )
    return READING

async def save_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if not value.isdigit():
        await update.message.reply_text('❗ Пожалуйста, отправьте только цифры или нажмите «Отмена».')
        return READING

    await update.message.reply_text(
        f'✅ Спасибо! Показания ({value}) сохранены.',
        reply_markup=MAIN_MARKUP,
    )
    return ConversationHandler.END

async def cancel_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Операция отменена.', reply_markup=MAIN_MARKUP)
    return ConversationHandler.END

async def meter_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔧 Замена счётчиков:\n1. Позвоните: +372 600‑5678\n2. Согласуйте дату\n3. Специалист приедет к вам',
        reply_markup=MAIN_MARKUP,
    )

async def history_readings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📊 История показаний (пример):\n• 01.06.2025 — 1285\n• 01.05.2025 — 1240\n• 01.04.2025 — 1192',
        reply_markup=MAIN_MARKUP,
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Выберите действие на клавиатуре ниже.', reply_markup=MAIN_MARKUP)

# ──────────────── INIT ────────────────
if __name__ == '__main__':
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
