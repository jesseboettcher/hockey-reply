'''
create_test_data

Script to populate database with players, teams, and games for testing.
    Creates 2 teams
    Creates 10 users
    Adds 10 users as players to one of the teams

To run: python -m webserver.test.create_test_data
'''
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
    else:
        print(f'User {email} already exists')

    return user

def team_has_player(user_id, players):
    for player in players:
        if player.user_id == user_id:
            return True

    return False

app = create_app(True)

db = get_db()

# team setup
team = db.get_team(TEAM_TEST_NAME)
if team == None:
    print(f'Adding test team')
    team = db.add_team(TEAM_TEST_NAME)
else:
    print(f'Team {TEAM_TEST_NAME} already exists')
team_id = team.team_id

team = db.get_team(TEAM_TEST_NAME_2)
if team == None:
    print(f'Adding test team 2')
    team = db.add_team(TEAM_TEST_NAME_2)
else:
    print(f'Team {TEAM_TEST_NAME_2} already exists')
team_id_2 = team.team_id

# user setup
for i in range(10):
    player = get_or_create_player(get_player_email(i))

    team = db.get_team(TEAM_TEST_NAME)

    if not team_has_player(player.user_id, team.players):
        join_team_as_player = TeamPlayer(
                                         team_id=team.team_id,
                                         role='captain' if i == 0 else 'full',
                                         pending_status=False,
                                         joined_at=datetime.datetime.now()
                                        )
        join_team_as_player.player = player
        team.players.append(join_team_as_player)
        db.commit_changes()
        print(f'Adding player {player.user_id} to team {TEAM_TEST_NAME}')
    else:
        print(f'Player {player.user_id} already on team {TEAM_TEST_NAME}')

user = get_or_create_player(get_player_email(0))
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
print('Commited changes')
