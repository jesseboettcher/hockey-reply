import datetime
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from webserver.data_synchronizer import Synchronizer
from webserver.email import EmailTemplate, send_new_games


class FakeDatabase:
    def __init__(self):
        self.team = SimpleNamespace(
            team_id=1,
            name='Unit Test Team',
            players=[
                SimpleNamespace(role='captain', user_id=10),
                SimpleNamespace(role='', user_id=11),
            ],
        )
        self.opponent = SimpleNamespace(team_id=2, name='Opponents')
        self.users = {
            10: SimpleNamespace(user_id=10, first_name='Jess', email='jess@example.com'),
            11: SimpleNamespace(user_id=11, first_name='Skip', email='skip@example.com'),
        }
        self.games = {
            101: SimpleNamespace(
                game_id=101,
                scheduled_at=datetime.datetime(2026, 4, 1, 3, 30),
                home_team_id=1,
                away_team_id=2,
                rink='North',
            ),
            102: SimpleNamespace(
                game_id=102,
                scheduled_at=datetime.datetime(2026, 4, 8, 4, 45),
                home_team_id=2,
                away_team_id=1,
                rink='South',
            ),
        }

    def get_team_by_id(self, team_id):
        if team_id == 1:
            return self.team
        if team_id == 2:
            return self.opponent
        return None

    def get_game_by_id(self, game_id):
        return self.games.get(game_id)

    def get_user_by_id(self, user_id):
        return self.users.get(user_id)

    def get_team_player(self, team_id, user_id):
        return SimpleNamespace(game_time_display_offset=0)


class SynchronizerTests(unittest.TestCase):
    def test_send_new_games_emails_rostered_players(self):
        db = FakeDatabase()

        with patch('webserver.email.send_email') as send_email_mock:
            send_new_games(db, 1, [102, 101])

        send_email_mock.assert_called_once()
        template, data, to_email = send_email_mock.call_args[0]

        self.assertEqual(template, EmailTemplate.NEW_GAMES)
        self.assertEqual(to_email, 'jess@example.com')
        self.assertEqual(data['game_count'], '2')
        self.assertEqual(data['games_label'], 'games')
        self.assertEqual(data['verb'], 'have')
        self.assertEqual(data['open_path'], 'http://hockeyreply.com/team/1')
        self.assertIn('Opponents', data['games_text'])

    @patch('webserver.data_synchronizer.send_game_coming_soon')
    @patch('webserver.data_synchronizer.send_new_games')
    @patch('webserver.data_synchronizer.Database')
    def test_notify_sends_new_games_before_clearing_map(self, database_cls, send_new_games_mock, send_game_coming_soon_mock):
        fake_db = Mock()
        fake_db.get_games_coming_soon.return_value = []
        database_cls.return_value = fake_db

        synchronizer = Synchronizer()
        synchronizer.new_games_map = {
            1: [101, 102],
            2: [103],
        }

        synchronizer.notify()

        self.assertEqual(
            send_new_games_mock.call_args_list,
            [call(fake_db, 1, [101, 102]), call(fake_db, 2, [103])],
        )
        self.assertEqual(synchronizer.new_games_map, {})
        send_game_coming_soon_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
