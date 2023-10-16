'''
hockey_db

Contains the Database class that's used for all queries into the postgres DB.
'''
import datetime
import os

from flask import current_app, g
import phonenumbers
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker

from webserver.database.alchemy_models import Game, GameReply, Team, User, TeamGoalie, TeamPlayer
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
    def get_users(self):
        return self.session.query(User).all()

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

    def remove_goalie_from_team(self, team_id, goalie_id):
        self.session.query(TeamGoalie).filter(and_(TeamGoalie.team_id == team_id, TeamGoalie.id == goalie_id)).delete()

    ### Game methods
    def get_games(self):
        return self.session.query(Game).all()

    def get_games_for_team(self, team_id):
        return self.session.query(Game).filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id)).order_by(Game.scheduled_at.asc()).all()

    def get_game_by_id(self, game_id):
        return self.session.query(Game).filter(Game.game_id == game_id).one_or_none()

    def remove_game_by_id(self, game_id):
        self.session.query(Game).filter(Game.game_id == game_id).delete()

    def get_games_coming_soon(self):
        today = datetime.datetime.now()
        soon = today + datetime.timedelta(hours=84)
        return self.session.query(Game).filter(and_(Game.did_notify_coming_soon == False,
                                                    Game.scheduled_at > today, # TODO >= today
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

            # Check if team ids match, update if they do not. Teams can change during playoffs
            # when games are posted with one or both of the teams ommitted until games in the
            # earlier rounds have completed.
            parsed_home_team = self.get_team(game_parser.home_team)
            parsed_away_team = self.get_team(game_parser.away_team)

            if parsed_away_team and parsed_away_team.team_id != game.away_team_id:
                write_log('INFO', f'Away team changed from {game.away_team_id} to {parsed_away_team.team_id} for {game.game_id}')
                game.away_team_id = parsed_away_team.team_id

            if parsed_home_team and parsed_home_team.team_id != game.home_team_id:
                write_log('INFO', f'Home team changed from {game.home_team_id} to {parsed_home_team.team_id} for {game.game_id}')
                game.home_team_id = parsed_home_team.team_id

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
                    game_type=game_parser.type,
                    created_at=datetime.datetime.now())

        self.session.add(game)
        self.session.commit()
        return True

    def add_game_object(self, game):
        self.session.add(game)
        self.session.commit()

    def update_locker_rooms(self, locker_room_parser):

        for game_id in locker_room_parser.get_games_with_locker_rooms():

            game = self.session.query(Game).filter(Game.game_id == game_id).one_or_none()
            if game is None:
                continue

            home_lr, away_lr = locker_room_parser.get_locker_rooms_for_game(game_id)

            if home_lr != game.home_locker_room:
                game.home_locker_room = home_lr

            if away_lr != game.away_locker_room:
                game.away_locker_room = away_lr

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

class PersonReference:
    """
    Class to reference a person by user_id, if registered, or name and phone number otherwise.
    """
    def __init__(self, user_id, name, phone_number):
        if user_id is None:
            self.user_id = 0
        else:
            self.user_id = user_id
        self.name = name

        if self.user_id > 0:
            db = get_db()
            user = db.get_user_by_id(self.user_id)

            if self.name is None:
                self.name = user.first_name

            if phone_number is None:
                phone_number = user.phone_number

        if phone_number is None:
            self.phone_number = None
        elif isinstance(phone_number, phonenumbers.PhoneNumber):
            self.phone_number = phone_number
        else:
            self.phone_number = phonenumbers.parse(phone_number, "US")

        if self.name == None:
            self.name = "Unknown"

        assert(self.name is not None)

    def __hash__(self):
        return hash((self.user_id, self.name, phonenumbers.format_number(self.phone_number, phonenumbers.PhoneNumberFormat.E164)))

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, PersonReference):
            return self.user_id == __value.user_id and self.name == __value.name and self.phone_number == __value.phone_number
        return False

    def __str__(self) -> str:
        return f'PersonReference({self.user_id}, {self.name}, {self.phone_number})'
