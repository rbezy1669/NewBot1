"""
Обновленный Telegram Bot для платформы Энергосбыт
Современный функционал с интеграцией Mini App, улучшенными командами и полным API взаимодействием
"""

import logging
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests
from urllib.parse import quote

from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
CLIENT_ID = os.getenv('GOSUSLUGI_CLIENT_ID', '')
REDIRECT_URI = os.getenv('REDIRECT_URI', f'{API_BASE_URL}/callback')

# Состояния разговора
READING_INPUT, METER_TYPE_SELECT, READING_CONFIRM = range(3)
SERVICE_TYPE_SELECT, SERVICE_DETAILS = range(3, 5)

class EnergyBot:
    """Основной класс бота энергосбыта"""
    
    def __init__(self):
        self.application = None
        self.user_sessions = {}
        
    async def initialize(self):
        """Инициализация бота"""
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")
            
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Установка команд бота
        await self.set_bot_commands()
        
        # Регистрация обработчиков
        self.register_handlers()
        
        logger.info("Бот инициализирован успешно")
    
    async def set_bot_commands(self):
        """Установка меню команд бота"""
        commands = [
            BotCommand("start", "Запуск и главное меню"),
            BotCommand("miniapp", "Открыть Mini App"),
            BotCommand("readings", "Передать показания"),
            BotCommand("history", "История показаний"),
            BotCommand("services", "Заказать услуги"),
            BotCommand("profile", "Мой профиль"),
            BotCommand("support", "Поддержка и контакты"),
            BotCommand("help", "Помощь по командам"),
        ]
        
        await self.application.bot.set_my_commands(commands)
    
    def register_handlers(self):
        """Регистрация всех обработчиков"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("miniapp", self.miniapp_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("services", self.services_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # Диалог передачи показаний
        reading_conv = ConversationHandler(
            entry_points=[CommandHandler("readings", self.readings_start)],
            states={
                METER_TYPE_SELECT: [CallbackQueryHandler(self.meter_type_selected)],
                READING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reading_input)],
                READING_CONFIRM: [CallbackQueryHandler(self.reading_confirm)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_operation)]
        )
        self.application.add_handler(reading_conv)
        
        # Диалог заказа услуг
        service_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.service_start, pattern="^service_")],
            states={
                SERVICE_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_details)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_operation)]
        )
        self.application.add_handler(service_conv)
        
        # Callback обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)

MAIN_KEYBOARD = [
    [KeyboardButton("📱 Открыть личный кабинет", web_app=WebAppInfo(url="https://new-bot1-murex.vercel.app"))],
    ["📊 Передать показания", "📈 История показаний"],
    ["🔧 Замена счётчиков", "📞 Связаться с поддержкой"]
]
MAIN_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

MAIN_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

# URL Mini App (замените на ваш домен)
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://new-bot1-murex.vercel.app')

CANCEL_KEYBOARD = [['❌ Отмена']]
CANCEL_MARKUP = ReplyKeyboardMarkup(CANCEL_KEYBOARD, resize_keyboard=True)

REPLACEMENT_KEYBOARD = [
    ['Однофазный счётчик', 'Трёхфазный счётчик'],
    ['Узнать стоимость', '❌ Отмена']
]
REPLACEMENT_MARKUP = ReplyKeyboardMarkup(REPLACEMENT_KEYBOARD, resize_keyboard=True)


class DatabaseManager:
    """Менеджер базы данных для бота"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                gosuslugi_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица показаний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                reading_value INTEGER,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Таблица заявок на замену
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replacement_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                meter_type TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, telegram_id: int, username: str = None, full_name: str = None):
        """Добавление пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
        ''', (telegram_id, username, full_name))
        conn.commit()
        conn.close()
    
    def add_reading(self, telegram_id: int, reading_value: int):
        """Добавление показания"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO readings (telegram_id, reading_value)
            VALUES (?, ?)
        ''', (telegram_id, reading_value))
        conn.commit()
        conn.close()
    
    def get_readings_history(self, telegram_id: int, limit: int = 10):
        """Получение истории показаний"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT reading_value, submission_date
            FROM readings
            WHERE telegram_id = ?
            ORDER BY submission_date DESC
            LIMIT ?
        ''', (telegram_id, limit))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def add_replacement_request(self, telegram_id: int, meter_type: str):
        """Добавление заявки на замену"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO replacement_requests (telegram_id, meter_type)
            VALUES (?, ?)
        ''', (telegram_id, meter_type))
        conn.commit()
        conn.close()


# Инициализация менеджера БД
db = DatabaseManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.full_name)
    
    welcome_text = f"""
👋 Добро пожаловать, {user.first_name}!

Я бот службы Энергосбыт. Используйте личный кабинет для удобного управления вашими услугами:

📱 Личный кабинет - полнофункциональное приложение
📊 Быстрая передача показаний через бота
📞 Круглосуточная поддержка

