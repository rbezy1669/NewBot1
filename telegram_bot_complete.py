"""
Полный Telegram бот для службы Энергосбыт с PostgreSQL и Mini App
Все функции в одном файле для простого развёртывания
"""

import os
import json
import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Telegram imports
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes

# FastAPI imports for web server
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

# PostgreSQL imports
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# НАСТРОЙКИ И КОНФИГУРАЦИЯ
# =============================================================================

# Telegram Bot Token - замените на свой
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# URL Mini App - замените на свой домен
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://your-replit-url.replit.app')

# PostgreSQL настройки
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/energybot')

# OAuth настройки для Госуслуг
GOSUSLUGI_CLIENT_ID = os.getenv('GOSUSLUGI_CLIENT_ID', 'test_client_id')
GOSUSLUGI_CLIENT_SECRET = os.getenv('GOSUSLUGI_CLIENT_SECRET', 'test_client_secret')
REDIRECT_URI = os.getenv('REDIRECT_URI', f'{MINI_APP_URL}/oauth/callback')

# Состояния для ConversationHandler
WAITING_READING, WAITING_REPLACEMENT_TYPE = range(2)

# =============================================================================
# МОДЕЛИ БАЗЫ ДАННЫХ (SQLAlchemy)
# =============================================================================

Base = declarative_base()

class User(Base):
    """Пользователи системы"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class MeterReading(Base):
    """Показания счетчиков"""
    __tablename__ = 'meter_readings'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    reading_value = Column(Integer, nullable=False)
    meter_type = Column(String, default='electric')
    submission_method = Column(String, default='bot')
    status = Column(String, default='submitted')
    reading_date = Column(DateTime, default=func.now())

class ServiceRequest(Base):
    """Заявки на услуги"""
    __tablename__ = 'service_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    service_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default='new')
    created_at = Column(DateTime, default=func.now())

class EmailSubscription(Base):
    """Email подписки"""
    __tablename__ = 'email_subscriptions'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

# Database engine and session
engine = create_engine(DATABASE_URL) if DATABASE_URL.startswith('postgresql') else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

def create_tables():
    """Создание всех таблиц"""
    if engine:
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL tables created")

def get_db():
    """Получение сессии базы данных"""
    if SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

# =============================================================================
# МЕНЕДЖЕР БАЗЫ ДАННЫХ
# =============================================================================

class DatabaseManager:
    """Менеджер базы данных с поддержкой SQLite для fallback"""
    
    def __init__(self):
        self.use_postgres = engine is not None
        if not self.use_postgres:
            # Fallback to SQLite
            self.db_path = "energybot.db"
            self.init_sqlite()
    
    def init_sqlite(self):
        """Инициализация SQLite как fallback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meter_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                reading_value INTEGER NOT NULL,
                meter_type TEXT DEFAULT 'electric',
                submission_method TEXT DEFAULT 'bot',
                status TEXT DEFAULT 'submitted',
                reading_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                service_type TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")
    
    def add_user(self, telegram_id: str, username: str = None, full_name: str = None):
        """Добавление пользователя"""
        if self.use_postgres and SessionLocal:
            db = SessionLocal()
            try:
                existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if existing_user:
                    return existing_user
                
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
            finally:
                db.close()
        else:
            # SQLite fallback
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username, full_name)
                VALUES (?, ?, ?)
            ''', (telegram_id, username, full_name))
            conn.commit()
            conn.close()
    
    def add_reading(self, user_id: str, reading_value: int, method: str = 'bot'):
        """Добавление показания"""
        if self.use_postgres and SessionLocal:
            db = SessionLocal()
            try:
                reading = MeterReading(
                    user_id=user_id,
                    reading_value=reading_value,
                    submission_method=method
                )
                db.add(reading)
                db.commit()
                db.refresh(reading)
                return reading
            finally:
                db.close()
        else:
            # SQLite fallback
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO meter_readings (user_id, reading_value, submission_method)
                VALUES (?, ?, ?)
            ''', (user_id, reading_value, method))
            conn.commit()
            conn.close()
    
    def get_readings_history(self, user_id: str, limit: int = 10):
        """Получение истории показаний"""
        if self.use_postgres and SessionLocal:
            db = SessionLocal()
            try:
                readings = db.query(MeterReading).filter(
                    MeterReading.user_id == user_id
                ).order_by(MeterReading.reading_date.desc()).limit(limit).all()
                return readings
            finally:
                db.close()
        else:
            # SQLite fallback
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT reading_value, reading_date, submission_method, status
                FROM meter_readings WHERE user_id = ?
                ORDER BY reading_date DESC LIMIT ?
            ''', (user_id, limit))
            readings = cursor.fetchall()
            conn.close()
            return readings
    
    def add_service_request(self, user_id: str, service_type: str, description: str = None):
        """Добавление заявки на услугу"""
        if self.use_postgres and SessionLocal:
            db = SessionLocal()
            try:
                request = ServiceRequest(
                    user_id=user_id,
                    service_type=service_type,
                    description=description
                )
                db.add(request)
                db.commit()
                db.refresh(request)
                return request
            finally:
                db.close()
        else:
            # SQLite fallback
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO service_requests (user_id, service_type, description)
                VALUES (?, ?, ?)
            ''', (user_id, service_type, description))
            conn.commit()
            conn.close()

