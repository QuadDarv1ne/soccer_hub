import json
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, select, text
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.db.models import Team, Player, Match, Goal, Base
from app.core.config import DATABASE_URL  # Предполагается, что DATABASE_URL загружается из .env файла
import logging
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение значения DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Создаем асинхронный движок для подключения к базе данных
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Универсальная функция для парсинга изображений (команд и игроков)
async def parse_image(url, css_class, http_session):
    try:
        async with http_session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            image_div = soup.find('div', class_=css_class)
            if image_div:
                image_tag = image_div.find('img')
                if image_tag:
                    return image_tag.get('src')
        return None
    except Exception as e:
        logger.error(f"Ошибка при парсинге изображения с URL {url}: {e}")
        return None

# Функции для парсинга данных
async def parse_team_photo(team_name, http_session):
    search_url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={team_name.replace(' ', '+')}"
    return await parse_image(search_url, 'vereinprofil_tooltip', http_session)

async def parse_player_photo(player_name, http_session):
    search_url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={player_name.replace(' ', '+')}"
    return await parse_image(search_url, 'spielprofil_tooltip', http_session)

# Функции для добавления записей
async def add_team(session, name, city, founded, stadium, http_session):
    existing_team = await session.execute(select(Team).where(Team.name == name))
    if existing_team.scalars().first():
        logger.warning(f"Team {name} already exists")
        return

    url_photo = await parse_team_photo(name, http_session)
    team = Team(name=name, city=city, founded=founded, stadium=stadium, url_photo=url_photo)
    session.add(team)
    logger.info(f"Added team: {team.name}")

async def add_player(session, name, position, team_id, goals, is_starter, http_session):
    existing_player = await session.execute(select(Player).where(Player.name == name, Player.team_id == team_id))
    if existing_player.scalars().first():
        logger.warning(f"Player {name} already exists in team ID {team_id}")
        return

    url_photo = await parse_player_photo(name, http_session)
    player = Player(name=name, position=position, team_id=team_id, goals=goals, url_photo=url_photo, is_starter=is_starter)
    session.add(player)
    logger.info(f"Added player: {player.name} to team ID {team_id}")

async def add_match(session, home_team_id, away_team_id, date, home_score, away_score):
    match = Match(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        date=date,
        home_score=home_score,
        away_score=away_score
    )
    session.add(match)
    logger.info(f"Added match on {match.date} between teams {home_team_id} and {away_team_id}")

async def add_goal(session, match_id, player_id, minute):
    goal = Goal(match_id=match_id, player_id=player_id, minute=minute)
    session.add(goal)
    logger.info(f"Added goal: Match ID {match_id}, Player ID {player_id}, Minute {minute}")

# Функция для сохранения данных в файлы JSON
async def save_to_json(session):
    # Сохранение данных команд
    result = await session.execute(text("SELECT * FROM teams"))
    teams = result.scalars().all()
    teams_data = [{
        "id": team.id,
        "name": team.name,
        "city": team.city,
        "founded": team.founded,
        "stadium": team.stadium,
        "points": team.points,
        "url_photo": team.url_photo
    } for team in teams]
    
    with open('teams.json', 'w', encoding='utf-8') as f:
        json.dump(teams_data, f, ensure_ascii=False, indent=4)
    logger.info("Teams data saved to teams.json")
    
    # Сохранение данных игроков
    result = await session.execute(text("SELECT * FROM players"))
    players = result.scalars().all()
    players_data = [{
        "id": player.id,
        "name": player.name,
        "position": player.position,
        "goals": player.goals,
        "team_id": player.team_id,
        "url_photo": player.url_photo,
        "is_starter": player.is_starter
    } for player in players]
    
    with open('players.json', 'w', encoding='utf-8') as f:
        json.dump(players_data, f, ensure_ascii=False, indent=4)
    logger.info("Players data saved to players.json")
    
    # Сохранение данных матчей
    result = await session.execute(text("SELECT * FROM matches"))
    matches = result.scalars().all()
    matches_data = [{
        "id": match.id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "date": match.date.strftime('%Y-%m-%d %H:%M:%S'),
        "home_score": match.home_score,
        "away_score": match.away_score
    } for match in matches]
    
    with open('matches.json', 'w', encoding='utf-8') as f:
        json.dump(matches_data, f, ensure_ascii=False, indent=4)
    logger.info("Matches data saved to matches.json")
    
    # Сохранение данных голов
    result = await session.execute(text("SELECT * FROM goals"))
    goals = result.scalars().all()
    goals_data = [{
        "id": goal.id,
        "match_id": goal.match_id,
        "player_id": goal.player_id,
        "minute": goal.minute
    } for goal in goals]
    
    with open('goals.json', 'w', encoding='utf-8') as f:
        json.dump(goals_data, f, ensure_ascii=False, indent=4)
    logger.info("Goals data saved to goals.json")

