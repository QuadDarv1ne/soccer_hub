from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Match
from app.services.match_service import get_all_matches, get_match_by_id

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/{match_id}", response_class=HTMLResponse)
async def get_match(request: Request, match_id: int, db: Session = Depends(get_db)):
    match = get_match_by_id(db, match_id)
    if match:
        return templates.TemplateResponse("match.html", {"request": request, "match": match})
    raise HTTPException(status_code=404, detail="Матч не найден")

@router.get("/", response_class=HTMLResponse)
async def list_matches(request: Request, db: Session = Depends(get_db)):
    matches = get_all_matches(db)
    return templates.TemplateResponse("matches.html", {"request": request, "matches": matches})