# Глобальный экземпляр менеджера БД
db = DatabaseManager()

# =============================================================================
# КЛАВИАТУРЫ TELEGRAM
# =============================================================================

# Главная клавиатура
MAIN_KEYBOARD = [
    ['📱 Открыть личный кабинет'],
    ['📊 Передать показания', '📈 История показаний'],
    ['🔧 Замена счётчика', '📞 Поддержка']
]

MAIN_MARKUP = ReplyKeyboardMarkup(
    MAIN_KEYBOARD,
    resize_keyboard=True,
    one_time_keyboard=False
)

# Клавиатура отмены
CANCEL_KEYBOARD = [['❌ Отмена']]
CANCEL_MARKUP = ReplyKeyboardMarkup(CANCEL_KEYBOARD, resize_keyboard=True)

# Клавиатура типов счётчиков
METER_TYPES_KEYBOARD = [
    ['Электрический счётчик'],
    ['Газовый счётчик'],
    ['Счётчик воды'],
    ['❌ Отмена']
]

METER_TYPES_MARKUP = ReplyKeyboardMarkup(
    METER_TYPES_KEYBOARD,
    resize_keyboard=True,
    one_time_keyboard=True
)

# =============================================================================
# TELEGRAM BOT HANDLERS
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    db.add_user(str(user.id), user.username, user.full_name)
    
    welcome_text = f"""
👋 Добро пожаловать, {user.first_name}!

Я бот службы Энергосбыт с личным кабинетом прямо в Telegram:

📱 Личный кабинет - полнофункциональное приложение
📊 Быстрая передача показаний через бота
📞 Круглосуточная поддержка

Выберите действие на клавиатуре ниже.
    """
    
    await update.message.reply_text(welcome_text, reply_markup=MAIN_MARKUP)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 Энергосбыт Бот - Справка

Доступные функции:

📱 Личный кабинет
   Полнофункциональное приложение в Telegram

📊 Передать показания
   Быстрая передача показаний счётчиков

📈 История показаний
   Просмотр последних 10 показаний

🔧 Замена счётчика
   Заявка на замену или поверку счётчика

📞 Поддержка
   Контакты службы поддержки

