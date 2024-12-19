import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import Base  # Импортируйте свой базовый класс
from app.db.models import Team, Match, Player, ActionLog  # Импортируйте свои модели

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем базу данных и создаем движок
DATABASE_URL="sqlite+aiosqlite:///./instance/soccer_hub.db"  # Путь к вашей базе данных

def create_db():
    """Создает директорию базы данных и инициализирует базу данных."""
    # Проверяем, существует ли директория
    db_directory = os.path.dirname(DATABASE_URL.split(":///")[-1])
    if not os.path.exists(db_directory):
        os.makedirs(db_directory)
        logger.info(f"Создана директория для базы данных: {db_directory}")

    try:
        # Создаем движок базы данных
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

        # Создаем все таблицы в базе данных
        Base.metadata.create_all(bind=engine)

        logger.info("База данных и таблицы созданы успешно.")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при работе с базой данных: {e}")

if __name__ == "__main__":
    create_db()
