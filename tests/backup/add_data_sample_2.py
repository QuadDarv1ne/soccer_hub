import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Team, Player, Match, Goal, Base
from dotenv import load_dotenv

# Загрузите переменные окружения из файла .env
load_dotenv()

# Получите значения переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем движок для подключения к базе данных
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Список команд для поиска
teams_info = [
    ("Зенит", "Санкт-Петербург", 1925, "Газпром Арена"),
    ("Спартак", "Москва", 1922, "Открытие Арена"),
    ("ЦСКА", "Москва", 1911, "ВЭБ Арена"),
    ("Локомотив", "Москва", 1922, "РЖД Арена"),
    ("Краснодар", "Краснодар", 2008, "Стадион Краснодар"),
    ("Динамо", "Москва", 1923, "ВТБ Арена"),
    ("Рубин", "Казань", 1958, "Казань Арена"),
    ("Ростов", "Ростов-на-Дону", 1930, "Ростов Арена"),
    ("Ахмат", "Грозный", 1946, "Ахмат Арена"),
    ("Сочи", "Сочи", 2018, "Фишт"),
    ("Урал", "Екатеринбург", 1930, "Центральный стадион"),
    ("Арсенал", "Тула", 1946, "Арсенал"),
    ("Химки", "Химки", 1997, "Арена Химки"),
    ("Оренбург", "Оренбург", 1976, "Газовик"),
    ("Тамбов", "Тамбов", 2013, "Спартак"),
    ("Ротор", "Волгоград", 1929, "Волгоград Арена"),
    ("Уфа", "Уфа", 2010, "Нефтяник"),
    ("Торпедо", "Москва", 1924, "Эдуард Стрельцов"),
    ("Чертаново", "Москва", 1993, "Академия Чертаново")
]

# Функция для парсинга данных о командах
def parse_teams():
    teams = []
    for team_name, city, founded, stadium in teams_info:
        url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={team_name.replace(' ', '+')}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            logger.error(f"Не удалось получить результаты поиска для {team_name}: {response.status_code}")
            continue
        soup = BeautifulSoup(response.content, 'html.parser')
        team_page = soup.find('a', class_='vereinprofil_tooltip')
        if team_page:
            team_url = "https://www.transfermarkt.com" + team_page['href']
            teams.append((team_name, city, founded, stadium, team_url))
            logger.debug(f"Найдена команда: {team_name}")
    logger.info(f"Парсинг завершен, найдено {len(teams)} команд")
    return teams

# Функция для парсинга данных о игроках команды
def parse_players(team_url):
    response = requests.get(team_url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        logger.error(f"Не удалось получить игроков с {team_url}: {response.status_code}")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    players = []
    for player in soup.select('.items .spielprofil_tooltip'):
        player_name = player.text.strip()
        player_url = 'https://www.transfermarkt.com' + player['href']
        players.append((player_name, player_url))
        logger.debug(f"Найден игрок: {player_name}")
    logger.info(f"Парсинг завершен, найдено {len(players)} игроков с {team_url}")
    return players

# Функция для парсинга данных о прошедших матчах
def parse_matches():
    url = 'https://www.transfermarkt.com/premier-liga/spieltag/wettbewerb/RU1'
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        logger.error(f"Не удалось получить матчи: {response.status_code}")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    matches = []
    for match in soup.select('.ergebnis-link'):
        match_url = 'https://www.transfermarkt.com' + match['href']
        matches.append(match_url)
        logger.debug(f"Найден URL матча: {match_url}")
    logger.info(f"Парсинг завершен, найдено {len(matches)} матчей")
    return matches

# Функция для сохранения данных в базу данных
def save_data():
    with SessionLocal() as session:
        try:
            teams = parse_teams()
            if not teams:
                logger.error("Команды не найдены")
                return

            for team_name, city, founded, stadium, team_url in teams:
                team_photo = parse_team_photo(team_name)
                team = Team(name=team_name, city=city, founded=founded, stadium=stadium, url_photo=team_photo)
                session.add(team)
                session.commit()
                team_id = team.id
                logger.info(f"Добавлена команда: {team_name} с ID {team_id}")
                
                players = parse_players(team_url)
                if not players:
                    logger.warning(f"Игроки не найдены для команды {team_name}")
                    continue

                for player_name, player_url in players:
                    player_photo = parse_player_photo(player_name)
                    player = Player(name=player_name, team_id=team_id, url_photo=player_photo)
                    session.add(player)
                    session.commit()
                    logger.info(f"Добавлен игрок: {player_name} в команду с ID {team_id}")

            match_urls = parse_matches()
            if not match_urls:
                logger.error("Матчи не найдены")
                return

            for match_url in match_urls:
                response = requests.get(match_url, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code != 200:
                    logger.error(f"Не удалось получить детали матча с {match_url}: {response.status_code}")
                    continue
                soup = BeautifulSoup(response.content, 'html.parser')
                home_team_name = soup.select_one('.sb-heim').text.strip()
                away_team_name = soup.select_one('.sb-gast').text.strip()
                home_team = session.query(Team).filter_by(name=home_team_name).first()
                away_team = session.query(Team).filter_by(name=away_team_name).first()
                if not home_team or not away_team:
                    logger.warning(f"Не удалось найти команды: {home_team_name}, {away_team_name}")
                    continue
                date_str = soup.select_one('.sb-datum').text.strip()
                date = datetime.strptime(date_str, '%d/%m/%Y')
                home_score = int(soup.select_one('.sb-endstand').text.split(':')[0].strip())
                away_score = int(soup.select_one('.sb-endstand').text.split(':')[1].strip())
                match = Match(home_team_id=home_team.id, away_team_id=away_team.id, date=date, home_score=home_score, away_score=away_score)
                session.add(match)
                session.commit()
                logger.info(f"Добавлен матч: {home_team_name} против {away_team_name} на {date} с результатом {home_score}:{away_score}")

            logger.info("Все данные успешно добавлены")
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка: {e}")
            raise

def parse_team_photo(team_name):
    try:
        url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={team_name.replace(' ', '+')}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            logger.error(f"Не удалось получить фото команды для {team_name}: {response.status_code}")
            return None
        soup = BeautifulSoup(response.content, 'html.parser')
        team_page = soup.find('a', class_='vereinprofil_tooltip')
        if team_page:
            team_url = "https://www.transfermarkt.com" + team_page['href']
            response = requests.get(team_url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                logger.error(f"Не удалось получить страницу команды для {team_name}: {response.status_code}")
                return None
            soup = BeautifulSoup(response.content, 'html.parser')
            logo = soup.find('div', class_='dataBild').find('img')
            return logo['src'] if logo else None
        return None
    except Exception as e:
        logger.error(f"Ошибка при парсинге фото команды для {team_name}: {e}")
        return None

def parse_player_photo(player_name):
    try:
        url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={player_name.replace(' ', '+')}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            logger.error(f"Не удалось получить фото игрока для {player_name}: {response.status_code}")
            return None
        soup = BeautifulSoup(response.content, 'html.parser')
        player_page = soup.find('a', class_='spielprofil_tooltip')
        if player_page:
            player_url = "https://www.transfermarkt.com" + player_page['href']
            response = requests.get(player_url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                logger.error(f"Не удалось получить страницу игрока для {player_name}: {response.status_code}")
                return None
            soup = BeautifulSoup(response.content, 'html.parser')
            photo = soup.find('div', class_='dataBild').find('img')
            return photo['src'] if photo else None
        return None
    except Exception as e:
        logger.error(f"Ошибка при парсинге фото игрока для {player_name}: {e}")
        return None

if __name__ == "__main__":
    save_data()
