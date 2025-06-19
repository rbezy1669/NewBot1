#!/usr/bin/env python3
"""
Запуск обновленного Telegram бота для платформы Энергосбыт
"""

import os
import sys
import asyncio
import logging
from bot import EnergyBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    print("🤖 Запуск Telegram бота Энергосбыт...")
    
    # Проверка переменных окружения
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ Ошибка: BOT_TOKEN не установлен")
        print("Установите токен бота в переменных окружения")
        sys.exit(1)
    
    print(f"✅ Токен бота найден: {bot_token[:10]}...")
    
    try:
        # Создание и запуск бота
        bot = EnergyBot()
        print("🚀 Инициализация бота...")
        asyncio.run(bot.run())
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()