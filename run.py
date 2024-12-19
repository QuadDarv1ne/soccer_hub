import uvicorn
from app.main import app
import os

def main():
    # Получение параметров из переменных окружения с указанием значений по умолчанию
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = os.getenv("RELOAD", "true").lower() == "true"

    # Запуск сервера uvicorn с указанными параметрами
    uvicorn.run(
        "app.main:app",      # Укажите путь к вашему приложению FastAPI
        host=host,           # IP-адрес, на котором будет запущен сервер
        port=port,           # Порт, на котором будет запущен сервер
        log_level=log_level, # Уровень логирования
        reload=reload        # Автоматическая перезагрузка при изменении кода
    )

if __name__ == "__main__":
    main()
