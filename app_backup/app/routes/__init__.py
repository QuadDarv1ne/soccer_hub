from fastapi import APIRouter
from app.routes import matches_router, teams_router

router = APIRouter()
router.include_router(teams_router.router)
router.include_router(matches_router.router)