Выберите действие на клавиатуре ниже.
    """
    
    await update.message.reply_text(welcome_text, reply_markup=MAIN_MARKUP)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 Справка по боту Энергосбыт

Доступные команды:
• /start - Главное меню
• /help - Эта справка
• /status - Статус ваших заявок

📊 Передача показаний:
Отправьте текущие показания вашего счётчика

📈 История показаний:
Просмотр последних переданных показаний

🔧 Замена счётчиков:
Оформление заявки на замену или установку

📞 Поддержка:
Контактная информация службы поддержки

🔐 Госуслуги:
Авторизация для расширенных функций
    """
    await update.message.reply_text(help_text, reply_markup=MAIN_MARKUP)


async def start_reading_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало ввода показаний"""
    await update.message.reply_text(
        "📊 Передача показаний счётчика\n\n"
        "Введите текущие показания (только цифры):\n"
        "Например: 12345",
        reply_markup=CANCEL_MARKUP
    )
    return READING_INPUT


async def process_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка показаний"""
    user_input = update.message.text.strip()
    
    if not user_input.isdigit():
        await update.message.reply_text(
            "❗ Пожалуйста, введите только цифры.\n"
            "Например: 12345\n\n"
            "Или нажмите '❌ Отмена' для возврата в главное меню."
        )
        return READING_INPUT
    
    reading_value = int(user_input)
    
    # Проверка разумности показаний
    if reading_value < 0 or reading_value > 999999:
        await update.message.reply_text(
            "❗ Показания должны быть от 0 до 999999.\n"
            "Пожалуйста, проверьте и введите корректное значение."
        )
        return READING_INPUT
    
    # Сохранение в базу данных
    telegram_id = update.effective_user.id
    db.add_reading(telegram_id, reading_value)
    
    await update.message.reply_text(
        f"✅ Показания успешно переданы!\n\n"
        f"📊 Значение: {reading_value:,}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Спасибо! Ваши показания обработаны и переданы в биллинговую систему.",
        reply_markup=MAIN_MARKUP
    )
    
    return ConversationHandler.END


async def show_readings_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ истории показаний"""
    telegram_id = update.effective_user.id
    history = db.get_readings_history(telegram_id)
    
    if not history:
        await update.message.reply_text(
            "📈 История показаний пуста\n\n"
            "Вы ещё не передавали показания через этот бот.\n"
            "Воспользуйтесь кнопкой '📊 Передать показания' для отправки текущих значений.",
            reply_markup=MAIN_MARKUP
        )
        return
    
    history_text = "📈 История ваших показаний:\n\n"
    
    for reading, date_str in history:
        # Парсим дату из строки
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%d.%m.%Y %H:%M')
        except:
            formatted_date = date_str
            
        history_text += f"📊 {reading:,} — {formatted_date}\n"
    
    history_text += f"\n📋 Показано последних записей: {len(history)}"
    
    await update.message.reply_text(history_text, reply_markup=MAIN_MARKUP)


async def start_meter_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса замены счётчика"""
    replacement_text = """
🔧 Замена счётчиков

Мы предоставляем услуги по замене и установке электросчётчиков:

• Однофазные счётчики (для квартир)
• Трёхфазные счётчики (для частных домов)

Выберите тип счётчика или узнайте стоимость услуг:
    """
    
    await update.message.reply_text(
        replacement_text,
        reply_markup=REPLACEMENT_MARKUP
    )
    return REPLACEMENT_DETAILS


async def process_replacement_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка заявки на замену"""
    user_choice = update.message.text
    telegram_id = update.effective_user.id
    
    if user_choice in ['Однофазный счётчик', 'Трёхфазный счётчик']:
        meter_type = 'single_phase' if 'Однофазный' in user_choice else 'three_phase'
        db.add_replacement_request(telegram_id, meter_type)
        
        response_text = f"""
✅ Заявка на замену принята!

🔧 Тип счётчика: {user_choice}
📅 Дата заявки: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📞 С вами свяжется наш специалист в течение 24 часов для согласования:
• Удобного времени визита
• Точной стоимости услуг
• Технических деталей

Контакты для срочных вопросов:
📱 +7 (800) 555-0123
        """
        
        await update.message.reply_text(response_text, reply_markup=MAIN_MARKUP)
        return ConversationHandler.END
        
    elif user_choice == 'Узнать стоимость':
        pricing_text = """
💰 Стоимость услуг по замене счётчиков:

🏠 Однофазный счётчик:
• Счётчик + установка: от 3,500 ₽
• Только установка: от 1,200 ₽

🏭 Трёхфазный счётчик:
• Счётчик + установка: от 8,500 ₽  
• Только установка: от 2,500 ₽

📋 В стоимость входит:
✓ Демонтаж старого счётчика
✓ Установка и подключение нового
✓ Настройка и проверка
✓ Оформление документов
✓ Гарантия 12 месяцев

