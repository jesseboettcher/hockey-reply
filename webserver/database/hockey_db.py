import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlite3

from webserver.database.alchemy_models import Game, Team

class Database:
    SQLITE_DB_PATH = 'database/hockey.db'

    def __init__(self, local):

        connect_string = f'postgresql://postgres:{os.getenv("POSTGRES_PASSWORD")}@hockey-data.cb53hszvt88d.us-west-2.rds.amazonaws.com/hockeydata'
        if local:
            connect_string = f"sqlite:///{self.SQLITE_DB_PATH}"

        engine = create_engine(connect_string)
        Session = sessionmaker()
        Session.configure(bind=engine)
        self.session = Session()

    def get_teams(self):
        return self.session.query(Team).all()

    def get_team(self, name):
        return self.session.query(Team).filter(Team.name == name).one_or_none()

    def add_team(self, team_name):
        team = self.session.query(Team).filter(Team.name == team_name).one_or_none()

        if team is not None:
            return

        team = Team(name=team_name)

        self.session.add(team)
        self.session.commit()

        return team;

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
                    scheduled_time=game_parser.datetime,
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
