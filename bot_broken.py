"""
Обновленный Telegram Bot для платформы Энергосбыт
Совместимая версия с улучшенным функционалом
"""

import logging
import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import requests

try:
    import telegram
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Telegram library import error: {e}")
    TELEGRAM_AVAILABLE = False

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')

# Состояния разговора
READING_INPUT, METER_TYPE_SELECT, READING_CONFIRM = range(3)

class EnergyBot:
    """Основной класс бота энергосбыта"""
    
    def __init__(self):
        self.application = None
        

    
    def register_handlers(self):
        """Регистрация всех обработчиков"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("miniapp", self.miniapp_command))
        self.application.add_handler(CommandHandler("readings", self.readings_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("services", self.services_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # Callback обработчики
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Текстовые сообщения
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update, context):
        """Команда /start - главное меню"""
        user = update.effective_user
        
        welcome_text = (
            f"👋 Добро пожаловать, {user.first_name}!\n\n"
            "🏢 Энергосбыт - Личный кабинет\n\n"
            "Управляйте коммунальными услугами прямо в Telegram:\n"
            "⚡ Передавайте показания счетчиков\n"
            "📊 Просматривайте историю потребления\n"
            "🔧 Заказывайте услуги и ремонт\n"
            "💬 Получайте поддержку 24/7\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [KeyboardButton("🚀 Открыть Mini App")],
            [KeyboardButton("⚡ Передать показания"), KeyboardButton("📊 История")],
            [KeyboardButton("🔧 Услуги"), KeyboardButton("💬 Поддержка")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def miniapp_command(self, update, context):
        """Команда /miniapp - открытие Mini App"""
        keyboard = [[
            InlineKeyboardButton(
                "🚀 Открыть приложение", 
                url=f"{API_BASE_URL}/static/index.html"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 Mini App Энергосбыт\n\n"
            "Полнофункциональное приложение для управления коммунальными услугами:\n\n"
            "📱 Современный интерфейс\n"
            "📊 Интерактивные графики\n"
            "⚡ Быстрая передача показаний\n"
            "🔧 Заказ услуг в один клик\n\n"
            "Нажмите кнопку ниже для запуска:",
            reply_markup=reply_markup
        )
    
    async def readings_command(self, update, context):
        """Команда передачи показаний"""
        keyboard = [
            [
                InlineKeyboardButton("⚡ Электричество", callback_data="meter_electric"),
                InlineKeyboardButton("🔥 Газ", callback_data="meter_gas")
            ],
            [
                InlineKeyboardButton("💧 Холодная вода", callback_data="meter_cold_water"),
                InlineKeyboardButton("🌡️ Горячая вода", callback_data="meter_hot_water")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 Передача показаний счетчика\n\n"
            "Выберите тип счетчика:",
            reply_markup=reply_markup
        )
    
    async def history_command(self, update, context):
        """Команда истории показаний"""
        user_id = str(update.effective_user.id)
        readings = await self.get_readings_history(user_id)
        
        if not readings:
            await update.message.reply_text(
                "📊 История показаний\n\n"
                "У вас пока нет переданных показаний.\n"
                "Используйте /readings для передачи показаний."
            )
            return
        
        history_text = "📊 История показаний (последние 5)\n\n"
        
        for reading in readings[-5:]:
            meter_icon = self.get_meter_icon(reading.get('meter_type', 'electric'))
            try:
                date = datetime.fromisoformat(reading['reading_date']).strftime('%d.%m.%Y')
            except:
                date = "недавно"
            
            history_text += f"{meter_icon} {reading['reading_value']} ({date})\n"
        
        keyboard = [[
            InlineKeyboardButton("🚀 Открыть полную историю", url=f"{API_BASE_URL}/static/index.html")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(history_text, reply_markup=reply_markup)
    
    async def services_command(self, update, context):
        """Команда услуг"""
        keyboard = [
            [
                InlineKeyboardButton("🔧 Замена счетчика", callback_data="service_meter_replacement"),
                InlineKeyboardButton("⚙️ Ремонт", callback_data="service_repair")
            ],
            [
                InlineKeyboardButton("🔍 Поверка", callback_data="service_inspection"),
                InlineKeyboardButton("💬 Консультация", callback_data="service_consultation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 Заказ услуг\n\n"
            "Выберите необходимую услугу:",
            reply_markup=reply_markup
        )
    
    async def support_command(self, update, context):
        """Команда поддержки"""
        keyboard = [
            [
                InlineKeyboardButton("📞 Позвонить", url="tel:+78001234567"),
                InlineKeyboardButton("✉️ Email", url="mailto:support@energosbyt.ru")
            ],
            [
                InlineKeyboardButton("💬 Онлайн чат", callback_data="start_chat")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💬 Служба поддержки\n\n"
            "🕐 Время работы: 8:00 - 20:00 (пн-пт)\n"
            "📞 Телефон: +7 800 123-45-67\n"
            "✉️ Email: support@energosbyt.ru\n\n"
            "⚠️ Аварийная служба: +7 800 123-45-68 (круглосуточно)",
            reply_markup=reply_markup
        )
    
    async def help_command(self, update, context):
        """Команда помощи"""
        help_text = (
            "📚 Справка по командам\n\n"
            "/start - Главное меню\n"
            "/miniapp - Открыть приложение\n"
            "/readings - Передать показания\n"
            "/history - История показаний\n"
            "/services - Заказать услуги\n"
            "/support - Служба поддержки\n\n"
            "💡 Используйте кнопки для удобной навигации"
        )
        
        await update.message.reply_text(help_text)
    
    async def button_callback(self, update, context):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("meter_"):
            await self.handle_meter_selection(query, context)
        elif query.data.startswith("service_"):
            await self.handle_service_selection(query, context)
        elif query.data == "start_chat":
            await query.edit_message_text(
                "💬 Для связи с оператором:\n"
                "📞 Позвоните: +7 800 123-45-67\n"
                "✉️ Напишите: support@energosbyt.ru"
            )
    
    async def handle_meter_selection(self, query, context):
        """Обработка выбора типа счетчика"""
        meter_types = {
            "meter_electric": "⚡ Электричество",
            "meter_gas": "🔥 Газ", 
            "meter_cold_water": "💧 Холодная вода",
            "meter_hot_water": "🌡️ Горячая вода"
        }
        
        meter_name = meter_types.get(query.data, "Неизвестный счетчик")
        context.user_data['meter_type'] = query.data.replace("meter_", "")
        context.user_data['meter_name'] = meter_name
        
        await query.edit_message_text(
            f"📊 {meter_name}\n\n"
            "Введите показания счетчика числом:"
        )
        
        context.user_data['waiting_for_reading'] = True
    
    async def handle_service_selection(self, query, context):
        """Обработка выбора услуги"""
        service_types = {
            "service_meter_replacement": "Замена счетчика",
            "service_repair": "Ремонт счетчика",
            "service_inspection": "Поверка счетчика", 
            "service_consultation": "Консультация"
        }
        
        service_name = service_types.get(query.data, "Неизвестная услуга")
        
        await query.edit_message_text(
            f"🔧 {service_name}\n\n"
            "Заявка принята! С вами свяжется специалист в течение рабочего дня.\n\n"
            "📞 Время работы: 8:00 - 20:00"
        )
        
        # Создание заявки через API
        user_id = str(query.from_user.id)
        service_type = query.data.replace("service_", "")
        await self.create_service_request(user_id, service_type, f"Заявка на {service_name.lower()}")
    
    async def handle_text(self, update, context):
        """Обработка текстовых сообщений"""
        text = update.message.text
        
        # Обработка кнопок клавиатуры
        if text == "🚀 Открыть Mini App":
            await self.miniapp_command(update, context)
        elif text == "⚡ Передать показания":
            await self.readings_command(update, context)
        elif text == "📊 История":
            await self.history_command(update, context)
        elif text == "🔧 Услуги":
            await self.services_command(update, context)
        elif text == "💬 Поддержка":
            await self.support_command(update, context)
        # Обработка показаний
        elif context.user_data.get('waiting_for_reading'):
            await self.process_reading_input(update, context)
        else:
            await update.message.reply_text(
                "Используйте команды или кнопки меню для навигации.\n"
                "Нажмите /help для получения справки."
            )
    
    async def process_reading_input(self, update, context):
        """Обработка ввода показаний"""
        try:
            reading_value = float(update.message.text.replace(',', '.'))
            
            if reading_value < 0:
                await update.message.reply_text(
                    "❌ Показания не могут быть отрицательными. Попробуйте еще раз:"
                )
                return
            
            user_id = str(update.effective_user.id)
            meter_type = context.user_data.get('meter_type', 'electric')
            meter_name = context.user_data.get('meter_name', 'Счетчик')
            
            # Отправка показаний через API
            success = await self.submit_reading(user_id, reading_value, meter_type)
            
            if success:
                await update.message.reply_text(
                    f"✅ Показания переданы успешно!\n\n"
                    f"Тип: {meter_name}\n"
                    f"Значение: {reading_value}\n"
                    f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    "📱 Откройте Mini App для детальной статистики"
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при передаче показаний. Попробуйте позже."
                )
            
            # Очистка состояния
            context.user_data.pop('waiting_for_reading', None)
            context.user_data.pop('meter_type', None)
            context.user_data.pop('meter_name', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Введите число (например: 1234 или 1234.5):"
            )
    
    async def error_handler(self, update, context):
        """Обработчик ошибок"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    # API методы
    async def submit_reading(self, user_id: str, reading_value: float, meter_type: str) -> bool:
        """Отправка показаний через API"""
        try:
            data = {
                "telegram_id": int(user_id),
                "reading_value": int(reading_value),
                "meter_type": meter_type
            }
            response = requests.post(f"{API_BASE_URL}/api/readings", json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error submitting reading: {e}")
            return False
    
    async def get_readings_history(self, user_id: str) -> list:
        """Получение истории показаний"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/readings/{user_id}")
            if response.status_code == 200:
                return response.json().get('readings', [])
        except Exception as e:
            logger.error(f"Error getting readings history: {e}")
        return []
    
    async def create_service_request(self, user_id: str, service_type: str, description: str) -> bool:
        """Создание заявки на услугу"""
        try:
            data = {
                "telegram_id": int(user_id),
                "service_type": service_type,
                "description": description
            }
            response = requests.post(f"{API_BASE_URL}/api/service-request", json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            return False
    
    @staticmethod
    def get_meter_icon(meter_type: str) -> str:
        """Получение иконки для типа счетчика"""
        icons = {
            'electric': '⚡',
            'gas': '🔥',
            'cold_water': '💧',
            'hot_water': '🌡️',
            'water': '💧'
        }
        return icons.get(meter_type, '📊')
    
    def run(self):
        """Запуск бота"""
        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram library недоступна")
            return
            
        try:
            # Создание приложения
            if not BOT_TOKEN:
                raise ValueError("BOT_TOKEN не установлен")
                
            self.application = Application.builder().token(BOT_TOKEN).build()
            self.register_handlers()
            
            logger.info("Бот инициализирован успешно")
            logger.info("Запуск бота...")
            
            # Запуск бота
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")

def main():
    """Основная функция запуска"""
    try:
        bot = EnergyBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()