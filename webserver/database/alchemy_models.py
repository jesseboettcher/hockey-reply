from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

Base = declarative_base()

team_player = Table(
    "team_player",
    Base.metadata,
    Column("team_id", Integer, ForeignKey("team.team_id")),
    Column("user_id", Integer, ForeignKey("users.user_id")),
    Column("role", String)
)

class Team(Base):
    __tablename__ = "team"
    team_id = Column(Integer, primary_key=True)
    name = Column(String)
    players = relationship (
        "User", secondary=team_player, back_populates="teams"
    )

class Game(Base):
    __tablename__ = "game"
    game_id = Column(Integer, primary_key=True)
    scheduled_at = Column(DateTime)
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

class GameReply(Base):
    __tablename__ = "game_reply"
    reply_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game.game_id"))
    user_id = Column(Integer, ForeignKey("user.user_id"))
    response = Column(String)
    message = Column(String)
    modified_at = Column(DateTime)

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

    created_at = Column(DateTime)
    logged_in_at = Column(DateTime)

    teams = relationship (
        "Team", secondary=team_player, back_populates="players"
    )

    @property
    def password(self):
        raise AttributeError('Cannot read password')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self._password, password)
