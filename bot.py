"""
Telegram Bot for Russian Energy Platform
Полнофункциональный бот для энергосбыта с Mini App интеграцией
"""

import os
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any

# Telegram imports
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Telegram library import error: {e}")
    TELEGRAM_AVAILABLE = False

# Configuration
BOT_TOKEN = os.getenv('7807810519:AAGlq6BQhrOiLJe1Obl0H0-nKoHk0KLfsmw')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
MINI_APP_URL = f"{API_BASE_URL}/static/index.html"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class EnergyBot:
    """Telegram Bot для платформы энергосбыта"""
    
    def __init__(self):
        """Инициализация бота"""
        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram library не установлена")
            return
            
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не найден в переменных окружения")
            return
            
        # Создание приложения
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.session = None
        
        # Регистрация обработчиков
        self._register_handlers()
        
        logger.info("Бот инициализирован успешно")
    
    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("miniapp", self.miniapp_command))
        self.application.add_handler(CommandHandler("readings", self.readings_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("services", self.services_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Обработчики callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - главное меню"""
        user = update.effective_user
        
        welcome_message = f"""
🏠 Добро пожаловать в энергосбыт, {user.first_name}!

Я помогу вам:
• 📊 Передавать показания счетчиков
• 📈 Просматривать историю потребления
• 🛠 Заказывать услуги
• 💬 Получать поддержку

Выберите действие из меню ниже:
        """
        
        # Создание главного меню
        keyboard = [
            [KeyboardButton("📊 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton("📋 Показания"), KeyboardButton("📈 История")],
            [KeyboardButton("🛠 Услуги"), KeyboardButton("💬 Поддержка")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def miniapp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /miniapp - запуск Mini App"""
        keyboard = [[
            InlineKeyboardButton("🚀 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌟 Откройте полнофункциональное Mini App для удобного управления услугами:",
            reply_markup=reply_markup
        )
    
    async def readings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда передачи показаний"""
        keyboard = [
            [InlineKeyboardButton("⚡ Электричество", callback_data="meter_electric")],
            [InlineKeyboardButton("🔥 Газ", callback_data="meter_gas")],
            [InlineKeyboardButton("💧 Вода", callback_data="meter_water")],
            [InlineKeyboardButton("🚀 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 Выберите тип счетчика для передачи показаний:",
            reply_markup=reply_markup
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда истории показаний"""
        user_id = str(update.effective_user.id)
        
        try:
            history = await self.get_readings_history(user_id)
            
            if not history:
                message = "📈 История показаний пуста.\nПередайте первые показания через Mini App!"
            else:
                message = "📈 Последние показания:\n\n"
                for reading in history[:5]:  # Показываем последние 5
                    date = reading.get('reading_date', 'Неизвестно')[:10]  # Только дата
                    value = reading.get('reading_value', 0)
                    meter_type = reading.get('meter_type', 'electric')
                    icon = self._get_meter_icon(meter_type)
                    
                    message += f"{icon} {date}: {value} кВт·ч\n"
                
                message += "\n🚀 Откройте Mini App для полной истории"
            
            keyboard = [[
                InlineKeyboardButton("🚀 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            await update.message.reply_text("❌ Не удалось загрузить историю. Попробуйте позже.")
    
    async def services_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда услуг"""
        keyboard = [
            [InlineKeyboardButton("🔧 Замена счетчика", callback_data="service_replacement")],
            [InlineKeyboardButton("⚙️ Техобслуживание", callback_data="service_maintenance")],
            [InlineKeyboardButton("📞 Консультация", callback_data="service_consultation")],
            [InlineKeyboardButton("🚀 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛠 Выберите услугу:",
            reply_markup=reply_markup
        )
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда поддержки"""
        support_message = """
💬 Служба поддержки

📞 Телефон: +7 (800) 555-0123
📧 Email: support@energy.ru
🕐 Режим работы: 
   Пн-Пт: 8:00-20:00
   Сб-Вс: 9:00-18:00

🔧 Аварийная служба: +7 (800) 555-0911
(круглосуточно)

🌐 Сайт: energy.gov.ru
        """
        
        keyboard = [[
            InlineKeyboardButton("🚀 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(support_message, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        help_message = """
🤖 Команды бота:

/start - Главное меню
/miniapp - Открыть Mini App
/readings - Передать показания
/history - История показаний  
/services - Заказать услуги
/support - Контакты поддержки
/help - Эта справка

🚀 Mini App предоставляет полный функционал:
• Передача показаний всех типов счетчиков
• Детальная история с графиками
• Заказ услуг с отслеживанием
• Статистика потребления
        """
        
        await update.message.reply_text(help_message)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("meter_"):
            await self._handle_meter_selection(query, context)
        elif data.startswith("service_"):
            await self._handle_service_selection(query, context)
    
    async def _handle_meter_selection(self, query, context):
        """Обработка выбора типа счетчика"""
        meter_type = query.data.replace("meter_", "")
        meter_names = {
            "electric": "электричества",
            "gas": "газа", 
            "water": "воды"
        }
        
        context.user_data['waiting_for'] = f'reading_{meter_type}'
        
        message = f"📊 Введите показания счетчика {meter_names.get(meter_type, 'неизвестного типа')}:"
        
        keyboard = [[
            InlineKeyboardButton("🚀 Через Mini App", web_app=WebAppInfo(url=MINI_APP_URL)),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def _handle_service_selection(self, query, context):
        """Обработка выбора услуги"""
        service_type = query.data.replace("service_", "")
        service_names = {
            "replacement": "замена счетчика",
            "maintenance": "техническое обслуживание",
            "consultation": "консультация специалиста"
        }
        
        service_name = service_names.get(service_type, "неизвестная услуга")
        
        message = f"🛠 Услуга: {service_name}\n\nДля оформления заявки используйте Mini App с полным функционалом."
        
        keyboard = [[
            InlineKeyboardButton("🚀 Оформить в Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        text = update.message.text
        user_data = context.user_data
        
        # Обработка показаний
        if user_data.get('waiting_for', '').startswith('reading_'):
            await self._process_reading_input(update, context)
            return
        
        # Обработка кнопок главного меню
        if text == "📋 Показания":
            await self.readings_command(update, context)
        elif text == "📈 История":
            await self.history_command(update, context)
        elif text == "🛠 Услуги":
            await self.services_command(update, context)
        elif text == "💬 Поддержка":
            await self.support_command(update, context)
        else:
            await update.message.reply_text(
                "🤔 Используйте кнопки меню или команды /help для получения справки."
            )
    
    async def _process_reading_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода показаний"""
        try:
            reading_value = int(update.message.text)
            
            if reading_value < 0:
                await update.message.reply_text("❌ Показания не могут быть отрицательными.")
                return
            
            waiting_for = context.user_data.get('waiting_for', '')
            meter_type = waiting_for.replace('reading_', '')
            user_id = str(update.effective_user.id)
            
            # Отправка показаний через API
            success = await self.submit_reading(user_id, reading_value, meter_type)
            
            if success:
                icon = self._get_meter_icon(meter_type)
                await update.message.reply_text(
                    f"✅ Показания приняты!\n{icon} {reading_value} кВт·ч"
                )
            else:
                await update.message.reply_text("❌ Ошибка при отправке показаний. Попробуйте через Mini App.")
            
            # Очистка состояния
            context.user_data.pop('waiting_for', None)
            
        except ValueError:
            await update.message.reply_text("❌ Введите числовое значение показаний.")
        except Exception as e:
            logger.error(f"Ошибка обработки показаний: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
    
    # API методы
    async def submit_reading(self, user_id: str, reading_value: int, meter_type: str) -> bool:
        """Отправка показаний через API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            data = {
                "telegram_id": int(user_id),
                "reading_value": reading_value,
                "meter_type": meter_type
            }
            
            async with self.session.post(f"{API_BASE_URL}/api/readings", json=data) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Ошибка API отправки показаний: {e}")
            return False
    
    async def get_readings_history(self, user_id: str) -> list:
        """Получение истории показаний"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(f"{API_BASE_URL}/api/readings/{user_id}") as response:
                if response.status == 200:
                    return await response.json()
                return []
                
        except Exception as e:
            logger.error(f"Ошибка API получения истории: {e}")
            return []
    
    def _get_meter_icon(self, meter_type: str) -> str:
        """Получение иконки для типа счетчика"""
        icons = {
            'electric': '⚡',
            'gas': '🔥',
            'water': '💧'
        }
        return icons.get(meter_type, '📊')
    
    def run(self):
        """Запуск бота"""
        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram library недоступна")
            return
            
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не установлен")
            return
        
        try:
            logger.info("Запуск Telegram бота...")
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
        finally:
            if self.session:
                asyncio.run(self.session.close())

def main():
    """Основная функция"""
    try:
        bot = EnergyBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()