from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, UniqueConstraint, Enum as SQLAEnum
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PositionEnum(str, Enum):
    """Перечисление для позиций игроков."""
    FORWARD = "Forward"
    MIDFIELDER = "Midfielder"
    DEFENDER = "Defender"
    GOALKEEPER = "Goalkeeper"


class Team(Base):
    """
    Модель команды, включающая информацию о названии, городе, дате основания и стадионе.
    """
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    city = Column(String, index=True)
    founded = Column(Integer)  # Год основания
    stadium = Column(String)   # Стадион
    points = Column(Integer, default=0)
    url_photo = Column(String, nullable=True)  # URL фотографии

    # Связь с игроками
    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, city={self.city}, url_photo={self.url_photo})>"


class Match(Base):
    """
    Модель матча, связывающая команды, дату и результаты.
    """
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)

    home_team = relationship('Team', foreign_keys=[home_team_id], backref=backref('home_matches', cascade='all, delete-orphan'))
    away_team = relationship('Team', foreign_keys=[away_team_id], backref=backref('away_matches', cascade='all, delete-orphan'))
    goals = relationship("Goal", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('home_team_id', 'away_team_id', 'date', name='unique_match_constraint'),)

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, home_team_id={self.home_team_id}, away_team_id={self.away_team_id}, date={self.date})>"


class Player(Base):
    """
    Модель игрока, включая информацию о имени, позиции и команде.
    """
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(SQLAEnum(PositionEnum), nullable=False)
    goals = Column(Integer, default=0)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    url_photo = Column(String, nullable=True)
    is_starter = Column(Boolean, default=True)  # Новое поле для указания, является ли игрок основным

    team = relationship("Team", back_populates="players")
    goals_scored = relationship("Goal", back_populates="player", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('name', 'team_id', name='unique_player_in_team'),)

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name={self.name}, position={self.position}, team_id={self.team_id}, is_starter={self.is_starter})>"


class Goal(Base):
    """
    Модель гола, связывающая матчи и игроков.
    """
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    minute = Column(Integer, nullable=False)

    match = relationship("Match", back_populates="goals")
    player = relationship("Player", back_populates="goals_scored")

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, match_id={self.match_id}, player_id={self.player_id}, minute={self.minute})>"


class ActionLog(Base):
    """
    Лог действий пользователя.
    """
    __tablename__ = 'action_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="action_logs")

    def __repr__(self) -> str:
        return f"<ActionLog(id={self.id}, user_id={self.user_id}, action={self.action}, timestamp={self.timestamp})>"


class User(Base):
    """
    Модель пользователя, содержащая информацию о логине и пароле.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    action_logs = relationship("ActionLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
