import os
import requests
import json
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Константы
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_API_BASE_URL = "https://api.football-data.org/v4"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Хелпер для выполнения HTTP-запросов
def fetch_from_api(endpoint):
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    try:
        response = requests.get(f"{FOOTBALL_DATA_API_BASE_URL}/{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе {endpoint}: {e}")
        return None

# Функция для сохранения данных в JSON
def save_to_json(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Данные успешно сохранены в {filename}")
    except IOError as e:
        logger.error(f"Ошибка при сохранении данных в {filename}: {e}")

# Функция для получения матчей турнира
def get_matches(tournament_id):
    logger.info(f"Получение данных о матчах для турнира с ID {tournament_id}...")
    data = fetch_from_api(f"competitions/{tournament_id}/matches")
    if data and "matches" in data:
        matches = data["matches"]
        save_to_json(matches, f"matches_{tournament_id}.json")
        logger.info(f"Получено {len(matches)} матчей для турнира {tournament_id}")
    else:
        logger.error(f"Нет данных о матчах для турнира с ID {tournament_id}")

# Основная функция для получения данных по всем турнирам
def main():
    tournaments = [
        {"id": 2089, "name": "Russian Cup"},
        {"id": 2088, "name": "FNL"},
        {"id": 2137, "name": "RFPL"},
        {"id": 2091, "name": "Russian Super Cup"},
        {"id": 2090, "name": "Playoffs 1/2"}
    ]

    for tournament in tournaments:
        get_matches(tournament["id"])

if __name__ == "__main__":
    main()
