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

from models import DatabaseManager, get_db, User, MeterReading, ServiceRequest, EmailSubscription, AuthUser, SystemLog

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
CLIENT_ID = os.getenv('GOSUSLUGI_CLIENT_ID', 'your_client_id')
CLIENT_SECRET = os.getenv('GOSUSLUGI_CLIENT_SECRET', 'your_client_secret')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://0.0.0.0:5000/callback')
TOKEN_URL = 'https://esia.gosuslugi.ru/aas/oauth2/te'
USERINFO_URL = 'https://esia.gosuslugi.ru/rs/prns'

# Создание приложения FastAPI
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

# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()

# Модели данных
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

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница (редирект на статический сайт)"""
    return RedirectResponse(url="/static/index.html")

@app.get("/callback")
async def oauth_callback(request: Request):
    """Обработка OAuth callback от Госуслуг"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # Telegram ID
    error = request.query_params.get("error")
    
    if error:
        logger.error(f"OAuth error: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Ошибка авторизации</title></head>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Произошла ошибка при авторизации через Госуслуги: {error}</p>
                    <p><a href="https://t.me/your_bot_username">Вернуться к боту</a></p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Обмен кода на токен
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }
        
        token_response = requests.post(TOKEN_URL, data=token_data)
        token_info = token_response.json()
        
        if 'access_token' not in token_info:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Получение информации о пользователе
        headers = {'Authorization': f"Bearer {token_info['access_token']}"}
        user_response = requests.get(USERINFO_URL, headers=headers)
        user_data = user_response.json()
        
        # Сохранение данных пользователя в БД через SQLAlchemy
        if state:  # Telegram ID
            db = next(get_db())
            try:
                # Создание или обновление записи пользователя
                auth_user = db.query(AuthUser).filter(AuthUser.telegram_id == state).first()
                if not auth_user:
                    auth_user = AuthUser(telegram_id=state)
                    db.add(auth_user)
                
                # Update user attributes using proper SQLAlchemy approach
                for attr, value in {
                    'gosuslugi_id': user_data.get('id'),
                    'full_name': user_data.get('fullName', ''),
                    'email': user_data.get('email', ''),
                    'inn': user_data.get('inn', ''),
                    'snils': user_data.get('snils', ''),
                    'auth_data': json.dumps(user_data, ensure_ascii=False),
                    'is_verified': True,
                    'last_login': datetime.now()
                }.items():
                    setattr(auth_user, attr, value)
                
                db.commit()
            finally:
                db.close()
        
        return HTMLResponse(
            content="""
            <html>
                <head><title>Авторизация успешна</title></head>
                <body>
                    <h1>Авторизация через Госуслуги успешна!</h1>
                    <p>Вы можете закрыть это окно и вернуться к боту.</p>
                    <script>
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                    </script>
                </body>
            </html>
            """
        )
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Ошибка</title></head>
                <body>
                    <h1>Произошла ошибка</h1>
                    <p>Не удалось завершить авторизацию: {str(e)}</p>
                </body>
            </html>
            """,
            status_code=500
        )

@app.post("/api/subscribe")
async def subscribe_email(subscription: EmailSubscription, db: Session = Depends(get_db)):
    """API для подписки на email рассылку"""
    try:
        success = db_manager.add_email_subscription(subscription.email)
        if success:
            return {"message": "Подписка оформлена успешно", "status": "success"}
        else:
            return {"message": "Email уже подписан", "status": "info"}
    except Exception as e:
        logger.error(f"Email subscription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при оформлении подписки")

@app.get("/api/user/{telegram_id}")
async def get_user_info(telegram_id: str, db: Session = Depends(get_db)):
    """Получение информации о пользователе по Telegram ID"""
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        auth_user = db.query(AuthUser).filter(AuthUser.telegram_id == telegram_id).first()
        
        if not user and not auth_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        user_info = {
            "telegram_id": telegram_id,
            "full_name": auth_user.full_name if auth_user else (user.full_name if user else None),
            "email": auth_user.email if auth_user else (user.email if user else None),
            "inn": auth_user.inn if auth_user else (user.inn if user else None),
            "is_verified": auth_user.is_verified if auth_user else False
        }
        
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных пользователя")

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/api/readings")
async def submit_reading(submission: ReadingSubmission, db: Session = Depends(get_db)):
    """API для передачи показаний от Mini App"""
    try:
        reading = db_manager.add_reading(
            user_id=str(submission.telegram_id),
            reading_value=submission.reading_value,
            meter_type=submission.meter_type or 'electric',
            method='mini_app'
        )
        
        return {
            "message": "Показания успешно переданы",
            "reading_id": reading.id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Submit reading error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при передаче показаний")

@app.get("/api/readings/{telegram_id}")
async def get_readings_history(telegram_id: str, db: Session = Depends(get_db)):
    """Получение истории показаний пользователя"""
    try:
        readings = db_manager.get_readings_history(str(telegram_id), limit=20)
        readings_data = []
        
        for reading in readings:
            readings_data.append({
                "id": reading.id,
                "reading_value": reading.reading_value,
                "meter_type": reading.meter_type,
                "submission_method": reading.submission_method,
                "status": reading.status,
                "reading_date": reading.reading_date.isoformat() if reading.reading_date else None,
                "created_at": reading.created_at.isoformat() if reading.created_at else None
            })
        
        return {"readings": readings_data}
    except Exception as e:
        logger.error(f"Get readings history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения истории показаний")

@app.post("/api/service-request")
async def create_service_request(request: ServiceRequestModel, db: Session = Depends(get_db)):
    """API для создания заявки на услугу"""
    try:
        service_request = db_manager.add_service_request(
            user_id=str(request.telegram_id),
            service_type=request.service_type,
            description=request.description or f"Заявка на {request.service_type}"
        )
        
        return {
            "message": "Заявка создана успешно",
            "request_id": service_request.id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Create service request error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при создании заявки")

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Получение базовой статистики"""
    try:
        total_users = db.query(User).count()
        total_readings = db.query(MeterReading).count()
        total_requests = db.query(ServiceRequest).count()
        
        return {
            "total_users": total_users,
            "total_readings": total_readings,
            "total_service_requests": total_requests,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)