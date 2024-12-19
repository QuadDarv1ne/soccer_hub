from sqlalchemy.orm import Session
from app.db import models, schemas

# Получение всех матчей
def get_all_matches(db: Session):
    return db.query(models.Match).all()

# Получение матча по ID
def get_match_by_id(db: Session, match_id: int):
    return db.query(models.Match).filter(models.Match.id == match_id).first()

# Создание нового матча
def create_match(db: Session, match: schemas.MatchCreate):
    db_match = models.Match(
        home_team_id=match.home_team_id,
        away_team_id=match.away_team_id,
        date=match.date,
        home_score=match.home_score,
        away_score=match.away_score
    )
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

# Обновление существующего матча
def update_match(db: Session, match_id: int, match_data: schemas.MatchUpdate):
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        return None
    for key, value in match_data.dict(exclude_unset=True).items():
        setattr(match, key, value)
    db.commit()
    db.refresh(match)
    return match

# Удаление матча
def delete_match(db: Session, match_id: int):
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if match:
        db.delete(match)
        db.commit()
        return match
    return None
