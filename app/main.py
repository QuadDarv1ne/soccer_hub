from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import engine, Base
from app.routes import teams, matches
from app.core.config import settings
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание экземпляра FastAPI
app = FastAPI(title="Soccer Hub API")

# Настройка CORS
origins = [
    "http://localhost:3000",
    "https://your-frontend-url.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(teams.router, prefix="/teams", tags=["Команды"])
app.include_router(matches.router, prefix="/matches", tags=["Матчи"])

# Обработка ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(f"Ошибка валидации: {exc.errors()} на запросе: {await request.json()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# Обработка ошибок базы данных
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
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
@app.get("/", summary="Главная страница")
async def root():
    return {"message": "Добро пожаловать в Soccer Hub API!"}