Команды:
/start - Начать работу с ботом
/help - Показать эту справку
    """
    
    await update.message.reply_text(help_text, reply_markup=MAIN_MARKUP)

async def open_mini_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открытие Mini App"""
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
    
    webapp = WebAppInfo(url=MINI_APP_URL)
    keyboard = [[InlineKeyboardButton("📱 Открыть личный кабинет", web_app=webapp)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(mini_app_text, reply_markup=reply_markup)

async def start_reading_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало ввода показаний"""
    await update.message.reply_text(
        "📊 Передача показаний счётчика\n\n"
        "Введите текущие показания вашего счётчика (только цифры):",
        reply_markup=CANCEL_MARKUP
    )
    return WAITING_READING

async def process_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка показаний"""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Передача показаний отменена",
            reply_markup=MAIN_MARKUP
        )
        return ConversationHandler.END
    
    try:
        reading_value = int(text)
        if reading_value < 0:
            await update.message.reply_text(
                "⚠️ Показания не могут быть отрицательными. Попробуйте ещё раз:"
            )
            return WAITING_READING
        
        user_id = str(update.effective_user.id)
        db.add_reading(user_id, reading_value, 'bot')
        
        await update.message.reply_text(
            f"✅ Показания {reading_value} кВт⋅ч успешно переданы!\n\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"🔄 Статус: Принято к обработке\n\n"
            f"Спасибо за своевременную передачу показаний!",
            reply_markup=MAIN_MARKUP
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите только цифры (например: 12345):"
        )
        return WAITING_READING

async def show_readings_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ истории показаний"""
    user_id = str(update.effective_user.id)
    readings = db.get_readings_history(user_id, 10)
    
    if not readings:
        await update.message.reply_text(
            "📈 История показаний пуста\n\n"
            "Вы ещё не передавали показания через этого бота.",
            reply_markup=MAIN_MARKUP
        )
        return
    
    history_text = "📈 История ваших показаний:\n\n"
    
    if db.use_postgres:
        for i, reading in enumerate(readings, 1):
            date_str = reading.reading_date.strftime('%d.%m.%Y %H:%M')
            history_text += f"{i}. {reading.reading_value} кВт⋅ч - {date_str}\n"
    else:
        for i, reading in enumerate(readings, 1):
            history_text += f"{i}. {reading[0]} кВт⋅ч - {reading[1][:16]}\n"
    
    history_text += "\n💡 Для передачи новых показаний используйте кнопку '📊 Передать показания'"
    
    await update.message.reply_text(history_text, reply_markup=MAIN_MARKUP)

async def start_meter_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса замены счётчика"""
    await update.message.reply_text(
        "🔧 Заявка на замену счётчика\n\n"
        "Выберите тип счётчика для замены:",
        reply_markup=METER_TYPES_MARKUP
    )
    return WAITING_REPLACEMENT_TYPE

async def process_replacement_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка заявки на замену"""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Заявка отменена",
            reply_markup=MAIN_MARKUP
        )
        return ConversationHandler.END
    
    meter_types = {
        'Электрический счётчик': 'electric',
        'Газовый счётчик': 'gas',
        'Счётчик воды': 'water'
    }
    
    if text in meter_types:
        user_id = str(update.effective_user.id)
        service_type = f"meter_replacement_{meter_types[text]}"
        description = f"Заявка на замену: {text}"
        
        db.add_service_request(user_id, service_type, description)
        
        await update.message.reply_text(
            f"✅ Заявка на замену '{text}' принята!\n\n"
            f"📋 Номер заявки: #{datetime.now().strftime('%Y%m%d%H%M%S')}\n"
            f"📅 Дата подачи: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"⏱️ Срок рассмотрения: 3-5 рабочих дней\n\n"
            f"Наш специалист свяжется с вами для согласования времени замены.\n\n"
            f"📞 Вопросы? Обращайтесь в поддержку!",
            reply_markup=MAIN_MARKUP
        )
        
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "⚠️ Пожалуйста, выберите тип счётчика из предложенных вариантов:"
        )
        return WAITING_REPLACEMENT_TYPE

async def show_support_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ контактной информации"""
    support_text = """
📞 Служба поддержки Энергосбыт

🕐 Режим работы:
Пн-Пт: 8:00 - 20:00
Сб-Вс: 9:00 - 18:00

📱 Телефоны:
• Горячая линия: 8-800-xxx-xx-xx
• Аварийная служба: 8-xxx-xxx-xx-xx (круглосуточно)
• WhatsApp: +7-xxx-xxx-xx-xx

📧 Email: support@energosbyt.ru

🏢 Офисы обслуживания:
• ул. Ленина, 123 (Пн-Пт 9:00-18:00)
• ул. Советская, 456 (Пн-Пт 8:00-17:00)

💬 Онлайн-чат на сайте: energosbyt.ru

Мы всегда готовы помочь! 🤝
    """
    
    await update.message.reply_text(support_text, reply_markup=MAIN_MARKUP)

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    await update.message.reply_text(
        "❌ Операция отменена",
        reply_markup=MAIN_MARKUP
    )
    return ConversationHandler.END

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных сообщений"""
    await update.message.reply_text(
        "🤔 Извините, я не понимаю эту команду.\n\n"
        "Используйте кнопки меню или команду /help для получения справки.",
        reply_markup=MAIN_MARKUP
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f'Update {update} caused error {context.error}')
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😞 Произошла техническая ошибка.\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=MAIN_MARKUP
        )

# =============================================================================
# FASTAPI WEB SERVER ДЛЯ MINI APP
# =============================================================================

# Pydantic модели
class ReadingSubmissionAPI(BaseModel):
    telegram_id: int
    reading_value: int
    meter_type: Optional[str] = 'electric'

class ServiceRequestAPI(BaseModel):
    telegram_id: int
    service_type: str
    description: Optional[str] = None

# FastAPI приложение
app = FastAPI(title="Энергосбыт Mini App API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте"""
    if engine:
        create_tables()
    logger.info("Web server started")

@app.get("/")
async def root():
    """Главная страница - Mini App"""
    return RedirectResponse(url="/index.html")

@app.post("/api/readings")
async def submit_reading_api(submission: ReadingSubmissionAPI):
    """API для передачи показаний от Mini App"""
    try:
        db.add_reading(
            str(submission.telegram_id),
            submission.reading_value,
            'mini_app'
        )
        
        logger.info(f"Reading submitted via API: user {submission.telegram_id}, value {submission.reading_value}")
        
        return {
            "status": "success",
            "message": "Показания успешно переданы",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"API reading submission error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения показаний")

@app.get("/api/readings/{telegram_id}")
async def get_readings_api(telegram_id: str):
    """API для получения истории показаний"""
    try:
        readings = db.get_readings_history(telegram_id, 12)
        
        result = []
        if db.use_postgres:
            for reading in readings:
                result.append({
                    "id": reading.id,
                    "value": reading.reading_value,
                    "date": reading.reading_date.isoformat(),
                    "method": reading.submission_method,
                    "status": reading.status
                })
        else:
            for i, reading in enumerate(readings):
                result.append({
                    "id": i + 1,
                    "value": reading[0],
                    "date": reading[1],
                    "method": reading[2] if len(reading) > 2 else 'bot',
                    "status": reading[3] if len(reading) > 3 else 'submitted'
                })
        
        return result
        
    except Exception as e:
        logger.error(f"API readings history error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")

@app.post("/api/service-requests")
async def create_service_request_api(request: ServiceRequestAPI):
    """API для создания заявки на услугу"""
    try:
        db.add_service_request(
            str(request.telegram_id),
            request.service_type,
            request.description
        )
        
        return {
            "status": "success",
            "message": "Заявка создана успешно",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"API service request error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания заявки")

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "postgresql" if db.use_postgres else "sqlite"
    }