# Добавление данных в базу
async def add_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session, aiohttp.ClientSession() as http_session:
        try:
            # Данные команд
            teams_data = [
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
        
            # Данные игроков
            players_data = [
                # Зенит
                ("Артем Дзюба", "Forward", 1, 10, True),
                ("Вилмар Барриос", "Midfielder", 1, 5, True),
                ("Малком", "Forward", 1, 8, True),
                ("Далер Кузяев", "Midfielder", 1, 4, True),
                ("Деян Ловрен", "Defender", 1, 1, True),
                ("Сердар Азмун", "Forward", 1, 9, True),
                ("Андрей Лунев", "Goalkeeper", 1, 0, False),
                ("Александр Ерохин", "Midfielder", 1, 2, False),
                ("Юрий Жирков", "Defender", 1, 3, False),
                ("Себастьян Дриусси", "Forward", 1, 7, False),
                ("Дмитрий Чистяков", "Defender", 1, 0, False),
                ("Дмитрий Шомко", "Defender", 1, 0, False),
                ("Михаил Кержаков", "Goalkeeper", 1, 0, False),
                ("Дмитрий Скопинцев", "Defender", 1, 0, False),
                
                # Спартак
                ("Александр Соболев", "Forward", 2, 6, True),
                ("Зелимхан Бакаев", "Midfielder", 2, 7, True),
                ("Джордан Ларссон", "Forward", 2, 9, True),
                ("Георгий Джикия", "Defender", 2, 1, True),
                ("Илья Кутепов", "Defender", 2, 2, False),
                ("Роман Зобнин", "Midfielder", 2, 3, True),
                ("Александр Максименко", "Goalkeeper", 2, 0, True),
                ("Александр Ташаев", "Midfielder", 2, 3, False),
                
                # ЦСКА
                ("Федор Чалов", "Forward", 3, 4, True),
                ("Игорь Акинфеев", "Goalkeeper", 3, 0, True),
                ("Никола Влашич", "Midfielder", 3, 3, True),
                ("Марио Фернандес", "Defender", 3, 1, True),
                ("Ильзат Ахметов", "Midfielder", 3, 2, True),
                ("Константин Марадишвили", "Midfielder", 3, 2, False),
                ("Вадим Карпов", "Defender", 3, 0, False),
                
                # Локомотив
                ("Антон Миранчук", "Midfielder", 4, 2, True),
                ("Гжегож Крыховяк", "Midfielder", 4, 1, True),
                ("Эдер", "Forward", 4, 3, False),  # Запасной
                ("Мацей Рыбус", "Defender", 4, 0, True),
                ("Соломон Квирквелия", "Defender", 4, 1, False),
                ("Дмитрий Баринов", "Midfielder", 4, 2, True),
                ("Маринато Гилерме", "Goalkeeper", 4, 0, True),
                
                # Краснодар
                ("Маркус Берг", "Forward", 5, 5, False),  # Запасной
                ("Реми Кабелла", "Midfielder", 5, 4, True),
                ("Юрий Газинский", "Midfielder", 5, 2, True),
                ("Ари", "Forward", 5, 3, True),
                ("Кристиан Рамирес", "Defender", 5, 1, True),
                ("Евгений Чернов", "Defender", 5, 0, False),
                ("Матвей Сафонов", "Goalkeeper", 5, 0, True),
                
                # Сочи
                ("Клинтон Н'Жи", "Forward", 6, 1, True),
                ("Александр Ташаев", "Midfielder", 6, 3, False),  # Запасной
                ("Эммануэль Маммана", "Defender", 6, 1, True),
                ("Андрей Мостовой", "Midfielder", 6, 2, True),
                ("Сергей Терехов", "Defender", 6, 0, False),
                ("Сослан Джанаев", "Goalkeeper", 6, 0, True),
                
                # Ростов
                ("Георгий Махатадзе", "Midfielder", 7, 1, True),
                ("Александр Гацкан", "Midfielder", 7, 2, True),
                ("Егор Сорокин", "Defender", 7, 1, True),
                ("Александр Трошечкин", "Midfielder", 7, 2, False),
                ("Максим Осипенко", "Defender", 7, 0, False),
                ("Сергей Песьяков", "Goalkeeper", 7, 0, True),
                
                # Ахмат
                ("Дмитрий Полоз", "Forward", 8, 3, True),
                ("Бернард Бериша", "Forward", 8, 2, True),
                ("Идрисс Диалло", "Defender", 8, 1, True),
                ("Исмаил Силла", "Midfielder", 8, 2, False),
                ("Александр Бутенко", "Defender", 8, 0, False),
                ("Александр Мельников", "Goalkeeper", 8, 0, True),
                
                # Рубин
                ("Бернард Бериша", "Forward", 9, 2, True),
                ("Алексей Сутормин", "Midfielder", 9, 2, True),
                ("Егор Сорокин", "Defender", 9, 1, True),
                ("Сильвие Бегич", "Defender", 9, 0, False),
                ("Андрей Лунев", "Goalkeeper", 9, 0, True),
                ("Дмитрий Тарасов", "Midfielder", 9, 1, False),
                ("Игорь Коновалов", "Midfielder", 9, 1, True),
                
                # Урал
                ("Алексей Помазун", "Goalkeeper", 10, 0, True),
                ("Владимир Гранат", "Defender", 10, 1, True),
                ("Никита Чернов", "Defender", 10, 0, False),
                ("Эрик Бикфалви", "Midfielder", 10, 2, True),
                ("Андрей Панюков", "Forward", 10, 3, True),
                ("Михаил Меркулов", "Defender", 10, 0, False),
                ("Сергей Прядкин", "Midfielder", 10, 1, True),
                
                # Урал
                ("Алексей Помазун", "Goalkeeper", 10, 0, True),
                ("Владимир Гранат", "Defender", 10, 1, True),
                ("Алексей Евсеев", "Midfielder", 10, 2, True),
                ("Роман Емельянов", "Midfielder", 10, 3, True),
                ("Дмитрий Жиронкин", "Forward", 10, 2, True),
                ("Александр Семакин", "Defender", 10, 0, True),
                ("Александр Прудников", "Forward", 10, 3, True),
                ("Игорь Портнягин", "Forward", 10, 1, True),
                ("Владислав Игнатьев", "Midfielder", 10, 1, True),
                ("Кирилл Панченко", "Forward", 10, 2, False),
                
                # Арсенал
                ("Сергей Ткачев", "Midfielder", 11, 1, True),
                ("Александр Ломовицкий", "Midfielder", 11, 3, True),
                ("Дмитрий Комбаров", "Defender", 11, 1, True),
                ("Алексей Грицаенко", "Defender", 11, 0, True),
                ("Александр Ковалев", "Goalkeeper", 11, 0, True),
                ("Игорь Смольников", "Defender", 11, 0, True),
                ("Сергей Рыжиков", "Goalkeeper", 11, 0, True),
                ("Андрей Панюков", "Forward", 11, 3, True),
                ("Дмитрий Скопинцев", "Defender", 11, 0, True),
                ("Максим Беляев", "Defender", 11, 0, False),
                
                # Химки
                ("Дмитрий Кузнецов", "Forward", 12, 3, False),  # Запасной
                ("Егор Голенков", "Forward", 12, 4, True),
                ("Андрей Мищенко", "Defender", 12, 2, True),
                ("Илья Кухарчук", "Midfielder", 12, 3, True),
                ("Александр Филин", "Defender", 12, 0, False),  # Запасной
                ("Игорь Дивеев", "Defender", 12, 1, True),

                # Оренбург
                ("Андрей Ещенко", "Defender", 13, 0, True),
                ("Денис Ткачук", "Midfielder", 13, 1, True),
                ("Александр Прудников", "Forward", 13, 2, True),
                ("Павел Нехайчик", "Midfielder", 13, 3, False),  # Запасной
                ("Андрей Малых", "Defender", 13, 0, False),  # Запасной
                ("Михаил Сиваков", "Midfielder", 13, 1, True),

                # Тамбов
                ("Петр Нечаев", "Midfielder", 14, 1, True),
                ("Александр Селихов", "Goalkeeper", 14, 0, True),
                ("Максим Трусевич", "Defender", 14, 0, False),  # Запасной
                ("Артем Федоров", "Forward", 14, 2, True),
                ("Дмитрий Каменщиков", "Midfielder", 14, 1, False),  # Запасной
                ("Иван Рыжов", "Midfielder", 14, 1, True),

                # Ротор
                ("Алексей Сапогов", "Forward", 15, 3, True),
                ("Андрей Тихонов", "Midfielder", 15, 2, True),
                ("Сергей Паршивлюк", "Defender", 15, 1, True),
                ("Денис Глушаков", "Midfielder", 15, 1, False),  # Запасной
                ("Артем Мамин", "Defender", 15, 0, False),  # Запасной
                ("Игорь Горбатенко", "Midfielder", 15, 1, True),

                # Уфа
                ("Денис Терентьев", "Defender", 16, 0, True),
                ("Александр Кучеров", "Midfielder", 16, 1, True),
                ("Иван Олейников", "Forward", 16, 2, True),
                ("Михаил Бородин", "Goalkeeper", 16, 0, False),  # Запасной
                ("Евгений Осипов", "Defender", 16, 1, True),
                ("Александр Фомин", "Midfielder", 16, 1, False),  # Запасной

                # Торпедо
                ("Дмитрий Сычев", "Forward", 17, 4, True),
                ("Александр Павленко", "Midfielder", 17, 2, True),
                ("Сергей Терехов", "Defender", 17, 1, True),
                ("Игорь Лебеденко", "Forward", 17, 3, False),  # Запасной
                ("Александр Рыбаков", "Midfielder", 17, 1, False),  # Запасной
                ("Андрей Канчельскис", "Midfielder", 17, 1, True),

                # Чертаново
                ("Сергей Лапочкин", "Forward", 18, 3, True),
                ("Иван Савин", "Midfielder", 18, 2, True),
                ("Дмитрий Поляков", "Defender", 18, 1, True),
                ("Алексей Кузнецов", "Goalkeeper", 18, 0, True),
                ("Максим Ковалев", "Defender", 18, 0, False),  # Запасной
                ("Владимир Воробьев", "Midfielder", 18, 1, False),  # Запасной
            ]

            # Данные матчей с правильными голами (за полгода)
            matches_data = [
                (1, 2, datetime(2024, 7, 5), 2, 1),
                (2, 3, datetime(2024, 7, 10), 1, 1),
                (3, 4, datetime(2024, 7, 15), 0, 3),
                (4, 5, datetime(2024, 7, 20), 2, 2),
                (5, 1, datetime(2024, 7, 25), 1, 4),
                (6, 7, datetime(2024, 7, 30), 0, 1),
                (7, 8, datetime(2024, 8, 5), 3, 3),
                (8, 9, datetime(2024, 8, 10), 2, 2),
                (9, 10, datetime(2024, 8, 15), 1, 1),
                (10, 6, datetime(2024, 8, 20), 1, 0),
                (1, 4, datetime(2024, 8, 25), 2, 2),
                (5, 6, datetime(2024, 8, 30), 1, 3),
                (7, 10, datetime(2024, 9, 5), 2, 1),
                (2, 9, datetime(2024, 9, 10), 3, 0),
                (1, 3, datetime(2024, 9, 15), 0, 2),
                (4, 2, datetime(2024, 9, 20), 1, 1),
                (6, 1, datetime(2024, 9, 25), 2, 3),
                (7, 5, datetime(2024, 9, 30), 1, 2),
                (8, 4, datetime(2024, 10, 5), 2, 3),
                (9, 3, datetime(2024, 10, 10), 0, 1),
                (10, 2, datetime(2024, 10, 15), 1, 2),
                (1, 7, datetime(2024, 10, 20), 3, 1),
                (5, 9, datetime(2024, 10, 25), 2, 2),
                (6, 8, datetime(2024, 10, 30), 1, 1),
                (4, 10, datetime(2024, 11, 5), 0, 3),
                (3, 6, datetime(2024, 11, 10), 1, 2),
                (2, 5, datetime(2024, 11, 15), 2, 1),
                (8, 1, datetime(2024, 11, 20), 0, 4),
                (9, 7, datetime(2024, 11, 25), 1, 1),
                (10, 4, datetime(2024, 11, 30), 2, 2),
                (1, 8, datetime(2024, 12, 5), 3, 0),
                (5, 2, datetime(2024, 12, 10), 1, 2),
                (6, 3, datetime(2024, 12, 15), 0, 1),
                (7, 9, datetime(2024, 12, 20), 2, 3),
                (4, 1, datetime(2024, 12, 25), 1, 2),
                (2, 6, datetime(2024, 12, 30), 3, 1),
            ]

            # Данные голов
            goals_data = [
                (1, 10, 15),  # Матч 1, игрок 10, 15-я минута
                (1, 11, 35),  # Матч 1, игрок 11, 35-я минута
                (2, 12, 20),  # Матч 2, игрок 12, 20-я минута
                (2, 13, 60),  # Матч 2, игрок 13, 60-я минута
                (3, 14, 10),  # Матч 3, игрок 14, 10-я минута
                (3, 15, 45),  # Матч 3, игрок 15, 45-я минута
                (3, 16, 80),  # Матч 3, игрок 16, 80-я минута
                (4, 17, 30),  # Матч 4, игрок 17, 30-я минута
                (4, 18, 55),  # Матч 4, игрок 18, 55-я минута
                (4, 19, 70),  # Матч 4, игрок 19, 70-я минута
                (5, 20, 25),  # Матч 5, игрок 20, 25-я минута
                (5, 21, 50),  # Матч 5, игрок 21, 50-я минута
                (5, 22, 75),  # Матч 5, игрок 22, 75-я минута
                (6, 23, 40),  # Матч 6, игрок 23, 40-я минута
                (6, 24, 85),  # Матч 6, игрок 24, 85-я минута
                (7, 25, 15),  # Матч 7, игрок 25, 15-я минута
                (7, 26, 45),  # Матч 7, игрок 26, 45-я минута
                (7, 27, 65),  # Матч 7, игрок 27, 65-я минута
                (8, 28, 30),  # Матч 8, игрок 28, 30-я минута
                (8, 29, 70),  # Матч 8, игрок 29, 70-я минута
                (9, 30, 25),  # Матч 9, игрок 30, 25-я минута
                (9, 31, 55),  # Матч 9, игрок 31, 55-я минута
                (10, 32, 35), # Матч 10, игрок 32, 35-я минута
                (10, 33, 65), # Матч 10, игрок 33, 65-я минута
                (11, 34, 20), # Матч 11, игрок 34, 20-я минута
                (11, 35, 50), # Матч 11, игрок 35, 50-я минута
                (12, 36, 25), # Матч 12, игрок 36, 25-я минута
                (12, 37, 75), # Матч 12, игрок 37, 75-я минута
                (13, 38, 30), # Матч 13, игрок 38, 30-я минута
                (13, 39, 55), # Матч 13, игрок 39, 55-я минута
                (14, 40, 15), # Матч 14, игрок 40, 15-я минута
                (14, 41, 45), # Матч 14, игрок 41, 45-я минута
                (15, 42, 35), # Матч 15, игрок 42, 35-я минута
                (15, 43, 65), # Матч 15, игрок 43, 65-я минута
                (16, 44, 10), # Матч 16, игрок 44, 10-я минута
                (16, 45, 50), # Матч 16, игрок 45, 50-я минута
                (17, 46, 25), # Матч 17, игрок 46, 25-я минута
                (17, 47, 75), # Матч 17, игрок 47, 75-я минута
                (18, 48, 30), # Матч 18, игрок 48, 30-я минута
                (18, 49, 70), # Матч 18, игрок 49, 70-я минута
                (19, 50, 10), # Матч 19, игрок 50, 10-я минута
                (19, 51, 55), # Матч 19, игрок 51, 55-я минута
                (20, 52, 20), # Матч 20, игрок 52, 20-я минута
                (20, 53, 65), # Матч 20, игрок 53, 65-я минута
                (21, 54, 25), # Матч 21, игрок 54, 25-я минута
                (21, 55, 55), # Матч 21, игрок 55, 55-я минута
                (22, 56, 35), # Матч 22, игрок 56, 35-я минута
                (22, 57, 70), # Матч 22, игрок 57, 70-я минута
                (23, 58, 15), # Матч 23, игрок 58, 15-я минута
                (23, 59, 45), # Матч 23, игрок 59, 45-я минута
                (24, 60, 35), # Матч 24, игрок 60, 35-я минута
                (24, 61, 55), # Матч 24, игрок 61, 55-я минута
                (25, 62, 10), # Матч 25, игрок 62, 10-я минута
                (25, 63, 50), # Матч 25, игрок 63, 50-я минута
                (26, 64, 20), # Матч 26, игрок 64, 20-я минута
                (26, 65, 55), # Матч 26, игрок 65, 55-я минута
                (27, 66, 30), # Матч 27, игрок 66, 30-я минута
                (27, 67, 75), # Матч 27, игрок 67, 75-я минута
                (28, 68, 25), # Матч 28, игрок 68, 25-я минута
                (28, 69, 70), # Матч 28, игрок 69, 70-я минута
                (29, 70, 15), # Матч 29, игрок 70, 15-я минута
                (29, 71, 45), # Матч 29, игрок 71, 45-я минута
                (30, 72, 35), # Матч 30, игрок 72, 35-я минута
                (30, 73, 55), # Матч 30, игрок 73, 55-я минута
                (31, 74, 10), # Матч 31, игрок 74, 10-я минута
                (31, 75, 50), # Матч 31, игрок 75, 50-я минута
                (32, 76, 20), # Матч 32, игрок 76, 20-я минута
                (32, 77, 65), # Матч 32, игрок 77, 65-я минута
                (33, 78, 25), # Матч 33, игрок 78, 25-я минута
                (33, 79, 70), # Матч 33, игрок 79, 70-я минута
                (34, 80, 15), # Матч 34, игрок 80, 15-я минута
                (34, 81, 55), # Матч 34, игрок 81, 55-я минута
                (35, 82, 20), # Матч 35, игрок 82, 20-я минута
                (35, 83, 65), # Матч 35, игрок 83, 65-я минута
                (36, 84, 25), # Матч 36, игрок 84, 25-я минута
                (36, 85, 55), # Матч 36, игрок 85, 55-я минута
            ]

            # Добавление данных в базу
            for team in teams_data:
                await add_team(session, *team, http_session)

            for player in players_data:
                await add_player(session, *player, http_session)

            for match in matches_data:
                await add_match(session, *match)

            for goal in goals_data:
                await add_goal(session, *goal)

            await session.commit()
            logger.info("All data added successfully")
            
            # Сохранение данных команд, игроков, матчей и голов в файлы JSON
            await save_to_json(session)

        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при добавлении данных: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_data())
