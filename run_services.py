"""
Скрипт для запуска всех сервисов системы Энергосбыт
Управляет веб-сервером, Telegram ботом и инициализацией БД
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging
from typing import List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    """Менеджер для управления всеми сервисами"""
    
    def __init__(self):
        self.services: List[subprocess.Popen] = []
        self.running = False
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов для корректного завершения"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов завершения"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.stop_all_services()
        sys.exit(0)
    
    def check_dependencies(self) -> bool:
        """Проверка зависимостей и конфигурации"""
        print("🔍 Проверка зависимостей...")
        
        # Проверка Python модулей
        required_modules = [
            'fastapi',
            'uvicorn',
            'telegram',
            'requests',
            'sqlite3'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"✅ {module}")
            except ImportError:
                missing_modules.append(module)
                print(f"❌ {module} - не установлен")
        
        if missing_modules:
            print(f"\n⚠️ Не хватает модулей: {', '.join(missing_modules)}")
            print("Установите их командой:")
            print("pip install fastapi uvicorn python-telegram-bot requests")
            return False
        
        # Проверка переменных окружения (опционально для демо режима)
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print("⚠️ BOT_TOKEN не установлен - бот будет работать в демо режиме")
        else:
            print("✅ BOT_TOKEN найден")
        
        print("✅ Все зависимости проверены")
        return True
    
    def init_databases(self):
        """Инициализация баз данных"""
        print("🗄️ Инициализация баз данных...")
        try:
            from database import DatabaseInitializer
            initializer = DatabaseInitializer()
            initializer.initialize_all()
            print("✅ Базы данных инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            print(f"❌ Ошибка инициализации БД: {e}")
    
    def start_web_server(self):
        """Запуск веб-сервера FastAPI"""
        print("🌐 Запуск веб-сервера...")
        try:
            process = subprocess.Popen([
                sys.executable, 'backend.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.services.append(process)
            print("✅ Веб-сервер запущен (порт 8000)")
            return process
        except Exception as e:
            logger.error(f"Ошибка запуска веб-сервера: {e}")
            print(f"❌ Ошибка запуска веб-сервера: {e}")
            return None
    
    def start_telegram_bot(self):
        """Запуск Telegram бота"""
        print("🤖 Запуск Telegram бота...")
        
        # Проверяем наличие BOT_TOKEN
        if not os.getenv('BOT_TOKEN'):
            print("⚠️ BOT_TOKEN не установлен, пропускаем запуск бота")
            return None
            
        try:
            process = subprocess.Popen([
                sys.executable, 'bot.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.services.append(process)
            print("✅ Telegram бот запущен")
            return process
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            print(f"❌ Ошибка запуска бота: {e}")
            return None
    
    def monitor_service(self, process: subprocess.Popen, name: str):
        """Мониторинг состояния сервиса"""
        while self.running and process.poll() is None:
            time.sleep(5)
        
        if self.running:
            logger.warning(f"Сервис {name} завершился неожиданно")
            print(f"⚠️ Сервис {name} завершился неожиданно")
            
            # Попытка перезапуска
            if name == "web-server":
                self.start_web_server()
            elif name == "telegram-bot":
                self.start_telegram_bot()
    
    def start_all_services(self):
        """Запуск всех сервисов"""
        print("🚀 Запуск системы Энергосбыт...")
        print("=" * 50)
        
        # Проверка зависимостей
        if not self.check_dependencies():
            return False
        
        # Инициализация БД
        self.init_databases()
        
        self.running = True
        
        # Запуск веб-сервера
        web_process = self.start_web_server()
        if web_process:
            threading.Thread(
                target=self.monitor_service,
                args=(web_process, "web-server"),
                daemon=True
            ).start()
        
        # Небольшая задержка между запусками
        time.sleep(2)
        
        # Запуск Telegram бота
        bot_process = self.start_telegram_bot()
        if bot_process:
            threading.Thread(
                target=self.monitor_service,
                args=(bot_process, "telegram-bot"),
                daemon=True
            ).start()
        
        print("=" * 50)
        print("🎉 Все сервисы запущены!")
        print()
        print("📱 Telegram бот: готов к работе")
        print("🌐 Веб-портал: http://localhost:5000")
        print("🔗 API документация: http://localhost:5000/docs")
        print()
        print("Для завершения работы нажмите Ctrl+C")
        print("=" * 50)
        
        return True
    
    def stop_all_services(self):
        """Остановка всех сервисов"""
        print("\n🛑 Остановка сервисов...")
        self.running = False
        
        for i, process in enumerate(self.services):
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Сервис {i+1} остановлен")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️ Сервис {i+1} принудительно завершён")
            except Exception as e:
                logger.error(f"Ошибка остановки сервиса {i+1}: {e}")
        
        self.services.clear()
        print("🏁 Все сервисы остановлены")
    
    def show_status(self):
        """Показать статус всех сервисов"""
        print("📊 Статус сервисов:")
        print("-" * 30)
        
        for i, process in enumerate(self.services):
            if process.poll() is None:
                print(f"✅ Сервис {i+1}: работает (PID: {process.pid})")
            else:
                print(f"❌ Сервис {i+1}: остановлен")
    
    def run_interactive_mode(self):
        """Интерактивный режим управления"""
        while self.running:
            try:
                print("\n" + "=" * 50)
                print("🎛️ Панель управления Энергосбыт")
                print("1. Показать статус сервисов")
                print("2. Перезапустить веб-сервер")
                print("3. Перезапустить Telegram бота")
                print("4. Остановить все сервисы")
                print("5. Выход")
                print("=" * 50)
                
                choice = input("Введите номер команды: ").strip()
                
                if choice == '1':
                    self.show_status()
                elif choice == '2':
                    print("🔄 Перезапуск веб-сервера...")
                    # Реализация перезапуска
                elif choice == '3':
                    print("🔄 Перезапуск Telegram бота...")
                    # Реализация перезапуска
                elif choice == '4':
                    self.stop_all_services()
                    break
                elif choice == '5':
                    break
                else:
                    print("❌ Неверная команда")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Ошибка в интерактивном режиме: {e}")
    
    def wait_for_services(self):
        """Ожидание завершения всех сервисов"""
        try:
            while self.running and any(p.poll() is None for p in self.services):
                time.sleep(1)
        except KeyboardInterrupt:
            pass

def print_banner():
    """Вывод баннера приложения"""
    banner = """
╔══════════════════════════════════════════════════════╗
║              🏢 СИСТЕМА ЭНЕРГОСБЫТ                   ║
║                                                      ║
║  📱 Telegram Bot + 🌐 Web Portal + 🔐 Gosuslugi     ║
║                                                      ║
║  Комплексная система обслуживания клиентов           ║
║  энергосбытовой компании                             ║
╚══════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Основная функция"""
    print_banner()
    
    manager = ServiceManager()
    
    try:
        # Запуск всех сервисов
        if manager.start_all_services():
            # Ожидание работы сервисов
            manager.wait_for_services()
        else:
            print("❌ Не удалось запустить все сервисы")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал завершения...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"💥 Критическая ошибка: {e}")
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main()
