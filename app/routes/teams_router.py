from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Team
from app.services.team_service import get_team_by_id, get_all_teams

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/{team_id}", response_class=HTMLResponse)
async def get_team(request: Request, team_id: int, db: Session = Depends(get_db)):
    team = get_team_by_id(db, team_id)
    if team:
        return templates.TemplateResponse("team.html", {"request": request, "team": team})
    raise HTTPException(status_code=404, detail="Команда не найдена")

@router.get("/", response_class=HTMLResponse)
async def list_teams(request: Request, db: Session = Depends(get_db)):
    teams = get_all_teams(db)
    return templates.TemplateResponse("teams.html", {"request": request, "teams": teams})
