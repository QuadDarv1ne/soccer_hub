import logging
import traceback
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import engine, Base, get_db
from app.db.models import Match, Player, Team
from app.routes import teams_router, matches_router, analytics_router, players_router
from app.core.config import Settings

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Создание экземпляра FastAPI
app = FastAPI(title="Soccer Hub API")
templates = Jinja2Templates(directory="app/templates")

# Получение настроек из класса Settings
settings = Settings()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"],  # Можно ограничить, если нужно
)

# Подключение маршрутов
app.include_router(teams_router, prefix="/teams", tags=["Команды"])
app.include_router(matches_router, prefix="/matches", tags=["Матчи"])
app.include_router(analytics_router, prefix="/analytics", tags=["Аналитика"])
app.include_router(players_router, prefix="/players", tags=["Игроки"])

# Обработка ошибки валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Ошибка валидации: {exc.errors()} на запросе: {await request.json()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# Обработка ошибки SQLAlchemy
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Ошибка базы данных: {exc} на запросе: {await request.json()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ошибка базы данных. Пожалуйста, попробуйте позже."},
    )

# Создание таблиц базы данных
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("База данных инициализирована.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Приложение завершает работу.")

# Основной маршрут
@app.get("/", response_class=HTMLResponse, summary="Главная страница")
async def root(request: Request) -> HTMLResponse:
    logger.info("Запрос к главной странице.")
    return templates.TemplateResponse("index.html", {"request": request})

# Страница команд
@app.get("/teams", response_class=HTMLResponse, summary="Команды")
async def teams_page(request: Request, db: Session = Depends(get_db)):
    teams = db.query(Team).all()  # Получаем все команды из базы данных
    logger.info(f"Найдено {len(teams)} команд.")
    return templates.TemplateResponse("teams.html", {"request": request, "teams": teams})

# Страница матчей
@app.get("/matches", response_class=HTMLResponse, summary="Матчи")
async def matches_page(request: Request, db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    logger.info(f"Найдено {len(matches)} матчей.")
    return templates.TemplateResponse("matches.html", {"request": request, "matches": matches})

# Страница игроков
@app.get("/players", response_class=HTMLResponse, summary="Игроки")
async def get_players(request: Request, db: Session = Depends(get_db)):
    players = db.query(Player).all()  # Получаем всех игроков
    logger.info(f"Найдено {len(players)} игроков.")
    return templates.TemplateResponse("players.html", {"request": request, "players": players})

@app.get("/analytics", response_class=HTMLResponse, summary="Аналитика")
async def analytics_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    logger.info("Запрос к странице аналитики.")
    
    top_teams = []
    top_scorers = []
    match_stats = {}

    try:
        # Получаем топ команд
        top_teams = db.query(Team).order_by(Team.points.desc()).limit(10).all()

        # Получаем топ бомбардиров
        top_scorers = db.query(Player).order_by(Player.goals.desc()).limit(10).all()

        # Получаем статистику матчей
        total_goals = db.query(func.sum(Match.home_score + Match.away_score)).scalar() or 0
        total_matches = db.query(Match).count()
        avg_goals_per_match = (total_goals / total_matches) if total_matches > 0 else 0

        match_stats = {
            'total_goals': total_goals,
            'total_matches': total_matches,
            'avg_goals_per_match': avg_goals_per_match,
        }
        
        logger.info(f"Статистика матчей: {match_stats}")

    except Exception as e:
        logger.error(f"Ошибка при получении данных для аналитики: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Ошибка при получении данных аналитики.")

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "top_teams": top_teams,
        "top_scorers": top_scorers,
        "match_stats": match_stats,
        "no_teams": len(top_teams) == 0,  # Добавляем флаг для проверки отсутствия команд
        "no_scorers": len(top_scorers) == 0,  # Флаг для проверки отсутствия бомбардиров
    })
