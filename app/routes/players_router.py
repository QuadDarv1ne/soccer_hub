from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Player
from app.services.player_service import get_player_by_id, get_all_players

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/{player_id}", response_class=HTMLResponse)
async def get_player(request: Request, player_id: int, db: Session = Depends(get_db)):
    player = get_player_by_id(db, player_id)
    if player:
        return templates.TemplateResponse("player.html", {"request": request, "player": player})
    raise HTTPException(status_code=404, detail="Игрок не найден")

@router.get("/", response_class=HTMLResponse)
async def list_players(request: Request, db: Session = Depends(get_db)):
    players = get_all_players(db)
    return templates.TemplateResponse("players.html", {"request": request, "players": players})