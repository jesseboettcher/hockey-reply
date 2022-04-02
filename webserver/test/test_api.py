import datetime
import json
import unittest

from webserver import create_app
from webserver.database.hockey_db import get_db, setup_test_db
from webserver.database.alchemy_models import Game, TeamPlayer, User

class BasicTestCase(unittest.TestCase):

    GAME_TEST_ID = 1
    TEAM_TEST_NAME = 'Unit Test'
    TEAM_TEST_NAME_2 = 'Unit Test 2'
    USER_TEST_EMAIL = 'a@b.c'

    @classmethod
    def setUpClass(self):
        self.app = create_app(True)
        self.client = self.app.test_client(self)

        setup_test_db()
        db = get_db()

        # team setup
        team = db.get_team(self.TEAM_TEST_NAME)
        if team == None:
            print(f'Adding test team')
            team = db.add_team(self.TEAM_TEST_NAME)
        self.team_id = team.team_id

        team = db.get_team(self.TEAM_TEST_NAME_2)
        if team == None:
            print(f'Adding test team 2')
            team = db.add_team(self.TEAM_TEST_NAME_2)
        self.team_id_2 = team.team_id

        # logged in user setup
        # make sure this person is an admin so there are no auth failures on some tests
        self.app.config['TESTING_USER'] = db.get_user_by_id(3);
        assert(self.app.config['TESTING_USER'] != None)

        # user setup
        user = db.get_user(self.USER_TEST_EMAIL)

        if user == None:
            print(f'Adding test user')
            user = User(email=self.USER_TEST_EMAIL.strip().lower(),
                        first_name='Jack',
                        last_name='Black',
                        created_at=datetime.datetime.now(),
                        logged_in_at=datetime.datetime.now(),
                        admin=False
                        )
            user.password = '12345678'
            db.add_user(user)

            team = db.get_team(self.TEAM_TEST_NAME)
            join_team_as_player = TeamPlayer(
                                             team_id=team.team_id,
                                             role='captain',
                                             pending_status=False,
                                             joined_at=datetime.datetime.now()
                                            )
            join_team_as_player.player = user
            team.players.append(join_team_as_player)
            db.commit_changes()

        self.user_id = user.user_id

        # game setup
        game = db.get_game_by_id(self.GAME_TEST_ID)
        delta = datetime.timedelta(hours=18)
        game_time = delta + datetime.datetime.now()

        if game == None:
            print(f'Adding test game')


            game = Game(game_id=self.GAME_TEST_ID,
                        scheduled_at=game_time,
                        completed=0,
                        rink='center',
                        level='A',
                        home_team_id=self.team_id,
                        away_team_id=self.team_id_2,
                        home_goals=0,
                        away_goals=0,
                        game_type='Championship')
            db.add_game_object(game)

        game.scheduled_at = game_time
        db.commit_changes()

    @classmethod
    def tearDownClass(self):
        del(self.app)

    def test_join_and_remove_from_team(self):
        db = get_db()

        expected_result = 200
        team_player = db.get_team_player(self.team_id, self.user_id)
        if team_player is None:
            expected_result = 400

        response = self.client.post(f'/api/remove-player',
                                    content_type='application/json',
                                    data=json.dumps({
                                    "team_id": f"{self.team_id}",
                                    "user_id": f"{self.user_id}"
        }))
        self.assertEqual(response.status_code, expected_result)

        response = self.client.post(f'/api/join-team',
                                    content_type='application/json',
                                    data=json.dumps({
                                    "user_id": f"{self.user_id}",
                                    "team_id": f"{self.team_id}"
        }))
        self.assertEqual(response.status_code, 200)

    def test_get_games_for_team(self):
        response = self.client.get(f'/api/games/{self.team_id}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(response.get_data())

    def test_get_single_game(self):
        response = self.client.get(f'/api/game/{self.GAME_TEST_ID}/for-team/{self.team_id}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(response.get_data())

        # 0 is an invalid game ID
        response = self.client.get('/api/game/0/for-team/0', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_post_game_reply(self):
        response = self.client.post(f'/api/game/reply/{self.GAME_TEST_ID}/for-team/{self.team_id}',
                                    content_type='application/json',
                                    data=json.dumps({
                                    "user_id": f"{self.user_id}",
                                    "response": "yes",
                                    "message": "are we going up for beers?"
        }))
        self.assertEqual(response.status_code, 200)

    def test_get_game_replies_for_team(self):
        response = self.client.get(f'/api/game/reply/{self.GAME_TEST_ID}/for-team/{self.team_id}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(response.get_data())

