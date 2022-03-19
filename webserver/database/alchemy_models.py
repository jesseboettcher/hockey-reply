from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

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

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("google_id"), UniqueConstraint("email"))

    user_id = Column(Integer, primary_key=True)

    external_id = Column(String, default=lambda: str(uuid.uuid4()), nullable=False)

    google_id = Column(String, nullable=True)
    activated = Column(Integer, default='0', server_default='0', nullable=False)

    _password = Column(String)

    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)

    @property
    def password(self):
        raise AttributeError('Cannot read password')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self._password, password)
