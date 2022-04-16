'''
alchemy_models

Model classes to set up the SQLAlchemy bindings to the database. Instances of these classes are
returned by all hockey_db.Database queries and changes to these objects are propagated back
to the actual DB.
'''
import secrets
from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

Base = declarative_base()

class TeamPlayer(Base):
    __tablename__ = 'team_player'
    team_id = Column(ForeignKey('team.team_id'), primary_key=True)
    user_id = Column(ForeignKey('users.user_id'), primary_key=True)
    role = Column(String)
    number = Column(String)
    pending_status = Column(Boolean)
    joined_at = Column(DateTime)
    player = relationship("User", back_populates="teams") # TODO rename user
    team = relationship("Team", back_populates="players")

class Team(Base):
    __tablename__ = "team"
    team_id = Column(Integer, primary_key=True)
    external_id = Column(Integer, default='0')
    name = Column(String)
    players = relationship ("TeamPlayer", back_populates="team", cascade="all, delete-orphan")

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
    did_notify_coming_soon = Column(Boolean)

class GameReply(Base):
    __tablename__ = "game_reply"
    reply_id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game.game_id"))
    team_id = Column(Integer)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    is_goalie = Column(Boolean)
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
    salt = Column(String)

    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String)
    usa_hockey_number = Column(String)

    created_at = Column(DateTime)
    logged_in_at = Column(DateTime)

    teams = relationship ("TeamPlayer", back_populates="player")

    admin = Column(Boolean)

    password_reset_token = Column(String, nullable=True)
    password_reset_token_expires_at = Column(DateTime)

    @property
    def password(self):
        raise AttributeError('Cannot read password')

    @password.setter
    def password(self, password):
        # Add some random additional text to the password befeore hashing so that
        # common passwords do not create a common hash.
        self.salt = secrets.token_urlsafe(16)
        self._password = generate_password_hash(f"{password}{self.salt}")

    def verify_password(self, password):
        return check_password_hash(self._password, f"{password}{self.salt}")
