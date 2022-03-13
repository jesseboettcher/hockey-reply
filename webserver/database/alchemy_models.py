from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

player_team = Table(
    "player_team",
    Base.metadata,
    Column("player_id", Integer, ForeignKey("player.player_id")),
    Column("team_id", Integer, ForeignKey("team.team_id")),
)

class Player(Base):
    __tablename__ = "player"
    player_id = Column(Integer, primary_key=True)
    name = Column(String)
    teams = relationship (
        "Team", secondary=player_team, back_populates="players"
    )

class Team(Base):
    __tablename__ = "team"
    team_id = Column(Integer, primary_key=True)
    name = Column(String)
    players = relationship (
        "Player", secondary=player_team, back_populates="teams"
    )

class Game(Base):
    __tablename__ = "game"
    game_id = Column(Integer, primary_key=True)
    scheduled_time = Column(String)
    completed = Column(Integer)
    rink = Column(String)
    level = Column(String)
    home_team_id = Column(Integer, ForeignKey("team.team_id"))
    away_team_id = Column(Integer, ForeignKey("team.team_id"))
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    game_type = Column(String)
    scoresheet_html_url = Column(String)
    scoresheet_pdf_url = Column(String)