# Статические файлы будут обслуживаться отдельно

# =============================================================================
# MAIN - ЗАПУСК БОТА И WEB СЕРВЕРА
# =============================================================================

async def run_bot():
    """Запуск Telegram бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # ConversationHandler для ввода показаний
    reading_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📊 Передать показания$'), start_reading_input)],
        states={
            WAITING_READING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reading)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_operation)],
    )
    
    # ConversationHandler для замены счётчика
    replacement_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔧 Замена счётчика$'), start_meter_replacement)],
        states={
            WAITING_REPLACEMENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_replacement_request)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_operation)],
    )
    
    application.add_handler(reading_conv)
    application.add_handler(replacement_conv)
    
    # Простые обработчики
    application.add_handler(MessageHandler(filters.Regex('^📱 Открыть личный кабинет$'), open_mini_app))
    application.add_handler(MessageHandler(filters.Regex('^📈 История показаний$'), show_readings_history))
    application.add_handler(MessageHandler(filters.Regex('^📞 Поддержка$'), show_support_contacts))
    
    # Обработчик неизвестных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("Starting Telegram bot...")
    await application.run_polling(drop_pending_updates=True)

def run_web_server():
    """Запуск веб-сервера"""
    logger.info("Starting web server on port 5000...")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "bot":
            # Запуск только бота
            asyncio.run(run_bot())
        elif sys.argv[1] == "web":
            # Запуск только веб-сервера
            run_web_server()
        else:
            print("Usage: python telegram_bot_complete.py [bot|web]")
    else:
        print("Telegram Bot for Энергосбыт")
        print("Usage:")
        print("  python telegram_bot_complete.py bot  - Run only Telegram bot")
        print("  python telegram_bot_complete.py web  - Run only web server")
        print()
        print("Configuration required:")
        print("  BOT_TOKEN - Your Telegram bot token")
        print("  MINI_APP_URL - Your Mini App URL")
        print("  DATABASE_URL - PostgreSQL connection string (optional, SQLite fallback)")