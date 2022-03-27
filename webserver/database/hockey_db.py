import datetime
import os

from flask import current_app, g
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker
import sqlite3

from webserver.database.alchemy_models import Game, GameReply, Team, User, TeamPlayer

global_db_instance = None

def get_db():
    global global_db_instance
    if global_db_instance is None:
        global_db_instance = Database(False)

    return global_db_instance

def close_db(e=None):
    if global_db_instance is not None:
        global_db_instance.close()

class Database:
    SQLITE_DB_PATH = 'database/hockey.db'

    def __init__(self, local):
        connect_string = f'postgresql://postgres:{os.getenv("POSTGRES_PASSWORD")}@hockey-data.cb53hszvt88d.us-west-2.rds.amazonaws.com/hockeydata'
        if local:
            connect_string = f"sqlite:///{self.SQLITE_DB_PATH}"

        self.engine = create_engine(connect_string)
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()

    def __del__(self):
        self.close();

    def close(self):
        self.session.close()
        self.engine.dispose()

    def commit_changes(self):
        self.session.commit()

    ### User methods
    def get_user(self, email):
        return self.session.query(User).filter(func.lower(User.email) == email.strip().lower()).first()

    def get_user_by_id(self, user_id):
        return self.session.query(User).filter_by(user_id=user_id).first()

    def get_user_by_external_id(self, external_id):
        return self.session.query(User).filter(func.lower(User.external_id) == external_id).first()

    def get_user_by_password_reset_token(self, token):
        return self.session.query(User).filter(User.password_reset_token == token).one_or_none()

    def add_user(self, user):
        self.session.add(user)
        self.session.commit()
        return user;

    ### Teams methods
    def get_teams(self):
        return self.session.query(Team).all()

    def get_team(self, name):
        return self.session.query(Team).filter(Team.name == name).one_or_none()

    def get_team_by_id(self, team_id):
        return self.session.query(Team).filter(Team.team_id == team_id).one_or_none()

    def add_team(self, team_name):
        team = self.session.query(Team).filter(Team.name == team_name).one_or_none()

        if team is not None:
            return

        team = Team(name=team_name)

        self.session.add(team)
        self.session.commit()

        return team;

    def get_team_players(self):
        return self.session.query(TeamPlayer).all()

    def get_team_player(self, team_id, user_id):
        return self.session.query(TeamPlayer).filter(and_(TeamPlayer.team_id == team_id, TeamPlayer.user_id == user_id)).one_or_none()

    ### Game methods
    def get_games(self):
        return self.session.query(Game).all()

    def get_games_for_team(self, team_id):
        return self.session.query(Game).filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id)).all()

    def get_game_by_id(self, game_id):
        return self.session.query(Game).filter(Game.game_id == game_id).one_or_none()

    def add_game(self, game_parser):
        game = self.session.query(Game).filter(Game.game_id == game_parser.id).one_or_none()

        if game is not None:
            # todo update if differences
            return

        home_team = self.get_team(game_parser.home_team)
        if home_team is None:
            home_team = self.add_team(game_parser.home_team)

        away_team = self.get_team(game_parser.away_team)
        if away_team is None:
            away_team = self.add_team(game_parser.away_team)

        game = Game(game_id=game_parser.id,
                    scheduled_at=game_parser.datetime,
                    completed=game_parser.completed,
                    rink=game_parser.rink,
                    level=game_parser.level,
                    home_team_id=home_team.team_id,
                    away_team_id=away_team.team_id,
                    home_goals=game_parser.home_goals,
                    away_goals=game_parser.away_goals,
                    game_type=game_parser.type)

        self.session.add(game)
        self.session.commit()

    def add_game_object(self, game):
        self.session.add(game)
        self.session.commit()

    ### Reply methods
    def game_replies_for_game(self, game_id, team_id):
        return self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.team_id == team_id)).all()

    def game_reply_for_game_and_user(self, game_id, team_id, user_id):
        return self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.team_id == team_id, GameReply.user_id == user_id)).one_or_none()

    def set_game_reply(self, game_id, team_id, user_id, reply, message):
        db_reply = self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.user_id == user_id)).one_or_none()

        if db_reply is None:
            db_reply = GameReply(game_id=game_id,
                                 team_id=team_id,
                                 user_id=user_id,
                                 response=reply,
                                 message=message
                                )
            self.session.add(db_reply)
        else:
            if reply:
                db_reply.response = reply
            if message:
                db_reply.message = message

        db_reply.modified_at = datetime.datetime.now()

        self.session.commit()