💡 Дополнительные услуги:
• Замена автоматов: от 500 ₽
• Прокладка кабеля: от 150 ₽/м
• Выезд в выходные: +500 ₽

Для точного расчёта оставьте заявку!
        """
        
        await update.message.reply_text(pricing_text, reply_markup=REPLACEMENT_MARKUP)
        return REPLACEMENT_DETAILS


async def show_support_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ контактной информации"""
    support_text = """
📞 Служба поддержки Энергосбыт

🕐 Часы работы:
Пн-Пт: 08:00 - 20:00
Сб-Вс: 09:00 - 18:00

📱 Телефоны:
• Общие вопросы: +7 (800) 555-0123
• Аварийная служба: +7 (800) 555-0911
• Коммерческая служба: +7 (800) 555-0456

📧 Email:
• info@energosbyt.ru
• support@energosbyt.ru

🌐 Сайт: www.energosbyt.ru

📍 Офисы обслуживания:
• ул. Энергетиков, 15 (центр города)
• пр. Советский, 89 (северный район)
• ул. Мира, 234 (южный район)

⚡ Аварийные ситуации:
Звоните 112 или +7 (800) 555-0911
(круглосуточно, бесплатно)
    """
    
    await update.message.reply_text(support_text, reply_markup=MAIN_MARKUP)


async def open_mini_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открытие Mini App в Telegram"""
    mini_app_text = """
📱 Личный кабинет Энергосбыт

Откройте полнофункциональный личный кабинет прямо в Telegram:

🏠 Управление лицевыми счетами
📊 Передача показаний счётчиков
📈 История потребления и платежей
🔧 Заказ услуг и консультаций
📞 Связь с поддержкой

Нажмите кнопку ниже для запуска приложения:
    """
    
    keyboard = [[InlineKeyboardButton("📱 Открыть личный кабинет", web_app={"url": MINI_APP_URL})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        mini_app_text,
        reply_markup=reply_markup
    )


import json

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных, отправленных из Telegram WebApp"""
    try:
        data = json.loads(update.effective_message.web_app_data.data)

        if data.get("action") == "support_request":
            user_id = data.get("user_id")
            name = data.get("name")
            timestamp = data.get("timestamp")

            logger.info(f"📥 Обращение в ТП от {name} (ID: {user_id}), время: {timestamp}")

            await update.message.reply_text(
                "✅ Ваше обращение принято! С вами свяжется оператор при необходимости.",
                reply_markup=MAIN_MARKUP
            )
        else:
            await update.message.reply_text("⚠️ Неизвестное действие от WebApp.", reply_markup=MAIN_MARKUP)

    except Exception as e:
        logger.error(f"❌ Ошибка обработки web_app_data: {e}")
        await update.message.reply_text("❌ Ошибка при обработке обращения.", reply_markup=MAIN_MARKUP)


async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    await update.message.reply_text(
        "❌ Операция отменена.\n\nВы вернулись в главное меню.",
        reply_markup=MAIN_MARKUP
    )
    return ConversationHandler.END


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных сообщений"""
    await update.message.reply_text(
        "🤔 Я не понимаю это сообщение.\n\n"
        "Пожалуйста, используйте кнопки меню или команды:\n"
        "• /start - Главное меню\n"
        "• /help - Справка",
        reply_markup=MAIN_MARKUP
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "😔 Произошла техническая ошибка.\n\n"
            "Попробуйте повторить операцию или обратитесь в службу поддержки.",
            reply_markup=MAIN_MARKUP
        )



def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        print("⚠️ BOT_TOKEN не установлен. Бот не может быть запущен.")
        print("Установите переменную окружения BOT_TOKEN для запуска бота.")
        return
    
    
    # Создание приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Обработчик передачи показаний
    readings_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📊 Передать показания$'), start_reading_input)],
        states={
            READING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reading)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_operation)],
    )
    app.add_handler(readings_conv)
    
    # Обработчик замены счётчиков
    replacement_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔧 Замена счётчиков$'), start_meter_replacement)],
        states={
            REPLACEMENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_replacement_request)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_operation)],
    )
    app.add_handler(replacement_conv)
    
    # Простые обработчики
    app.add_handler(MessageHandler(filters.Regex('^📱 Открыть личный кабинет$'), open_mini_app))
    app.add_handler(MessageHandler(filters.Regex('^📈 История показаний$'), show_readings_history))
    app.add_handler(MessageHandler(filters.Regex('^📞 Связаться с поддержкой$'), show_support_contacts))
    
    # Обработчик неизвестных сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    logger.info("🤖 Бот Энергосбыт запущен...")
    print("🤖 Бот Энергосбыт запущен и готов к работе!")
    
    # Запуск бота
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.run_polling(drop_pending_updates=True)
    

if __name__ == "__main__":
    main()
