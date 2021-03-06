'''
hockey_db

Contains the Database class that's used for all queries into the postgres DB.
'''
import datetime
import os

from flask import current_app, g
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker

from webserver.database.alchemy_models import Game, GameReply, Team, User, TeamPlayer
from webserver.email import send_game_time_changed
from webserver.logging import write_log

global_db_instance = None

def setup_test_db():
    ''' There is no current flask request when run in unit test environments.
        This function will set up a global DB instance for use in those cases.
    '''
    global global_db_instance

    if global_db_instance is None:
        global_db_instance = Database()

    return global_db_instance

def get_current_user():
    ''' There is no current flask request when run in unit test environments.
        All g.user accesses go through here, so the APIs can also run in test environments
    '''
    if current_app.config['TESTING']:
        return current_app.config['TESTING_USER']

    return g.user

def get_db():
    ''' Accessor for the current database instance. The db instance is stored with the flask
        session storage. When unit tests are running this will return the global test db instance
    '''
    if global_db_instance:
        return global_db_instance

    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = Database()
    return db

class Database:
    SQLITE_DB_PATH = 'database/hockey.db'

    def __init__(self):
        connect_string = f'postgresql://postgres:{os.getenv("POSTGRES_PASSWORD")}@hockey-data.cb53hszvt88d.us-west-2.rds.amazonaws.com/hockeydata'

        self.engine = create_engine(connect_string) # DEBUG add echo=True
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
        return self.session.query(Team).filter(func.lower(Team.name) == name.lower()).one_or_none()

    def get_team_by_id(self, team_id):
        return self.session.query(Team).filter(Team.team_id == team_id).one_or_none()

    def add_team(self, team_name, external_id):
        team = self.session.query(Team).filter(Team.name == team_name).one_or_none()

        if team is not None:
            if team.external_id == 0 and external_id != 0:
                team.external_id = external_id
                self.session.commit()
            return

        team = Team(name=team_name, external_id=external_id)

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
        return self.session.query(Game).filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id)).order_by(Game.scheduled_at.asc()).all()

    def get_game_by_id(self, game_id):
        return self.session.query(Game).filter(Game.game_id == game_id).one_or_none()

    def get_games_coming_soon(self):
        today = datetime.datetime.now()
        soon = today + datetime.timedelta(hours=72)
        return self.session.query(Game).filter(and_(Game.did_notify_coming_soon == False,
                                                    Game.scheduled_at > today,
                                                    Game.scheduled_at <= soon)).all()

    def add_game(self, game_parser):
        ''' Looks for the game_parser object in the db. Adds the game if it is new or otherwise
            updates its changed fields. Returns True if the game was new, False otherwise
        '''
        game = self.session.query(Game).filter(Game.game_id == game_parser.id).one_or_none()

        if game is not None:

            if game.completed != game_parser.completed:
                game.completed = game_parser.completed

            if game.scheduled_at != game_parser.datetime:

                old_scheduled_at = game.scheduled_at
                game.scheduled_at = game_parser.datetime
                self.session.commit()

                write_log('INFO', f'Game schedule change to {game_parser.datetime} from {old_scheduled_at} for {game.game_id}')
                send_game_time_changed(self, game, old_scheduled_at)

            self.session.commit()
            return False

        home_team = self.get_team(game_parser.home_team)
        if home_team is None:
            home_team = self.add_team(game_parser.home_team, 0)

        away_team = self.get_team(game_parser.away_team)
        if away_team is None:
            away_team = self.add_team(game_parser.away_team, 0)

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
        return True

    def add_game_object(self, game):
        self.session.add(game)
        self.session.commit()

    ### Reply methods
    def game_replies_for_game(self, game_id, team_id):
        return self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.team_id == team_id)).all()

    def game_reply_for_game_and_user(self, game_id, team_id, user_id):
        return self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.team_id == team_id, GameReply.user_id == user_id)).one_or_none()

    def set_game_reply(self, game_id, team_id, user_id, reply, message, is_goalie):
        ''' Game replies, messages, and the goalie flag are stored in the same record. The users
            may not update each of them at the same time, so this must handle updates.
        '''
        db_reply = self.session.query(GameReply).filter(and_(GameReply.game_id == game_id, GameReply.user_id == user_id)).one_or_none()

        if db_reply is None:
            db_reply = GameReply(game_id=game_id,
                                 team_id=team_id,
                                 user_id=user_id,
                                 response=reply,
                                 message=message,
                                 is_goalie=is_goalie
                                )
            self.session.add(db_reply)
        else:
            db_reply.is_goalie = is_goalie
            if reply:
                db_reply.response = reply
            if message:
                db_reply.message = message

        db_reply.modified_at = datetime.datetime.now()

        self.session.commit()
