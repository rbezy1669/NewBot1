"""
FastAPI Backend для обработки OAuth авторизации через Госуслуги
и предоставления API для веб-портала и Telegram Mini App
Использует PostgreSQL через SQLAlchemy
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

import requests
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from models import db_manager, get_db, User, MeterReading, ServiceRequest, EmailSubscription, AuthUser, SystemLog

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth конфигурация для Госуслуг
GOSUSLUGI_CLIENT_ID = os.getenv('GOSUSLUGI_CLIENT_ID', 'test_client_id')
GOSUSLUGI_CLIENT_SECRET = os.getenv('GOSUSLUGI_CLIENT_SECRET', 'test_client_secret')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/oauth/callback')

# URL для авторизации через Госуслуги
AUTH_URL = f"https://esia.gosuslugi.ru/aas/oauth2/ac?client_id={GOSUSLUGI_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=openid+fullname+email"

# Pydantic модели для API
class EmailSubscription(BaseModel):
    email: EmailStr

class UserInfo(BaseModel):
    telegram_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    inn: Optional[str] = None

class ReadingSubmission(BaseModel):
    telegram_id: int
    reading_value: int
    meter_type: Optional[str] = 'electric'

class ServiceRequestModel(BaseModel):
    telegram_id: int
    service_type: str
    description: Optional[str] = None

# Инициализация FastAPI приложения
app = FastAPI(
    title="Энергосбыт Backend API",
    description="API для веб-портала и Telegram Mini App",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация PostgreSQL БД при старте
@app.on_event("startup")
async def startup_event():
    """Инициализация базы данных при старте"""
    try:
        db_manager.create_all_tables()
        logger.info("PostgreSQL database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e

# API endpoints
@app.get("/")
async def root():
    """Главная страница (редирект на статический сайт)"""
    return RedirectResponse(url="/index.html")

@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    """Обработка OAuth callback от Госуслуг"""
    code = request.query_params.get('code')
    state = request.query_params.get('state')  # telegram_id
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Недостаточно параметров для авторизации")
    
    try:
        # Здесь должен быть реальный обмен кода на токен с Госуслугами
        # Для демонстрации используем заглушку
        user_data = {
            'id': f'gosuslugi_{state}',
            'fullName': 'Иванов Иван Иванович',
            'email': 'user@example.com',
            'inn': '123456789012',
            'mobile': '+7 900 123-45-67'
        }
        
        # Сохранение в PostgreSQL
        db = next(get_db())
        try:
            # Поиск или создание пользователя
            auth_user = db.query(AuthUser).filter(AuthUser.telegram_id == state).first()
            if not auth_user:
                auth_user = AuthUser(
                    telegram_id=state,
                    gosuslugi_id=user_data['id'],
                    full_name=user_data['fullName'],
                    email=user_data['email'],
                    inn=user_data['inn'],
                    auth_data=json.dumps(user_data, ensure_ascii=False),
                    is_verified=True
                )
                db.add(auth_user)
            else:
                auth_user.gosuslugi_id = user_data['id']
                auth_user.full_name = user_data['fullName']
                auth_user.email = user_data['email']
                auth_user.inn = user_data['inn']
                auth_user.auth_data = json.dumps(user_data, ensure_ascii=False)
                auth_user.is_verified = True
                auth_user.last_login = datetime.now()
            
            db.commit()
            
            # Логирование
            log_entry = SystemLog(
                user_id=state,
                action='oauth_success',
                details=f'Successful OAuth login via Gosuslugi',
                status='success'
            )
            db.add(log_entry)
            db.commit()
            
        finally:
            db.close()
        
        success_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Авторизация успешна</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
        </head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>✅ Авторизация через Госуслуги успешна!</h2>
            <p>Добро пожаловать, {user_data['fullName']}</p>
            <p>Теперь вы можете пользоваться всеми возможностями сервиса</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    window.Telegram.WebApp.close();
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=success_html)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка авторизации")

@app.post("/api/subscribe")
async def subscribe_email(subscription: EmailSubscription, db: Session = Depends(get_db)):
    """API для подписки на email рассылку"""
    try:
        result = db_manager.add_email_subscription(subscription.email)
        if result:
            return {"status": "success", "message": "Подписка оформлена успешно"}
        else:
            return {"status": "info", "message": "Email уже подписан"}
    except Exception as e:
        logger.error(f"Email subscription error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка оформления подписки")

@app.get("/api/user/{telegram_id}")
async def get_user_info(telegram_id: str, db: Session = Depends(get_db)):
    """Получение информации о пользователе по Telegram ID"""
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        auth_user = db.query(AuthUser).filter(AuthUser.telegram_id == telegram_id).first()
        
        user_info = {
            "telegram_id": telegram_id,
            "full_name": None,
            "email": None,
            "inn": None,
            "is_verified": False
        }
        
        if user:
            user_info.update({
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone
            })
        
        if auth_user:
            user_info.update({
                "full_name": auth_user.full_name,
                "email": auth_user.email,
                "inn": auth_user.inn,
                "is_verified": auth_user.is_verified
            })
        
        return user_info
        
    except Exception as e:
        logger.error(f"Error getting user info for {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных пользователя")

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Энергосбыт Backend API"
    }

@app.post("/api/readings")
async def submit_reading(submission: ReadingSubmission, db: Session = Depends(get_db)):
    """API для передачи показаний от Mini App"""
    try:
        # Добавление показания через менеджер БД
        reading = db_manager.add_reading(
            user_id=str(submission.telegram_id),
            reading_value=submission.reading_value,
            meter_type=submission.meter_type,
            method='mini_app'
        )
        
        # Логирование
        log_entry = SystemLog(
            user_id=str(submission.telegram_id),
            action='reading_submitted',
            details=f'Reading value: {submission.reading_value}, type: {submission.meter_type}',
            status='success'
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Reading submitted: user {submission.telegram_id}, value {submission.reading_value}")
        
        return {
            "status": "success",
            "message": "Показания успешно переданы",
            "reading_id": reading.id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error submitting reading: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения показаний")

@app.get("/api/readings/{telegram_id}")
async def get_readings_history(telegram_id: str, db: Session = Depends(get_db)):
    """Получение истории показаний пользователя"""
    try:
        readings = db_manager.get_readings_history(telegram_id, limit=12)
        
        result = []
        for reading in readings:
            result.append({
                "id": reading.id,
                "value": reading.reading_value,
                "date": reading.reading_date.isoformat(),
                "meter_type": reading.meter_type,
                "method": reading.submission_method,
                "status": reading.status
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting readings for user {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения истории")

@app.post("/api/service-requests")
async def create_service_request(request: ServiceRequestModel, db: Session = Depends(get_db)):
    """API для создания заявки на услугу"""
    try:
        service_request = db_manager.add_service_request(
            user_id=str(request.telegram_id),
            service_type=request.service_type,
            description=request.description
        )
        
        # Логирование
        log_entry = SystemLog(
            user_id=str(request.telegram_id),
            action='service_request_created',
            details=f'Service type: {request.service_type}',
            status='success'
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "status": "success",
            "message": "Заявка создана успешно",
            "request_id": service_request.id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating service request: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания заявки")

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Получение базовой статистики"""
    try:
        # Количество пользователей
        users_count = db.query(User).count()
        
        # Количество авторизованных пользователей
        auth_users_count = db.query(AuthUser).filter(AuthUser.is_verified == True).count()
        
        # Количество подписчиков
        subscribers_count = db.query(EmailSubscription).filter(EmailSubscription.is_active == True).count()
        
        # Количество показаний за последний месяц
        month_ago = datetime.now() - timedelta(days=30)
        recent_readings = db.query(MeterReading).filter(MeterReading.reading_date >= month_ago).count()
        
        return {
            "total_users": users_count,
            "authorized_users": auth_users_count,
            "email_subscribers": subscribers_count,
            "recent_readings": recent_readings,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")

# Статические файлы (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_new:app", host="0.0.0.0", port=5000, reload=True)