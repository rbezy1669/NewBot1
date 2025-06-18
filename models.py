"""
Database models for Russian Energy Platform
Using SQLAlchemy with PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import os

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
    inn = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class MeterReading(Base):
    """Показания счетчиков"""
    __tablename__ = 'meter_readings'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    reading_value = Column(Integer, nullable=False)
    meter_type = Column(String, default='electric')  # electric, gas, water
    submission_method = Column(String, default='bot')  # bot, mini_app, web
    status = Column(String, default='submitted')  # submitted, processed, verified
    notes = Column(Text, nullable=True)
    reading_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

class ServiceRequest(Base):
    """Заявки на услуги"""
    __tablename__ = 'service_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    service_type = Column(String, nullable=False)  # meter_replacement, consultation, repair
    description = Column(Text, nullable=True)
    status = Column(String, default='new')  # new, in_progress, completed, cancelled
    priority = Column(String, default='normal')  # low, normal, high, urgent
    scheduled_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class EmailSubscription(Base):
    """Email подписки"""
    __tablename__ = 'email_subscriptions'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    subscription_date = Column(DateTime, default=func.now())
    unsubscribed_date = Column(DateTime, nullable=True)

class AuthUser(Base):
    """Авторизованные пользователи через Госуслуги"""
    __tablename__ = 'auth_users'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    gosuslugi_id = Column(String, unique=True, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    inn = Column(String, nullable=True)
    snils = Column(String, nullable=True)
    auth_data = Column(Text, nullable=True)  # JSON данные от Госуслуг
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

class SystemLog(Base):
    """Системные логи"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    status = Column(String, default='success')  # success, error, warning
    created_at = Column(DateTime, default=func.now())

# Database connection setup
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Создание всех таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы PostgreSQL созданы успешно")

def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseManager:
    """Менеджер базы данных для работы с PostgreSQL"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def create_all_tables(self):
        """Создание всех таблиц"""
        create_tables()
        
    def add_user(self, telegram_id: str, username: str = None, full_name: str = None):
        """Добавление пользователя"""
        db = SessionLocal()
        try:
            # Проверка существования пользователя
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
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    def add_reading(self, user_id: str, reading_value: int, meter_type: str = 'electric', method: str = 'bot'):
        """Добавление показания счетчика"""
        db = SessionLocal()
        try:
            reading = MeterReading(
                user_id=user_id,
                reading_value=reading_value,
                meter_type=meter_type,
                submission_method=method
            )
            db.add(reading)
            db.commit()
            db.refresh(reading)
            return reading
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    def get_readings_history(self, user_id: str, limit: int = 10):
        """Получение истории показаний"""
        db = SessionLocal()
        try:
            readings = db.query(MeterReading).filter(
                MeterReading.user_id == user_id
            ).order_by(MeterReading.reading_date.desc()).limit(limit).all()
            return readings
        finally:
            db.close()
            
    def add_service_request(self, user_id: str, service_type: str, description: str = None):
        """Добавление заявки на услугу"""
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
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    def add_email_subscription(self, email: str):
        """Добавление email подписки"""
        db = SessionLocal()
        try:
            existing = db.query(EmailSubscription).filter(EmailSubscription.email == email).first()
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    existing.unsubscribed_date = None
                    db.commit()
                return existing
                
            subscription = EmailSubscription(email=email)
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            return subscription
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()