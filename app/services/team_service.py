from sqlalchemy.orm import Session
from app.db import models, schemas

# Получение команды по ID
def get_team_by_id(db: Session, team_id: int):
    return db.query(models.Team).filter(models.Team.id == team_id).first()

# Получение всех команд
def get_all_teams(db: Session):
    return db.query(models.Team).all()

# Создание новой команды
def create_team(db: Session, team: schemas.TeamCreate):
    db_team = models.Team(
        name=team.name,
        city=team.city,
        founded=team.founded,
        stadium=team.stadium
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

# Обновление существующей команды
def update_team(db: Session, team_id: int, team_data: schemas.TeamUpdate):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        return None
    for key, value in team_data.dict(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return team

# Удаление команды
def delete_team(db: Session, team_id: int):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if team:
        db.delete(team)
        db.commit()
        return team
    return None
