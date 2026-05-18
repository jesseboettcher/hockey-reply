import datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from bs4 import BeautifulSoup

from webserver.data_synchronizer import Synchronizer
from webserver.email import EmailTemplate, send_new_games
from webserver.website_parsers import ApiGameParser, TeamPageParser


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


class FakeSyncDatabase:
    def __init__(self):
        self.teams = []
        self.games = {}

    def add_team(self, team_name, external_id=0):
        self.teams.append((team_name, external_id))

    def add_game(self, game_parser):
        is_new = game_parser.id not in self.games
        self.games[game_parser.id] = SimpleNamespace(
            game_id=game_parser.id,
            home_team_id=game_parser.home_team,
            away_team_id=game_parser.away_team,
        )
        return is_new

    def get_game_by_id(self, game_id):
        return self.games[game_id]


class SynchronizerTests(unittest.TestCase):
    def make_synchronizer(self):
        return Synchronizer.__new__(Synchronizer)

    @patch('webserver.data_synchronizer.ProcessPoolExecutor')
    @patch('webserver.data_synchronizer.BackgroundScheduler')
    def test_scheduler_runs_sync_immediately_after_startup(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        Synchronizer()

        sync_job_call = scheduler.add_job.call_args_list[0]
        self.assertEqual(sync_job_call.args[1], 'interval')
        self.assertEqual(sync_job_call.kwargs['hours'], Synchronizer.SYNCHRONIZE_INTERVAL_HOURS)
        self.assertIn('next_run_time', sync_job_call.kwargs)

    @unittest.skipUnless(
        os.getenv('RUN_LIVE_TIMETOSCORE_API_TESTS') == '1',
        'set RUN_LIVE_TIMETOSCORE_API_TESTS=1 to call the live TimeToScore API',
    )
    def test_live_api_prints_dumpster_fire_current_schedule(self):
        synchronizer = self.make_synchronizer()
        api_config = {
            'api_base': Synchronizer.SHARKS_ICE_API_BASE_URL,
            'api_key': Synchronizer.SHARKS_ICE_API_KEY,
            'api_secret': Synchronizer.SHARKS_ICE_API_SECRET,
            'league_id': 1,
        }

        leagues_json = synchronizer.open_api_json('get_leagues', {'league_id': 1}, api_config)
        league = leagues_json['leagues'][0]
        season_id = int(league['current_season'])
        stat_class = int(league['default_stat_class_tag'])

        standings_json = synchronizer.open_api_json(
            'get_standings',
            {
                'league_id': 1,
                'season_id': season_id,
                'stat_class': stat_class,
            },
            api_config,
        )
        teams = synchronizer.teams_from_standings(standings_json)

        self.assertIn(4844, teams)
        self.assertEqual(teams[4844], 'Dumpster Fire')

        schedule_json = synchronizer.open_api_json(
            'get_schedule',
            {
                'league_id': 1,
                'season_id': season_id,
                'team_id': 4844,
            },
            api_config,
        )

        print(f'\nDumpster Fire schedule for season {season_id}:')
        for game in schedule_json.get('games', []):
            away_goals = '-' if game.get('away_goals') is None else game.get('away_goals')
            home_goals = '-' if game.get('home_goals') is None else game.get('home_goals')
            print(
                f'{game.get("date")} {game.get("formatted_time")} '
                f'{game.get("away_team", "").strip()} ({away_goals}) @ '
                f'{game.get("home_team", "").strip()} ({home_goals}) - '
                f'{game.get("location")} [{game.get("game_status")}] game_id={game.get("game_id")}'
            )

        if not schedule_json.get('games'):
            print('(no games found)')

    def test_legacy_team_fixture_still_parses(self):
        with open('webserver/test/team.html') as fixture:
            soup = BeautifulSoup(fixture, 'html.parser')

        parser = TeamPageParser('https://stats.sharksice.timetoscore.com/display-schedule?team=3329&season=52', soup)

        self.assertTrue(parser.parse())
        self.assertEqual(parser.external_id, 3329)
        self.assertEqual(parser.season_num, 52)
        self.assertGreater(len(parser.games), 0)

    def test_api_game_parser_matches_database_game_shape(self):
        game_json = {
            'game_id': '576574',
            'date': '2026-05-13',
            'time': '22:15:00',
            'location': 'San Jose Orange (N)',
            'home_team': 'Americans ',
            'away_team': 'Pager Flakes ',
            'home_goals': None,
            'away_goals': None,
            'level_name': 'Adult Division 1',
            'gtype_name': 'Regular',
            'league_name': 'SIAHL@SJ',
            'timezn': 'America/Los_Angeles',
            'result_flag': None,
            'game_status': 'NOT STARTED',
        }

        parser = ApiGameParser(game_json)

        self.assertTrue(parser.parse_success)
        self.assertEqual(parser.id, 576574)
        self.assertEqual(parser.completed, 0)
        self.assertEqual(parser.datetime, datetime.datetime(2026, 5, 13, 22, 15, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'PDT')))
        self.assertEqual(parser.rink, 'San Jose Orange (N)')
        self.assertEqual(parser.home_team, 'Americans')
        self.assertEqual(parser.away_team, 'Pager Flakes')
        self.assertEqual(parser.home_goals, 0)

    def test_api_url_signs_request_like_timetoscore_frontend(self):
        synchronizer = self.make_synchronizer()

        with patch('webserver.data_synchronizer.time.time', return_value=1778527533):
            url = synchronizer.api_url(
                'get_leagues',
                {'league_id': 1},
                {
                    'api_base': 'https://api.sharksice.timetoscore.com/',
                    'api_key': 'web',
                    'api_secret': 'i8IC4I8cCLdLGWiKk5Ukw4FfIjBtvOG4',
                },
            )

        self.assertEqual(
            url,
            'https://api.sharksice.timetoscore.com/get_leagues?auth_key=web&auth_timestamp=1778527533&body_md5=d41d8cd98f00b204e9800998ecf8427e&league_id=1&auth_signature=d088c14c75f5fba276d0cf17e063384b8cb9b603d7201b7ffb1ce0b7f4e89cd9',
        )

    def test_sync_season_uses_api_when_configured(self):
        html = '''
            <body>
                <div id="standings-root"
                     data-league="1"
                     data-api-base="https://api.sharksice.timetoscore.com/"
                     data-api-key="web"
                     data-api-secret="v8VP4V8pPYqYTJvXx5Hxj4SsVwOgiBT4"></div>
            </body>
        '''
        api_responses = {
            'get_leagues': {
                'leagues': [{
                    'current_season': 74,
                    'default_stat_class_tag': 1,
                }],
            },
            'get_standings': {
                'standings': {
                    'leagues': [{
                        'levels': [{
                            'conferences': [{
                                'teams': [
                                    {'id': 323, 'team_name': 'Americans '},
                                    {'id': 310, 'team_name': 'Pager Flakes '},
                                ],
                            }],
                        }],
                    }],
                },
            },
            'get_schedule': {
                'games': [{
                    'game_id': '576574',
                    'date': '2026-05-13',
                    'time': '22:15:00',
                    'location': 'San Jose Orange (N)',
                    'home_team': 'Americans ',
                    'away_team': 'Pager Flakes ',
                    'home_goals': None,
                    'away_goals': None,
                    'level_name': 'Adult Division 1',
                    'gtype_name': 'Regular',
                    'league_name': 'SIAHL@SJ',
                    'timezn': 'America/Los_Angeles',
                    'result_flag': None,
                    'game_status': 'NOT STARTED',
                }],
            },
        }

        synchronizer = self.make_synchronizer()
        synchronizer.db = FakeSyncDatabase()
        synchronizer.synced_games_list = []
        synchronizer.new_games_map = {}

        with patch.object(synchronizer, 'open_season_page', return_value=('season', BeautifulSoup(html, 'html.parser'))), \
                patch.object(synchronizer, 'open_api_json', side_effect=lambda endpoint, params, api_config=None: api_responses[endpoint]):
            self.assertTrue(synchronizer.sync_season('https://stats.sharksice.timetoscore.com/display-stats.php?league=1'))

        self.assertEqual(synchronizer.db.teams, [('Americans', 323), ('Pager Flakes', 310)])
        self.assertEqual(synchronizer.synced_games_list, [576574])
        self.assertEqual(
            synchronizer.new_games_map,
            {
                'Americans': [576574],
                'Pager Flakes': [576574],
            },
        )

    def test_sync_season_uses_legacy_scraper_when_configured(self):
        html = '''
            <body>
                <a href="display-schedule?team=4844&season=74">Dumpster Fire</a>
            </body>
        '''
        fake_parser = SimpleNamespace(
            external_id=4844,
            games=[],
            parse=Mock(return_value=True),
        )

        synchronizer = self.make_synchronizer()
        synchronizer.db = FakeSyncDatabase()
        synchronizer.synced_games_list = []
        synchronizer.new_games_map = {}

        with patch.object(Synchronizer, 'SHARKS_ICE_SYNC_SOURCE', Synchronizer.SYNC_SOURCE_SCRAPER), \
                patch.object(synchronizer, 'open_season_page', return_value=('season', BeautifulSoup(html, 'html.parser'))), \
                patch.object(synchronizer, 'open_team_page', return_value=('team', BeautifulSoup('<body></body>', 'html.parser'))) as open_team_page_mock, \
                patch.object(synchronizer, 'sync_api_season') as sync_api_season_mock, \
                patch('webserver.data_synchronizer.print_log'), \
                patch('webserver.data_synchronizer.TeamPageParser', return_value=fake_parser):
            self.assertTrue(synchronizer.sync_season('https://stats.sharksice.timetoscore.com/display-stats.php?league=1'))

        open_team_page_mock.assert_called_once_with('display-schedule?team=4844&season=74')
        sync_api_season_mock.assert_not_called()
        self.assertEqual(synchronizer.db.teams, [('Dumpster Fire', 4844)])

    @patch('webserver.data_synchronizer.write_log')
    def test_check_deleted_games_uses_database_game_id(self, write_log_mock):
        synchronizer = self.make_synchronizer()
        synchronizer.synced_games_list = [575025]
        synchronizer.db = SimpleNamespace(
            get_games=Mock(return_value=[
                SimpleNamespace(game_id=575025, completed=0),
                SimpleNamespace(game_id=578818, completed=0),
                SimpleNamespace(game_id=571632, completed=1),
            ]),
        )

        synchronizer.check_deleted_games()

        write_log_mock.assert_called_once_with('INFO', 'Game DELETED game_id 578818')

    def test_send_new_games_emails_rostered_players(self):
        db = FakeDatabase()

        with patch('webserver.email.write_log'), patch('webserver.email.send_email') as send_email_mock:
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
    @patch('webserver.data_synchronizer.write_log')
    def test_notify_sends_new_games_before_clearing_map(self, write_log_mock, database_cls, send_new_games_mock, send_game_coming_soon_mock):
        fake_db = Mock()
        fake_db.get_games_coming_soon.return_value = []
        database_cls.return_value = fake_db

        synchronizer = self.make_synchronizer()
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
