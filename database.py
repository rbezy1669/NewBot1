"""
Модуль для работы с базами данных
Инициализация и миграция схем для всех компонентов системы
"""

import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Инициализатор всех баз данных системы"""
    
    def __init__(self):
        self.databases = {
            'bot_data.db': self.init_bot_database,
            'backend_data.db': self.init_backend_database,
            'auth_users.db': self.init_auth_database,
            'readings.db': self.init_readings_database
        }
    
    def initialize_all(self):
        """Инициализация всех баз данных"""
        print("🗄️ Инициализация баз данных...")
        
        for db_name, init_func in self.databases.items():
            try:
                init_func(db_name)
                print(f"✅ {db_name} - инициализирована")
            except Exception as e:
                print(f"❌ Ошибка инициализации {db_name}: {e}")
                logger.error(f"Database init error for {db_name}: {e}")
        
        print("🗄️ Инициализация баз данных завершена")
    
    def init_bot_database(self, db_path: str):
        """Инициализация базы данных для Telegram бота"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей бота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                phone TEXT,
                gosuslugi_id TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица показаний счётчиков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                reading_value INTEGER NOT NULL,
                meter_number TEXT,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'submitted',
                notes TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Таблица заявок на замену счётчиков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replacement_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                meter_type TEXT NOT NULL,
                current_meter_number TEXT,
                address TEXT,
                preferred_date TEXT,
                phone_contact TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Таблица сообщений в поддержку
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_text TEXT,
                responded_at TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Индексы для оптимизации
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_readings_telegram_id ON readings(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_readings_date ON readings(submission_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_telegram_id ON replacement_requests(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_status ON replacement_requests(status)')
        
        conn.commit()
        conn.close()
    
    def init_backend_database(self, db_path: str):
        """Инициализация базы данных для backend API"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Таблица авторизованных через Госуслуги пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE,
                gosuslugi_id TEXT UNIQUE,
                full_name TEXT,
                first_name TEXT,
                last_name TEXT,
                middle_name TEXT,
                email TEXT,
                inn TEXT,
                snils TEXT,
                phone TEXT,
                birth_date TEXT,
                address TEXT,
                raw_data TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица email подписок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                telegram_id TEXT,
                full_name TEXT,
                subscription_source TEXT DEFAULT 'web',
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unsubscribed_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                preferences TEXT -- JSON строка с настройками подписки
            )
        ''')
        
        # Таблица промо-акций (для управления через админку)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица логов API запросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT,
                method TEXT,
                ip_address TEXT,
                user_agent TEXT,
                telegram_id TEXT,
                request_data TEXT,
                response_status INTEGER,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Заполнение промо-акций по умолчанию
        cursor.execute('''
            INSERT OR IGNORE INTO promotions (id, title, description, type)
            VALUES 
            (1, 'Скидка 15% на оплату электроэнергии онлайн', 'Оплачивайте счета через личный кабинет и получайте скидку 15%. Быстро и удобно! Акция действует до конца месяца.', 'discount'),
            (2, 'Бесплатная консультация по энергосбережению', 'Наши специалисты помогут снизить расходы на электроэнергию в вашем доме. Консультация включает анализ потребления и рекомендации.', 'consult'),
            (3, 'Акция для новых клиентов', 'Подключайтесь к Энергосбыту и получите скидку 10% на первый счет. Дополнительно — бесплатное подключение счётчика.', 'promo'),
            (4, 'Программа лояльности «Энергобонус»', 'Накопите баллы за оплату и обменяйте их на полезные подарки и услуги. 1 рубль = 1 балл. Минимум для обмена — 100 баллов.', 'loyalty')
        ''')
        
        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_telegram_id ON auth_users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_gosuslugi_id ON auth_users(gosuslugi_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_email ON email_subscriptions(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(is_active)')
        
        conn.commit()
        conn.close()
    
    def init_auth_database(self, db_path: str):
        """Инициализация базы данных для OAuth авторизации"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Упрощённая таблица для совместимости с существующими файлами
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                tg_id TEXT PRIMARY KEY,
                full_name TEXT,
                inn TEXT,
                raw TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def init_readings_database(self, db_path: str):
        """Инициализация базы данных для показаний счётчиков"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Основная таблица показаний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meter_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                meter_number TEXT,
                reading_value INTEGER NOT NULL,
                reading_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submission_method TEXT DEFAULT 'telegram',
                status TEXT DEFAULT 'confirmed',
                previous_reading INTEGER,
                consumption_kwh INTEGER,
                billing_period TEXT,
                notes TEXT
            )
        ''')
        
        # Таблица счётчиков пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_meters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                meter_number TEXT UNIQUE NOT NULL,
                meter_type TEXT DEFAULT 'single_phase',
                installation_date TIMESTAMP,
                last_reading INTEGER DEFAULT 0,
                last_reading_date TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_readings_user_id ON meter_readings(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_readings_date ON meter_readings(reading_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meters_user_id ON user_meters(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meters_number ON user_meters(meter_number)')
        
        conn.commit()
        conn.close()
    
    def create_sample_data(self):
        """Создание примеров данных для тестирования"""
        print("📊 Создание тестовых данных...")
        
        # Добавляем тестового пользователя
        try:
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (telegram_id, username, first_name, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                123456789,  # Тестовый Telegram ID
                'test_user',
                'Тест',
                'Тест Пользователь',
                datetime.now().isoformat()
            ))
            
            # Добавляем тестовые показания
            cursor.execute('''
                INSERT OR IGNORE INTO readings 
                (telegram_id, reading_value, submission_date)
                VALUES (?, ?, ?)
            ''', (
                123456789,
                12345,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            print("✅ Тестовые данные созданы")
            
        except Exception as e:
            print(f"❌ Ошибка создания тестовых данных: {e}")
    
    def check_database_integrity(self):
        """Проверка целостности всех баз данных"""
        print("🔍 Проверка целостности баз данных...")
        
        for db_name in self.databases.keys():
            if os.path.exists(db_name):
                try:
                    conn = sqlite3.connect(db_name)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()[0]
                    conn.close()
                    
                    if result == "ok":
                        print(f"✅ {db_name} - целостность OK")
                    else:
                        print(f"⚠️ {db_name} - найдены проблемы: {result}")
                        
                except Exception as e:
                    print(f"❌ Ошибка проверки {db_name}: {e}")
            else:
                print(f"⚠️ {db_name} - файл не найден")
    
    def backup_databases(self, backup_dir: str = "backups"):
        """Создание резервных копий баз данных"""
        import shutil
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for db_name in self.databases.keys():
            if os.path.exists(db_name):
                try:
                    backup_name = f"{backup_dir}/{db_name}_{timestamp}.backup"
                    shutil.copy2(db_name, backup_name)
                    print(f"💾 Создана резервная копия: {backup_name}")
                except Exception as e:
                    print(f"❌ Ошибка создания копии {db_name}: {e}")

def main():
    """Основная функция для инициализации баз данных"""
    initializer = DatabaseInitializer()
    
    print("🗄️ Система управления базами данных Энергосбыт")
    print("=" * 50)
    
    # Инициализация всех БД
    initializer.initialize_all()
    
    # Создание тестовых данных
    initializer.create_sample_data()
    
    # Проверка целостности
    initializer.check_database_integrity()
    
    print("=" * 50)
    print("🎉 Инициализация завершена успешно!")

if __name__ == "__main__":
    main()
