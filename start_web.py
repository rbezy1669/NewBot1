#!/usr/bin/env python3
"""
Simplified startup script for the Energy Platform web portal
Starts only the web server on port 5000 for demonstration
"""

import os
import sys

def main():
    print("🌐 Запуск веб-портала Энергосбыт...")
    
    # Initialize databases first
    try:
        from database import DatabaseInitializer
        initializer = DatabaseInitializer()
        initializer.initialize_all()
        print("✅ Базы данных инициализированы")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации БД: {e}")
    
    # Start web server
    try:
        import uvicorn
        from backend import app
        
        print("🚀 Запуск FastAPI сервера на порту 5000...")
        print("🔗 Веб-портал: http://localhost:5000")
        print("📚 API документация: http://localhost:5000/docs")
        print()
        print("Нажмите Ctrl+C для остановки")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=5000,
            reload=False,
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()