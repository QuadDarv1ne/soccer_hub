from fastapi import APIRouter
from app.routes import matches_router, teams_router

router = APIRouter()
router.include_router(teams_router.router)
router.include_router(matches_router.router)

from .teams_router import router as teams_router
from .matches_router import router as matches_router
from .analytics_router import router as analytics_router
from .players_router import router as players_router

# Экспортируем маршруты
__all__ = ["teams_router", "matches_router", "analytics_router", "players_router"]
