import datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from bs4 import BeautifulSoup

from webserver.data_synchronizer import Synchronizer
from webserver.database.hockey_db import Database
from webserver.email import EmailTemplate, send_new_games
from webserver.website_parsers import ApiGameParser, LockerRoomPageParser, TeamPageParser


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


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def one_or_none(self):
        return self.result


class FakeSession:
    def __init__(self, query_result):
        self.query_result = query_result
        self.did_commit = False

    def query(self, model):
        return FakeQuery(self.query_result)

    def commit(self):
        self.did_commit = True

    def close(self):
        pass


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
        self.assertEqual(sync_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)

        locker_room_job_call = scheduler.add_job.call_args_list[2]
        self.assertEqual(locker_room_job_call.args[1], 'interval')
        self.assertEqual(locker_room_job_call.kwargs['seconds'], Synchronizer.LOCKER_ROOM_INTERVAL_SECONDS)
        self.assertIn('next_run_time', locker_room_job_call.kwargs)
        self.assertEqual(locker_room_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)

    @patch.dict(os.environ, {}, clear=True)
    @patch('webserver.data_synchronizer.ProcessPoolExecutor')
    @patch('webserver.data_synchronizer.BackgroundScheduler')
    def test_local_locker_room_sync_only_schedules_and_starts_locker_room_job(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        with patch.object(Synchronizer, 'LOCAL_LOCKER_ROOM_SYNC_ONLY', True):
            Synchronizer()

        scheduler.start.assert_called_once()
        self.assertEqual(len(scheduler.add_job.call_args_list), 1)
        locker_room_job_call = scheduler.add_job.call_args_list[0]
        self.assertEqual(locker_room_job_call.args[0].__name__, 'locker_room_assignment_check')
        self.assertEqual(locker_room_job_call.args[1], 'interval')
        self.assertEqual(locker_room_job_call.kwargs['seconds'], Synchronizer.LOCKER_ROOM_INTERVAL_SECONDS)
        self.assertIn('next_run_time', locker_room_job_call.kwargs)
        self.assertEqual(locker_room_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)

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

    def test_locker_room_parser_handles_current_timetoscore_table(self):
        html = '''
            <body>
                <table class="lr-table">
                    <thead>
                        <tr>
                            <th>Game</th>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Rink</th>
                            <th>League</th>
                            <th>Home</th>
                            <th>LR</th>
                            <th>Away</th>
                            <th>LR</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="lr-game-id">605583</td>
                            <td>Sun Jun 07</td>
                            <td>1:15 PM</td>
                            <td>San Jose Blue (S)</td>
                            <td>SIAHL@SJ</td>
                            <td>Home Team One</td>
                            <td class="lr-lockerroom">G3</td>
                            <td>Away Team One</td>
                            <td class="lr-lockerroom">G5</td>
                        </tr>
                        <tr>
                            <td class="lr-game-id">578811</td>
                            <td>Sun Jun 07</td>
                            <td>1:30 PM</td>
                            <td>San Jose Blue (N)</td>
                            <td>SIAHL@SJ</td>
                            <td>Home Team Two</td>
                            <td class="lr-lockerroom">G8</td>
                            <td>Away Team Two</td>
                            <td class="lr-lockerroom">G6</td>
                        </tr>
                        <tr>
                            <td class="lr-game-id">578818</td>
                            <td>Sun, Jun 7th</td>
                            <td class="lr-time">9:00 PM</td>
                            <td>San Jose Grey</td>
                            <td>SIAHL@SJ Division 7B</td>
                            <td>Dumpster Fire</td>
                            <td class="lr-lockerroom">G9</td>
                            <td>JuggerNuggets</td>
                            <td class="lr-lockerroom">G7</td>
                        </tr>
                    </tbody>
                </table>
            </body>
        '''
        parser = LockerRoomPageParser(
            'https://stats.sharksice.timetoscore.com/display-lr-assignments.php',
            BeautifulSoup(html, 'html.parser'),
        )

        self.assertTrue(parser.parse())
        self.assertEqual(parser.get_locker_rooms_for_game('605583'), ('G3', 'G5'))
        self.assertEqual(parser.get_locker_rooms_for_game('578811'), ('G8', 'G6'))
        self.assertEqual(parser.get_locker_rooms_for_game(578818), ('G9', 'G7'))
        self.assertIn('578811', parser.get_games_with_locker_rooms())

    @patch('webserver.database.hockey_db.write_log')
    def test_update_locker_rooms_updates_matching_game_from_parser_string_id(self, write_log_mock):
        game = SimpleNamespace(
            game_id=578818,
            home_locker_room=None,
            away_locker_room=None,
        )
        locker_room_parser = SimpleNamespace(
            queried_ids=[],
            get_games_with_locker_rooms=Mock(return_value=['578818']),
        )

        def get_locker_rooms_for_game(game_id):
            locker_room_parser.queried_ids.append(game_id)
            return 'G9', 'G7'

        locker_room_parser.get_locker_rooms_for_game = get_locker_rooms_for_game

        db = Database.__new__(Database)
        db.session = FakeSession(game)
        db.engine = SimpleNamespace(dispose=Mock())

        db.update_locker_rooms(locker_room_parser)

        self.assertEqual(locker_room_parser.queried_ids, [578818])
        self.assertEqual(game.home_locker_room, 'G9')
        self.assertEqual(game.away_locker_room, 'G7')
        self.assertTrue(db.session.did_commit)
        write_log_mock.assert_called_once_with('INFO', 'Locker room sync parsed=1 matched=1 updated=2 missing_games=0')

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

    def test_api_config_from_soup_reads_timetoscore_proxy_config(self):
        html = '''
            <body>
                <div id="standings-root"
                     data-league="1"
                     data-season="0"
                     data-api-base="https://api.sharksice.timetoscore.com/"
                     data-api-key=""
                     data-api-secret=""
                     data-proxy-base="/test/api-proxy.php"
                     data-proxy-session="session-token"></div>
            </body>
        '''

        synchronizer = self.make_synchronizer()
        api_config = synchronizer.api_config_from_soup(BeautifulSoup(html, 'html.parser'))

        self.assertEqual(api_config['league_id'], 1)
        self.assertEqual(
            api_config['proxy_base'],
            'https://stats.sharksice.timetoscore.com/test/api-proxy.php',
        )
        self.assertEqual(api_config['proxy_session'], 'session-token')

    def test_proxy_api_url_matches_timetoscore_frontend_query_format(self):
        synchronizer = self.make_synchronizer()

        url = synchronizer.proxy_api_url(
            'get_schedule',
            {
                'season_id': 74,
                'league_id': 1,
                'team_id': 4844,
                'stat_class': '',
                'empty_value': None,
                'negative_value': -1,
            },
            {
                'proxy_base': 'https://stats.sharksice.timetoscore.com/test/api-proxy.php',
            },
        )

        self.assertEqual(
            url,
            'https://stats.sharksice.timetoscore.com/test/api-proxy.php?endpoint=get_schedule&league_id=1&season_id=74&team_id=4844',
        )

    @patch('webserver.data_synchronizer.requests.get')
    def test_open_api_json_uses_timetoscore_proxy_when_available(self, requests_get_mock):
        response = Mock()
        response.json.return_value = {'leagues': []}
        requests_get_mock.return_value = response

        synchronizer = self.make_synchronizer()

        result = synchronizer.open_api_json(
            'get_leagues',
            {'league_id': 1},
            {
                'api_base': 'https://api.sharksice.timetoscore.com/',
                'api_key': 'web',
                'api_secret': 'secret',
                'proxy_base': 'https://stats.sharksice.timetoscore.com/test/api-proxy.php',
                'proxy_session': 'session-token',
            },
        )

        self.assertEqual(result, {'leagues': []})
        requests_get_mock.assert_called_once()
        self.assertEqual(
            requests_get_mock.call_args.args[0],
            'https://stats.sharksice.timetoscore.com/test/api-proxy.php?endpoint=get_leagues&league_id=1',
        )
        self.assertEqual(
            requests_get_mock.call_args.kwargs['headers']['X-Proxy-Session'],
            'session-token',
        )

    @patch('webserver.data_synchronizer.write_log')
    @patch('webserver.data_synchronizer.requests.get')
    def test_open_api_json_logs_non_json_response(self, requests_get_mock, write_log_mock):
        response = Mock()
        response.status_code = 403
        response.text = '<html>Forbidden</html>'
        response.json.side_effect = ValueError('not json')
        requests_get_mock.return_value = response

        synchronizer = self.make_synchronizer()

        self.assertIsNone(synchronizer.open_api_json('get_leagues', {'league_id': 1}))
        write_log_mock.assert_called_once_with(
            'ERROR',
            'Failed TimeToScore API JSON for get_leagues: status=403 body=<html>Forbidden</html>',
        )

    @patch('webserver.data_synchronizer.write_log')
    @patch('webserver.data_synchronizer.requests.get')
    def test_open_page_uses_browser_like_headers(self, requests_get_mock, write_log_mock):
        response = Mock()
        response.status_code = 200
        response.content = b'<body></body>'
        response.text = '<body></body>'
        response.url = 'https://stats.sharksice.timetoscore.com/display-lr-assignments.php'
        requests_get_mock.return_value = response

        synchronizer = self.make_synchronizer()
        synchronizer.open_page('https://stats.sharksice.timetoscore.com/display-lr-assignments.php')

        self.assertEqual(
            requests_get_mock.call_args.kwargs['headers'],
            Synchronizer.SHARKS_ICE_REQUEST_HEADERS,
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

    @patch('webserver.data_synchronizer.write_log')
    def test_sync_api_season_returns_false_when_leagues_api_fails(self, write_log_mock):
        html = '''
            <body>
                <div id="standings-root" data-league="1"></div>
            </body>
        '''
        synchronizer = self.make_synchronizer()
        synchronizer.db = FakeSyncDatabase()

        with patch.object(synchronizer, 'open_api_json', return_value=None):
            self.assertFalse(synchronizer.sync_api_season(BeautifulSoup(html, 'html.parser')))

        write_log_mock.assert_called_once_with(
            'ERROR',
            'Failed synchronization of TimeToScore API get_leagues for league 1',
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

    @patch('webserver.data_synchronizer.write_log')
    @patch('webserver.data_synchronizer.Database')
    def test_sync_skips_deleted_game_check_by_default(self, database_cls, write_log_mock):
        synchronizer = self.make_synchronizer()

        with patch.object(synchronizer, 'sync_season', return_value=True), \
                patch.object(synchronizer, 'check_deleted_games') as check_deleted_games_mock:
            self.assertTrue(synchronizer.sync())

        check_deleted_games_mock.assert_not_called()

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
