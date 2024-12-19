from sqlalchemy.orm import Session
from app.db import models, schemas

# Получение всех игроков
def get_all_players(db: Session):
    return db.query(models.Player).all()

# Получение игрока по ID
def get_player_by_id(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.id == player_id).first()

# Создание нового игрока
def create_player(db: Session, player: schemas.PlayerCreate):
    db_player = models.Player(
        name=player.name,
        position=player.position,
        goals=player.goals,
        team_id=player.team_id,
        url_photo=player.url_photo,
        is_starter=player.is_starter,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player

# Обновление существующего игрока
def update_player(db: Session, player_id: int, player_data: schemas.PlayerUpdate):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        return None
    for key, value in player_data.dict(exclude_unset=True).items():
        setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return player

# Удаление игрока
def delete_player(db: Session, player_id: int):
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if player:
        db.delete(player)
        db.commit()
        return player
    return None