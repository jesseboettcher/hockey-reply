import datetime
import os
import requests
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
    def __init__(self, tracked_external_ids=None):
        self.teams = []
        self.games = {}
        self.added_games = []
        self.tracked_external_ids = tracked_external_ids or []

    def add_team(self, team_name, external_id=0):
        self.teams.append((team_name, external_id))

    def add_game(self, game_parser):
        is_new = game_parser.id not in self.games
        game = SimpleNamespace(
            game_id=game_parser.id,
            home_team_id=game_parser.home_team,
            away_team_id=game_parser.away_team,
        )
        self.games[game_parser.id] = game
        self.added_games.append(game)
        return is_new

    def get_game_by_id(self, game_id):
        return self.games[game_id]

    def get_teams(self):
        return [
            SimpleNamespace(name=f'Tracked {external_id}', external_id=external_id)
            for external_id in self.tracked_external_ids
        ]

    def get_rostered_teams(self):
        return self.get_teams()

    def get_external_ids_by_team_name(self, team_name):
        return [external_id for name, external_id in self.teams if name == team_name]

    def get_games_for_team_name(self, team_name):
        return [
            game
            for game in self.added_games
            if game.home_team_id == team_name or game.away_team_id == team_name
        ]


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
    def test_default_prod_settings_schedule_sync_and_notify_without_locker_rooms(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        Synchronizer()

        self.assertEqual(len(scheduler.add_job.call_args_list), 2)
        sync_job_call = scheduler.add_job.call_args_list[0]
        self.assertEqual(sync_job_call.args[1], 'interval')
        self.assertEqual(sync_job_call.kwargs['hours'], Synchronizer.SYNCHRONIZE_INTERVAL_HOURS)
        self.assertIn('next_run_time', sync_job_call.kwargs)
        self.assertEqual(sync_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)

        notify_job_call = scheduler.add_job.call_args_list[1]
        self.assertEqual(notify_job_call.args[0].__name__, 'notify')
        self.assertEqual(notify_job_call.args[1], 'interval')
        self.assertEqual(notify_job_call.kwargs['hours'], Synchronizer.NOTIFY_CHECK_INTERVAL_HOURS)

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
        self.assertEqual(locker_room_job_call.kwargs['executor'], 'locker_room')

    def test_locker_room_job_uses_dedicated_executor(self):
        synchronizer = self.make_synchronizer()
        synchronizer.scheduler = Mock()

        synchronizer.schedule_locker_room_assignment_check()

        locker_room_job_call = synchronizer.scheduler.add_job.call_args
        self.assertEqual(locker_room_job_call.kwargs['executor'], 'locker_room')

    @patch.dict(os.environ, {}, clear=True)
    @patch('webserver.data_synchronizer.ProcessPoolExecutor')
    @patch('webserver.data_synchronizer.BackgroundScheduler')
    def test_local_timetoscore_sync_only_schedules_sync_notify_and_locker_room_jobs(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        with patch.object(Synchronizer, 'LOCAL_TIMETOSCORE_SYNC_ONLY', True):
            Synchronizer()

        scheduler.start.assert_called_once()
        self.assertEqual(len(scheduler.add_job.call_args_list), 3)
        sync_job_call = scheduler.add_job.call_args_list[0]
        notify_job_call = scheduler.add_job.call_args_list[1]
        locker_room_job_call = scheduler.add_job.call_args_list[2]

        self.assertEqual(sync_job_call.args[0].__name__, 'sync')
        self.assertEqual(sync_job_call.args[1], 'interval')
        self.assertEqual(sync_job_call.kwargs['hours'], Synchronizer.SYNCHRONIZE_INTERVAL_HOURS)
        self.assertIn('next_run_time', sync_job_call.kwargs)
        self.assertEqual(sync_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)

        self.assertEqual(notify_job_call.args[0].__name__, 'notify')
        self.assertEqual(notify_job_call.args[1], 'interval')
        self.assertEqual(notify_job_call.kwargs['hours'], Synchronizer.NOTIFY_CHECK_INTERVAL_HOURS)

        self.assertEqual(locker_room_job_call.args[0].__name__, 'locker_room_assignment_check')
        self.assertEqual(locker_room_job_call.args[1], 'interval')
        self.assertEqual(locker_room_job_call.kwargs['seconds'], Synchronizer.LOCKER_ROOM_INTERVAL_SECONDS)
        self.assertIn('next_run_time', locker_room_job_call.kwargs)
        self.assertEqual(locker_room_job_call.kwargs['misfire_grace_time'], Synchronizer.STARTUP_JOB_MISFIRE_GRACE_SECONDS)
        self.assertEqual(locker_room_job_call.kwargs['executor'], 'locker_room')

    @patch.dict(os.environ, {'HOCKEY_REPLY_ENV': 'prod'}, clear=True)
    @patch('webserver.data_synchronizer.ProcessPoolExecutor')
    @patch('webserver.data_synchronizer.BackgroundScheduler')
    def test_timetoscore_disabled_prod_schedules_notify_only(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        with patch.object(Synchronizer, 'TIMETOSCORE_SYNC_ENABLED', False), \
                patch.object(Synchronizer, 'NOTIFY_ENABLED', True):
            Synchronizer()

        scheduler.start.assert_called_once()
        self.assertEqual(len(scheduler.add_job.call_args_list), 1)
        notify_job_call = scheduler.add_job.call_args_list[0]
        self.assertEqual(notify_job_call.args[0].__name__, 'notify')
        self.assertEqual(notify_job_call.args[1], 'interval')
        self.assertEqual(notify_job_call.kwargs['hours'], Synchronizer.NOTIFY_CHECK_INTERVAL_HOURS)

    @patch.dict(os.environ, {'HOCKEY_REPLY_ENV': 'prod'}, clear=True)
    @patch('webserver.data_synchronizer.ProcessPoolExecutor')
    @patch('webserver.data_synchronizer.BackgroundScheduler')
    def test_timetoscore_and_notify_disabled_prod_starts_without_jobs(self, scheduler_cls, process_pool_cls):
        scheduler = Mock()
        scheduler_cls.return_value = scheduler
        process_pool_cls.return_value = Mock()

        with patch.object(Synchronizer, 'TIMETOSCORE_SYNC_ENABLED', False), \
                patch.object(Synchronizer, 'NOTIFY_ENABLED', False):
            Synchronizer()

        scheduler.start.assert_called_once()
        scheduler.add_job.assert_not_called()

    @unittest.skipUnless(
        os.getenv('RUN_LIVE_TIMETOSCORE_API_TESTS') == '1',
        'set RUN_LIVE_TIMETOSCORE_API_TESTS=1 to call the live TimeToScore API',
    )
    def test_live_api_prints_dumpster_fire_current_schedule(self):
        synchronizer = self.make_synchronizer()
        _, soup = synchronizer.open_season_page(
            f'{Synchronizer.SHARKS_ICE_BASE_URL}{Synchronizer.SHARKS_ICE_SEASON_ENDPOINTS[0]}'
        )
        api_config = synchronizer.api_config_from_soup(soup)

        self.assertTrue(api_config.get('proxy_base'))
        self.assertTrue(api_config.get('proxy_session'))

        leagues_json = synchronizer.open_api_json('get_leagues', {'league_id': 1}, api_config)
        self.assertIsNotNone(leagues_json)
        league = leagues_json['leagues'][0]
        stat_class = int(league['default_stat_class_tag'])
        season_id = api_config.get('season_id') or None

        standings_json = synchronizer.open_api_json(
            'get_standings',
            {
                'league_id': 1,
                'season_id': season_id,
                'stat_class': stat_class,
            },
            api_config,
        )
        self.assertIsNotNone(standings_json)
        teams = synchronizer.teams_from_standings(standings_json)

        self.assertIn(4844, teams)
        self.assertEqual(teams[4844], 'Dumpster Fire')

        schedule_json = synchronizer.open_api_json(
            'get_schedule',
            {
                'league_id': 1,
                'season_id': season_id,
                'stat_class': stat_class,
                'team_id': 4844,
            },
            api_config,
        )
        self.assertIsNotNone(schedule_json)

        print(f'\nDumpster Fire schedule for season {season_id or "page default"}:')
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

    @unittest.skipUnless(
        os.getenv('RUN_LIVE_TIMETOSCORE_SYNC_TESTS') == '1',
        'set RUN_LIVE_TIMETOSCORE_SYNC_TESTS=1 to run a live sync with a fake database',
    )
    def test_live_sync_season_populates_fake_database_from_timetoscore(self):
        synchronizer = self.make_synchronizer()
        synchronizer.db = FakeSyncDatabase()
        synchronizer.synced_games_list = []
        synchronizer.new_games_map = {}
        schedule_game_counts = {}
        league_schedule_game_count = None
        live_api_config = None

        season_url = f'{Synchronizer.SHARKS_ICE_BASE_URL}{Synchronizer.SHARKS_ICE_SEASON_ENDPOINTS[0]}'
        _, season_soup = synchronizer.open_season_page(season_url)
        preflight_api_config = synchronizer.api_config_from_soup(season_soup)
        print(
            'Live preflight API config: '
            f'league_id={preflight_api_config.get("league_id")} '
            f'season_id={preflight_api_config.get("season_id")} '
            f'stat_class={preflight_api_config.get("stat_class")} '
            f'proxy_base={preflight_api_config.get("proxy_base")} '
            f'proxy_session={"yes" if preflight_api_config.get("proxy_session") else "no"}'
        )
        preflight_leagues_json = synchronizer.open_api_json(
            'get_leagues',
            {'league_id': preflight_api_config.get('league_id', 1)},
            preflight_api_config,
        )
        print(f'Live preflight get_leagues: {preflight_leagues_json}')
        if (preflight_leagues_json or {}).get('error') == 'hourly rate limit exceeded':
            self.skipTest('TimeToScore hourly rate limit exceeded')
        self.assertIsNotNone(preflight_leagues_json)
        self.assertTrue(preflight_leagues_json.get('leagues'))

        synchronizer.db = FakeSyncDatabase(tracked_external_ids=[4844])
        original_open_api_json = synchronizer.open_api_json

        def open_api_json_with_schedule_counts(endpoint, params, api_config=None):
            nonlocal league_schedule_game_count, live_api_config
            if api_config:
                live_api_config = api_config
            response = original_open_api_json(endpoint, params, api_config)
            if endpoint == 'get_schedule':
                game_count = len((response or {}).get('games', []))
                if 'team_id' in params:
                    schedule_game_counts[int(params['team_id'])] = game_count
                else:
                    league_schedule_game_count = game_count
            return response

        with patch.object(synchronizer, 'open_api_json', side_effect=open_api_json_with_schedule_counts):
            self.assertTrue(
                synchronizer.sync_season(
                    season_url
                )
            )

        dumpster_fire_external_ids = synchronizer.db.get_external_ids_by_team_name('Dumpster Fire')
        dumpster_fire_games = synchronizer.db.get_games_for_team_name('Dumpster Fire')
        dumpster_fire_schedule_count = len(dumpster_fire_games)

        print(
            f'\nLive sync loaded {len(synchronizer.db.teams)} teams, '
            f'{len(synchronizer.db.games)} games, '
            f'{len(synchronizer.db.added_games)} add_game calls, '
            f'{len(dumpster_fire_games)} Dumpster Fire games'
        )
        print(f'Dumpster Fire external ids: {dumpster_fire_external_ids}')
        print(f'League schedule API game count: {league_schedule_game_count}')
        print(f'Dumpster Fire synced game count: {dumpster_fire_schedule_count}')
        self.print_live_schedule_probe(synchronizer, live_api_config, 4844)
        for game in sorted(dumpster_fire_games, key=lambda game: game.game_id):
            print(
                f'Dumpster Fire synced game_id={game.game_id} '
                f'{game.away_team_id} @ {game.home_team_id}'
            )

        self.assertIn(4844, dumpster_fire_external_ids)
        self.assertIsNotNone(dumpster_fire_schedule_count)
        self.assertGreater(dumpster_fire_schedule_count, 0)
        self.assertGreater(len(synchronizer.db.teams), 0)
        self.assertGreater(len(synchronizer.db.games), 0)
        self.assertGreater(len(dumpster_fire_games), 0)
        self.assertGreater(len(synchronizer.synced_games_list), 0)

    def print_live_schedule_probe(self, synchronizer, api_config, team_id):
        if not api_config:
            print('No live API config captured for schedule probe')
            return

        leagues_json = synchronizer.open_api_json('get_leagues', {'league_id': api_config.get('league_id', 1)}, api_config)
        current_season_id = None
        current_stat_class = None
        if leagues_json and leagues_json.get('leagues'):
            current_season_id = leagues_json['leagues'][0].get('current_season')
            current_stat_class = synchronizer.default_stat_class(leagues_json['leagues'][0], api_config)

        print(
            'Live API config: '
            f'league_id={api_config.get("league_id")} '
            f'season_id={api_config.get("season_id")} '
            f'stat_class={api_config.get("stat_class")} '
            f'default_stat_class={current_stat_class} '
            f'proxy_base={api_config.get("proxy_base")} '
            f'proxy_session={"yes" if api_config.get("proxy_session") else "no"}'
        )

        variants = [
            ('team only', {'team_id': team_id}),
            ('league + team', {'league_id': api_config.get('league_id', 1), 'team_id': team_id}),
            ('league + stat class + team', {'league_id': api_config.get('league_id', 1), 'stat_class': current_stat_class, 'team_id': team_id}),
            ('league + literal stat class 1 + team', {'league_id': api_config.get('league_id', 1), 'stat_class': 1, 'team_id': team_id}),
            ('page season', {'league_id': api_config.get('league_id', 1), 'season_id': api_config.get('season_id'), 'team_id': team_id}),
            ('current season', {'league_id': api_config.get('league_id', 1), 'season_id': current_season_id, 'team_id': team_id}),
            ('current season + stat class', {'league_id': api_config.get('league_id', 1), 'season_id': current_season_id, 'stat_class': current_stat_class, 'team_id': team_id}),
            ('season zero', {'league_id': api_config.get('league_id', 1), 'season_id': 0, 'team_id': team_id}),
        ]

        for label, params in variants:
            schedule_json = synchronizer.open_api_json('get_schedule', params, api_config)
            games = (schedule_json or {}).get('games', [])
            first_game = games[0] if games else {}
            print(
                f'Dumpster Fire probe {label}: {len(games)} games '
                f'first_game_id={first_game.get("game_id")} '
                f'first={first_game.get("away_team", "").strip()} @ {first_game.get("home_team", "").strip()}'
            )

        try:
            team_source, team_soup = synchronizer.open_team_page(f'display-schedule?team={team_id}')
            team_api_config = synchronizer.api_config_from_soup(team_soup)
            print(
                f'Dumpster Fire team page {team_source}: '
                f'league_id={team_api_config.get("league_id")} '
                f'season_id={team_api_config.get("season_id")} '
                f'proxy_base={team_api_config.get("proxy_base")} '
                f'proxy_session={"yes" if team_api_config.get("proxy_session") else "no"}'
            )
            team_schedule_json = synchronizer.open_api_json(
                'get_schedule',
                {
                    'league_id': team_api_config.get('league_id', 1),
                    'season_id': team_api_config.get('season_id') or None,
                    'stat_class': current_stat_class,
                    'team_id': team_id,
                },
                team_api_config,
            )
            team_games = (team_schedule_json or {}).get('games', [])
            print(f'Dumpster Fire team page config schedule: {len(team_games)} games')
        except Exception as error:
            print(f'Dumpster Fire team page probe failed: {error}')

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
        self.assertEqual(api_config['season_id'], 0)
        self.assertEqual(api_config['stat_class'], 0)
        self.assertEqual(
            api_config['proxy_base'],
            'https://stats.sharksice.timetoscore.com/test/api-proxy.php',
        )
        self.assertEqual(api_config['proxy_session'], 'session-token')

    def test_api_config_from_soup_reads_explicit_timetoscore_season(self):
        html = '''
            <body>
                <div id="standings-root"
                     data-league="1"
                     data-season="74"></div>
            </body>
        '''

        synchronizer = self.make_synchronizer()
        api_config = synchronizer.api_config_from_soup(BeautifulSoup(html, 'html.parser'))

        self.assertEqual(api_config['season_id'], 74)

    def test_default_stat_class_prefers_league_default_then_config_then_one(self):
        synchronizer = self.make_synchronizer()

        self.assertEqual(
            synchronizer.default_stat_class({'default_stat_class_tag': '2'}, {'stat_class': 1}),
            2,
        )
        self.assertEqual(
            synchronizer.default_stat_class({'default_stat_class_tag': None}, {'stat_class': '3'}),
            3,
        )
        self.assertEqual(
            synchronizer.default_stat_class({'default_stat_class_tag': None}, {'stat_class': 0}),
            1,
        )

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
        self.assertEqual(
            requests_get_mock.call_args.kwargs['timeout'],
            Synchronizer.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
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
        self.assertEqual(
            requests_get_mock.call_args.kwargs['timeout'],
            Synchronizer.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status.assert_called_once_with()

    @patch('webserver.data_synchronizer.time.monotonic', side_effect=[100.0, 140.0])
    @patch('webserver.data_synchronizer.write_log')
    @patch('webserver.data_synchronizer.Database')
    def test_locker_room_timeout_is_logged_and_database_is_closed(
            self, database_cls, write_log_mock, monotonic_mock):
        synchronizer = self.make_synchronizer()
        synchronizer.open_page = Mock(side_effect=requests.Timeout('read timed out'))

        synchronizer.locker_room_assignment_check()

        database_cls.return_value.close.assert_called_once_with()
        write_log_mock.assert_has_calls([
            call('INFO', 'Locker room assignment check started'),
            call('ERROR', 'Failed locker room assignment check read timed out'),
            call('INFO', 'Locker room assignment check finished duration_seconds=40.00'),
        ])

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
                    'home_id': '323',
                    'away_id': '310',
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
                patch.object(synchronizer, 'open_api_json', side_effect=lambda endpoint, params, api_config=None: api_responses[endpoint]) as open_api_json_mock:
            self.assertTrue(synchronizer.sync_season('https://stats.sharksice.timetoscore.com/display-stats.php?league=1'))

        self.assertEqual(
            open_api_json_mock.call_args_list[1].args[1],
            {
                'league_id': 1,
                'season_id': None,
                'stat_class': 1,
            },
        )
        self.assertEqual(
            open_api_json_mock.call_args_list[2].args[1],
            {
                'league_id': 1,
                'season_id': None,
                'stat_class': 1,
            },
        )
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
    def test_sync_api_season_filters_league_schedule_to_tracked_teams(self, write_log_mock):
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
                                    {'id': 4844, 'team_name': 'Dumpster Fire '},
                                    {'id': 9999, 'team_name': 'Not Tracked '},
                                ],
                            }],
                        }],
                    }],
                },
            },
            'get_schedule': {
                'games': [
                    {
                        'game_id': '578889',
                        'date': '2026-06-14',
                        'time': '18:30:00',
                        'location': 'San Jose Grey',
                        'home_id': '4917',
                        'away_id': '4844',
                        'home_team': 'DragonHawks ',
                        'away_team': 'Dumpster Fire ',
                        'home_goals': None,
                        'away_goals': None,
                        'level_name': 'Adult Division 7B',
                        'gtype_name': 'Regular',
                        'league_name': 'SIAHL@SJ',
                        'timezn': 'America/Los_Angeles',
                        'result_flag': None,
                        'game_status': 'NOT STARTED',
                    },
                    {
                        'game_id': '578890',
                        'date': '2026-06-14',
                        'time': '20:30:00',
                        'location': 'San Jose Grey',
                        'home_id': '9999',
                        'away_id': '8888',
                        'home_team': 'Not Tracked ',
                        'away_team': 'Also Not Tracked ',
                        'home_goals': None,
                        'away_goals': None,
                        'level_name': 'Adult Division 7B',
                        'gtype_name': 'Regular',
                        'league_name': 'SIAHL@SJ',
                        'timezn': 'America/Los_Angeles',
                        'result_flag': None,
                        'game_status': 'NOT STARTED',
                    },
                ],
            },
        }
        synchronizer = self.make_synchronizer()
        synchronizer.db = FakeSyncDatabase(tracked_external_ids=[4844])
        synchronizer.synced_games_list = []
        synchronizer.new_games_map = {}

        with patch.object(synchronizer, 'open_api_json', side_effect=lambda endpoint, params, api_config=None: api_responses[endpoint]) as open_api_json_mock:
            self.assertTrue(synchronizer.sync_api_season(BeautifulSoup(html, 'html.parser')))

        schedule_calls = [
            call_args.args[1]
            for call_args in open_api_json_mock.call_args_list
            if call_args.args[0] == 'get_schedule'
        ]
        self.assertEqual(
            schedule_calls,
            [{
                'league_id': 1,
                'season_id': None,
                'stat_class': 1,
            }],
        )
        self.assertEqual(synchronizer.db.get_external_ids_by_team_name('Dumpster Fire'), [4844])
        self.assertEqual(len(synchronizer.db.added_games), 1)
        self.assertEqual(synchronizer.db.added_games[0].game_id, 578889)

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
            'Failed synchronization of TimeToScore API get_leagues for league 1: None',
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
