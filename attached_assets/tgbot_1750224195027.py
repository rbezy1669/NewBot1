# Telegram Service Bot with navigation buttons (contact support, submit readings, meter replacement)
# Requires: python-telegram-bot >=20.0
# Install: pip install python-telegram-bot --upgrade

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = '7807810519:AAFg7_mETm_HTjhzwCvKPhzdZLawytSCtOc'  

# ──────────────── UI MARKUPS ────────────────
MAIN_KEYBOARD = [
    ['Замена счётчиков'],
    ['Передать показания'],
    ['Связаться с поддержкой'],
]
MAIN_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

CANCEL_KEYBOARD = [['Отмена']]
CANCEL_MARKUP = ReplyKeyboardMarkup(CANCEL_KEYBOARD, resize_keyboard=True)

# Conversation state
READING = 1

# ──────────────── HANDLERS ────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start command"""
    await update.message.reply_text(
        'Привет! Я бот службы учёта. Выберите действие на клавиатуре ниже.',
        reply_markup=MAIN_MARKUP,
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Навигация:\n'
        '• Связаться с поддержкой — получить контакты.\n'
        '• Передать показания — отправить текущие показания счётчика.\n'
        '• Замена счётчиков — узнать, как заказать замену.',
        reply_markup=MAIN_MARKUP,
    )

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '☎️ Телефон поддержки: +372 600‑1234\n'
        '📧 E‑mail: support@example.com\n'
        '⌚ Время работы: 09:00‑17:00 (пн‑пт)',
        reply_markup=MAIN_MARKUP,
    )

# ── «Передать показания» conversation ──
async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Введите текущие показания счётчика (только цифрами).',
        reply_markup=CANCEL_MARKUP,
    )
    return READING

async def save_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if not value.isdigit():
        await update.message.reply_text('❗ Пожалуйста, отправьте только цифры или нажмите «Отмена».')
        return READING

    # Здесь можно добавить логику сохранения значения в БД или отправки API
    await update.message.reply_text(
        f'✅ Спасибо! Ваши показания ({value}) переданы.',
        reply_markup=MAIN_MARKUP,
    )
    return ConversationHandler.END

async def cancel_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Операция отменена.', reply_markup=MAIN_MARKUP)
    return ConversationHandler.END

async def meter_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔧 Замена счётчиков:\n'
        '1. Позвоните по телефону +372 600‑5678, чтобы согласовать дату.\n'
        '2. Наш специалист приедет и произведёт замену.\n'
        '3. Стоимость услуги зависит от типа счётчика.',
        reply_markup=MAIN_MARKUP,
    )

# ──────────────── APP INITIALISATION ────────────────
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))

    # Conversation for readings
    readings_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Передать показания$'), start_reading)],
        states={
            READING: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reading)],
        },
        fallbacks=[MessageHandler(filters.Regex('^Отмена$'), cancel_reading)],
    )
    app.add_handler(readings_conv)

    # Other navigation buttons
    app.add_handler(MessageHandler(filters.Regex('^Связаться с поддержкой$'), contact_support))
    app.add_handler(MessageHandler(filters.Regex('^Замена счётчиков$'), meter_replacement))

    # Fallback for unknown text
    async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Выберите действие на клавиатуре ниже.', reply_markup=MAIN_MARKUP)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    print('🤖 Бот запущен...')
    app.run_polling()