import datetime
import json
import unittest

from webserver import create_app
from webserver.database.hockey_db import get_db
from webserver.database.alchemy_models import Game, TeamPlayer, User

GAME_TEST_ID = 1
TEAM_TEST_NAME = 'Unit Test'
TEAM_TEST_NAME_2 = 'Unit Test 2'
USER_TEST_EMAIL = 'a@b.c'

def get_player_email(player_index):
    return f'{player_index}@no.domain'

def get_or_create_player(email):
    user = db.get_user(email)

    if user == None:
        print(f'Adding test user {email}')
        user = User(email=email.strip().lower(),
                    first_name=email.split('@')[0],
                    created_at=datetime.datetime.now(),
                    logged_in_at=datetime.datetime.now(),
                    admin=False
                    )
        user.password = '12345678'
        get_db().add_user(user)

app = create_app(True)
client = app.test_client(self)

db = get_db()

# team setup
team = db.get_team(TEAM_TEST_NAME)
if team == None:
    print(f'Adding test team')
    team = db.add_team(TEAM_TEST_NAME)
team_id = team.team_id

team = db.get_team(TEAM_TEST_NAME_2)
if team == None:
    print(f'Adding test team 2')
    team = db.add_team(TEAM_TEST_NAME_2)
team_id_2 = team.team_id

# user setup
for i in range(10):
    get_or_create_player(get_player_email(i))

    team = db.get_team(TEAM_TEST_NAME)
    join_team_as_player = TeamPlayer(
                                     team_id=team.team_id,
                                     role='captain' if i == 0 else 'full',
                                     pending_status=False,
                                     joined_at=datetime.datetime.now()
                                    )
    join_team_as_player.player = user
    team.players.append(join_team_as_player)
    db.commit_changes()

user_id = user.user_id

# game setup
game = db.get_game_by_id(GAME_TEST_ID)
delta = datetime.timedelta(hours=18)
game_time = delta + datetime.datetime.now()

if game == None:
    print(f'Adding test game')


    game = Game(game_id=GAME_TEST_ID,
                scheduled_at=game_time,
                completed=0,
                rink='center',
                level='A',
                home_team_id=team_id,
                away_team_id=team_id_2,
                home_goals=0,
                away_goals=0,
                game_type='Championship')
    db.add_game_object(game)

game.scheduled_at = game_time
db.commit_changes()
