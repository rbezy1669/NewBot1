"""
FastAPI Backend для обработки OAuth авторизации через Госуслуги
и предоставления API для веб-портала
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

# Конфигурация
CLIENT_ID = os.getenv('GOSUSLUGI_CLIENT_ID', 'your_client_id')
CLIENT_SECRET = os.getenv('GOSUSLUGI_CLIENT_SECRET', 'your_client_secret')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://0.0.0.0:5000/callback')
TOKEN_URL = 'https://esia.gosuslugi.ru/aas/oauth2/te'
USERINFO_URL = 'https://esia.gosuslugi.ru/rs/prns'

app = FastAPI(title="Энергосбыт API", description="API для портала энергосбыта")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица авторизованных пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE,
                gosuslugi_id TEXT,
                full_name TEXT,
                email TEXT,
                inn TEXT,
                phone TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица подписок на email
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Таблица показаний (для синхронизации с ботом)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                reading_value INTEGER,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'backend'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user_auth(self, telegram_id: str, user_data: dict):
        """Сохранение данных авторизации пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO auth_users 
            (telegram_id, gosuslugi_id, full_name, email, inn, phone, raw_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            telegram_id,
            user_data.get('id'),
            user_data.get('fullName', ''),
            user_data.get('email', ''),
            user_data.get('inn', ''),
            user_data.get('mobile', ''),
            json.dumps(user_data, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def add_email_subscription(self, email: str) -> bool:
        """Добавление email подписки"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO email_subscriptions (email)
                VALUES (?)
            ''', (email,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Email уже существует
            return False
    
    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[dict]:
        """Получение пользователя по Telegram ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM auth_users WHERE telegram_id = ?
        ''', (telegram_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

# Инициализация менеджера БД
db_manager = DatabaseManager()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница (редирект на статический сайт)"""
    return RedirectResponse(url="/index.html")

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
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state")
    
    try:
        # Обмен кода на токен
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_response = requests.post(TOKEN_URL, data=token_data, headers=headers, timeout=10)
        
        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            raise HTTPException(status_code=400, detail="Token exchange failed")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Получение информации о пользователе
        user_headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get(USERINFO_URL, headers=user_headers, timeout=10)
        
        if user_response.status_code != 200:
            logger.error(f"User info request failed: {user_response.text}")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_info = user_response.json()
        
        # Сохранение данных пользователя
        db_manager.save_user_auth(state, user_info)
        
        logger.info(f"User {state} successfully authorized via Gosuslugi")
        
        # Успешная страница
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>Авторизация успешна</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .success {{ color: #4CAF50; }}
                        .info {{ background: #f0f8ff; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 400px; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">✅ Авторизация успешна!</h1>
                    <div class="info">
                        <p>Добро пожаловать, <strong>{user_info.get('fullName', 'Пользователь')}</strong>!</p>
                        <p>Ваш аккаунт успешно связан с ботом Энергосбыт.</p>
                        <p>Теперь вы можете вернуться к боту для получения расширенных возможностей.</p>
                    </div>
                    <p><a href="https://t.me/your_bot_username" style="color: #0088cc; text-decoration: none; font-weight: bold;">🤖 Вернуться к боту</a></p>
                </body>
            </html>
            """
        )
        
    except requests.RequestException as e:
        logger.error(f"Network error during OAuth: {e}")
        raise HTTPException(status_code=500, detail="Network error during authorization")
    except Exception as e:
        logger.error(f"Unexpected error during OAuth: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/subscribe")
async def subscribe_email(subscription: EmailSubscription):
    """API для подписки на email рассылку"""
    try:
        success = db_manager.add_email_subscription(subscription.email)
        
        if success:
            logger.info(f"New email subscription: {subscription.email}")
            return {"status": "success", "message": "Подписка успешно оформлена"}
        else:
            return {"status": "info", "message": "Этот email уже подписан на рассылку"}
            
    except Exception as e:
        logger.error(f"Error subscribing email {subscription.email}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при оформлении подписки")

@app.get("/api/user/{telegram_id}")
async def get_user_info(telegram_id: str):
    """Получение информации о пользователе по Telegram ID"""
    user = db_manager.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Убираем чувствительные данные
    safe_user = {
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "is_verified": bool(user.get("gosuslugi_id")),
        "created_at": user.get("created_at")
    }
    
    return safe_user

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Энергосбыт Backend API"
    }

@app.post("/api/readings")
async def submit_reading(request: Request):
    """API для передачи показаний от Mini App"""
    try:
        data = await request.json()
        telegram_id = data.get('telegram_id')
        reading_value = data.get('reading_value')
        user_data = data.get('user_data', {})
        
        if not telegram_id or not reading_value:
            raise HTTPException(status_code=400, detail="Не указаны обязательные данные")
        
        # Сохранение показания в базу данных
        conn = sqlite3.connect("readings.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO meter_readings (user_id, reading_value, submission_method)
            VALUES (?, ?, 'mini_app')
        ''', (str(telegram_id), int(reading_value)))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Reading submitted: user {telegram_id}, value {reading_value}")
        
        return {
            "status": "success",
            "message": "Показания успешно переданы",
            "reading_id": cursor.lastrowid,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error submitting reading: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения показаний")

@app.get("/api/readings/{telegram_id}")
async def get_readings_history(telegram_id: str):
    """Получение истории показаний пользователя"""
    try:
        conn = sqlite3.connect("readings.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT reading_value, reading_date, submission_method, status
            FROM meter_readings 
            WHERE user_id = ? 
            ORDER BY reading_date DESC 
            LIMIT 12
        ''', (telegram_id,))
        
        readings = []
        for row in cursor.fetchall():
            readings.append({
                "value": row[0],
                "date": row[1],
                "method": row[2],
                "status": row[3]
            })
        
        conn.close()
        
        return readings
        
    except Exception as e:
        logger.error(f"Error getting readings for user {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения истории")

@app.get("/api/stats")
async def get_stats():
    """Получение базовой статистики"""
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Количество авторизованных пользователей
        cursor.execute("SELECT COUNT(*) FROM auth_users")
        auth_users_count = cursor.fetchone()[0]
        
        # Количество подписчиков
        cursor.execute("SELECT COUNT(*) FROM email_subscriptions WHERE is_active = TRUE")
        subscribers_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "authorized_users": auth_users_count,
            "email_subscribers": subscribers_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")

# Статические файлы (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    
    print("🌐 Запуск FastAPI сервера...")
    print(f"📱 Redirect URI: {REDIRECT_URI}")
    print("🔗 Веб-портал будет доступен по адресу: http://0.0.0.0:5000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=False,
        access_log=True
    )
