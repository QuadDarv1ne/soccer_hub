from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import Match, Player, Team

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def analytics_page(request: Request, db: Session = Depends(get_db)):
    top_teams = db.query(Team).order_by(Team.points.desc()).limit(10).all()
    top_scorers = db.query(Player).order_by(Player.goals.desc()).limit(10).all()
    total_goals = db.query(func.sum(Match.home_score + Match.away_score)).scalar() or 0
    total_matches = db.query(Match).count()
    avg_goals_per_match = (total_goals / total_matches) if total_matches > 0 else 0

    match_stats = {
        'total_goals': total_goals,
        'total_matches': total_matches,
        'avg_goals_per_match': avg_goals_per_match,
    }

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "top_teams": top_teams,
        "top_scorers": top_scorers,
        "match_stats": match_stats,
    })