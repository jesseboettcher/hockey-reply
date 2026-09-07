'''
data_synchronizer

Top level class to pull data from the shark's ice web site, feed it into the html parsers, and use
the parser output to update the database with the latest data.
'''
import os
import datetime
import hashlib
import hmac
import requests
import time
from urllib.parse import quote_plus, urljoin

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from bs4 import BeautifulSoup

from webserver.database.hockey_db import Database, get_db
from webserver.email import send_game_coming_soon, send_new_games
from webserver.website_parsers import ApiGameParser, LockerRoomPageParser, TeamPageParser
from webserver.logging import print_log, write_log

class Synchronizer:

    SYNC_SOURCE_API = 'api'
    SYNC_SOURCE_SCRAPER = 'scraper'

    SHARKS_ICE_BASE_URL = 'https://stats.sharksice.timetoscore.com/'
    SHARKS_ICE_API_BASE_URL = 'https://api.sharksice.timetoscore.com/'
    SHARKS_ICE_API_KEY = 'web'
    SHARKS_ICE_API_SECRET = 'i8IC4I8cCLdLGWiKk5Ukw4FfIjBtvOG4'
    SHARKS_ICE_SYNC_SOURCE = SYNC_SOURCE_API
    SHARKS_ICE_REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
    }
    EMPTY_BODY_MD5 = 'd41d8cd98f00b204e9800998ecf8427e'
    SHARKS_ICE_SEASON_ENDPOINTS = [
        'display-stats.php?league=1',
    ]
    SHARKS_ICE_TEAM_ENDPOINT = 'display-schedule'
    SHARKS_ICE_LOCKROOM_ENDPOINT = 'display-lr-assignments.php'

    SYNCHRONIZE_INTERVAL_HOURS = 4
    NOTIFY_CHECK_INTERVAL_HOURS = 1
    LOCKER_ROOM_INTERVAL_SECONDS = 300
    STARTUP_JOB_MISFIRE_GRACE_SECONDS = 60
    SHARKS_ICE_REQUEST_TIMEOUT_SECONDS = (10, 30)
    CHECK_DELETED_GAMES = False
    TIMETOSCORE_SYNC_ENABLED = True
    NOTIFY_ENABLED = True
    LOCKER_ROOM_SYNC_ENABLED = False
    LOCAL_LOCKER_ROOM_SYNC_ONLY = False
    LOCAL_TIMETOSCORE_SYNC_ONLY = False
    SYNC_ONLY_TRACKED_TEAMS = True

    def __init__(self):
        self.db = None
        self.new_games_map = {}

        executors = {
            'default': {'type': 'threadpool', 'max_workers': 1},
            'locker_room': {'type': 'threadpool', 'max_workers': 1},
            'processpool': ProcessPoolExecutor(max_workers=1)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        self.scheduler = BackgroundScheduler()
        self.scheduler.configure(executors=executors, job_defaults=job_defaults)
        timetoscore_sync_enabled = self.TIMETOSCORE_SYNC_ENABLED or self.LOCAL_TIMETOSCORE_SYNC_ONLY
        notify_enabled = self.NOTIFY_ENABLED or self.LOCAL_TIMETOSCORE_SYNC_ONLY
        locker_room_sync_enabled = (
            self.LOCKER_ROOM_SYNC_ENABLED
            or self.LOCAL_LOCKER_ROOM_SYNC_ONLY
            or self.LOCAL_TIMETOSCORE_SYNC_ONLY
        )

        if timetoscore_sync_enabled and not self.LOCAL_LOCKER_ROOM_SYNC_ONLY:
            self.scheduler.add_job(
                self.sync,
                'interval',
                hours=self.SYNCHRONIZE_INTERVAL_HOURS,
                next_run_time=datetime.datetime.now(),
                misfire_grace_time=self.STARTUP_JOB_MISFIRE_GRACE_SECONDS,
            )

        if notify_enabled and not self.LOCAL_LOCKER_ROOM_SYNC_ONLY:
            self.scheduler.add_job(self.notify, 'interval', hours=self.NOTIFY_CHECK_INTERVAL_HOURS)

        if locker_room_sync_enabled:
            self.schedule_locker_room_assignment_check()

        if os.getenv('HOCKEY_REPLY_ENV') == 'prod' or self.local_timetoscore_only_mode():
            self.scheduler.start()

    def local_timetoscore_only_mode(self):
        return self.LOCAL_LOCKER_ROOM_SYNC_ONLY or self.LOCAL_TIMETOSCORE_SYNC_ONLY

    def schedule_locker_room_assignment_check(self):
        self.scheduler.add_job(
            self.locker_room_assignment_check,
            'interval',
            seconds=self.LOCKER_ROOM_INTERVAL_SECONDS,
            next_run_time=datetime.datetime.now(),
            misfire_grace_time=self.STARTUP_JOB_MISFIRE_GRACE_SECONDS,
            executor='locker_room',
        )

    def locker_room_assignment_check(self):
        started_at = time.monotonic()
        db = None
        write_log('INFO', 'Locker room assignment check started')

        try:
            db = Database()
            locker_room_source, locker_room_soup = self.open_page(f'{self.SHARKS_ICE_BASE_URL}{self.SHARKS_ICE_LOCKROOM_ENDPOINT}')
            write_log(
                'INFO',
                f'Locker room fetch source={locker_room_source} tables={len(locker_room_soup.find_all("table"))} rows={len(locker_room_soup.find_all("tr"))}',
            )
            locker_room_parser = LockerRoomPageParser(locker_room_source, locker_room_soup)
            locker_room_parser.parse()

            db.update_locker_rooms(locker_room_parser)
        except Exception as error:
            write_log('ERROR', f'Failed locker room assignment check {error}')
        finally:
            if db is not None:
                db.close()
            duration_seconds = time.monotonic() - started_at
            write_log('INFO', f'Locker room assignment check finished duration_seconds={duration_seconds:.2f}')

    def notify(self):
        ''' notify runs periodically to the check the datetime of upcoming games
            and sends out email notifications to everyone on those teams '''
        write_log('INFO', f'Notify sync')
        self.db = Database()

        for team_id, game_ids in self.new_games_map.items():
            write_log('INFO', f'Games added {game_ids}')
            send_new_games(self.db, team_id, game_ids)
        self.new_games_map = {}

        coming_soon = self.db.get_games_coming_soon()

        for game in coming_soon:
            write_log('INFO', f'Notify coming soon {game.game_id} ({game.scheduled_at})')
            send_game_coming_soon(self.db, game)
            game.did_notify_coming_soon = True

            # paranoid extra save updates to game was-notification-sent
            # because it was not updating for game 382145 on Mar 30 2023 during the day
            self.db.commit_changes()

        # save updates to game was-notification-sent
        self.db.commit_changes()

    def check_deleted_games(self):
        all_games = self.db.get_games()

        for game in all_games:
            if game.completed:
                continue

            if game.game_id not in self.synced_games_list:
                write_log('INFO', f'Game DELETED game_id {game.game_id}')
                # TODO
                # self.db.remove_game_by_id(game.game_id)
                # notify teams

    def sync(self):
        write_log('INFO', f'Synchronization started')
        self.db = Database()
        self.new_games_map = {}
        self.synced_games_list = []

        any_sync_failures = False

        for season in self.SHARKS_ICE_SEASON_ENDPOINTS:
            url = f'{self.SHARKS_ICE_BASE_URL}{season}'
            try:
                sync_succeeded = self.sync_season(url)
            except Exception as error:
                write_log('ERROR', f'Failed synchronization of season at {url}: {error}')
                sync_succeeded = False

            if not sync_succeeded:
                any_sync_failures = True

        if not any_sync_failures and self.CHECK_DELETED_GAMES:
            self.check_deleted_games()

        if any_sync_failures:
            write_log('ERROR', 'Synchronization complete with failures')
            return False

        write_log('INFO', f'Synchronization complete')
        return True

    def sync_season(self, url):

        source, soup = self.open_season_page(url)

        if self.SHARKS_ICE_SYNC_SOURCE == self.SYNC_SOURCE_API:
            return self.sync_api_season(soup, source)

        if self.SHARKS_ICE_SYNC_SOURCE != self.SYNC_SOURCE_SCRAPER:
            write_log('ERROR', f'Unknown synchronization source {self.SHARKS_ICE_SYNC_SOURCE}')
            return False

        found_team_links = False
        for link in soup.find_all('a'):
            
            href = link.get('href')
            if href is None or href.find(self.SHARKS_ICE_TEAM_ENDPOINT) == -1:
                print_log(f'SKIPPING {link}, not a team page')
                continue

            found_team_links = True
            team_name = link.string.strip()

            print_log(f'Parsing {team_name} at {link}')
            team_source, team_soup = self.open_team_page(href)
            team_parser = TeamPageParser(team_source, team_soup)
            success = team_parser.parse()

            if not success:
                write_log('ERROR', f'Failed synchronization of website at {url}')
                return False

            self.db.add_team(team_name, team_parser.external_id)

            for game in team_parser.games:
                game_is_new = self.db.add_game(game)
                db_game = self.db.get_game_by_id(game.id)

                self.synced_games_list.append(game.id)

                if game_is_new:
                    if not db_game.home_team_id in self.new_games_map:
                        self.new_games_map[db_game.home_team_id] = []
                    if not db_game.away_team_id in self.new_games_map:
                        self.new_games_map[db_game.away_team_id] = []

                    self.new_games_map[db_game.home_team_id].append(db_game.game_id)
                    self.new_games_map[db_game.away_team_id].append(db_game.game_id)

        if not found_team_links:
            write_log('ERROR', f'No legacy team links found at {url}')
            return False

        return True

    def sync_api_season(self, soup, source_url=None):
        api_config = self.api_config_from_soup(soup, source_url)
        league_id = api_config.get('league_id', 1)

        leagues_json = self.open_api_json('get_leagues', {'league_id': league_id}, api_config)
        if not leagues_json or not leagues_json.get('leagues'):
            write_log('ERROR', f'Failed synchronization of TimeToScore API get_leagues for league {league_id}: {leagues_json}')
            return False

        league = leagues_json['leagues'][0]
        season_id = api_config.get('season_id') or None
        stat_class = self.default_stat_class(league, api_config)

        standings_json = self.open_api_json(
            'get_standings',
            {
                'league_id': league_id,
                'season_id': season_id,
                'stat_class': stat_class,
            },
            api_config,
        )
        if not standings_json:
            write_log('ERROR', f'Failed synchronization of TimeToScore API get_standings for league {league_id} season {season_id}')
            return False

        teams = self.teams_from_standings(standings_json)
        tracked_team_ids = self.tracked_external_team_ids()
        if self.SYNC_ONLY_TRACKED_TEAMS and tracked_team_ids:
            write_log('INFO', f'TimeToScore API sync filtering league schedule to tracked teams {sorted(tracked_team_ids)}')

        for team_id, team_name in teams.items():
            self.db.add_team(team_name, team_id)

        schedule_json = self.open_api_json(
            'get_schedule',
            {
                'league_id': league_id,
                'season_id': season_id,
                'stat_class': stat_class,
            },
            api_config,
        )
        if not schedule_json:
            write_log('ERROR', f'Failed synchronization of TimeToScore API get_schedule for league {league_id} season {season_id}')
            return False

        for game_dict in schedule_json.get('games', []):
            if self.SYNC_ONLY_TRACKED_TEAMS and tracked_team_ids and not self.game_includes_tracked_team(game_dict, tracked_team_ids):
                continue

            self.sync_api_game(game_dict)

        return True

    def game_includes_tracked_team(self, game_dict, tracked_team_ids):
        for key in ('home_id', 'away_id'):
            try:
                team_id = int(game_dict.get(key))
            except (TypeError, ValueError):
                continue
            if team_id in tracked_team_ids:
                return True

        return False

    def sync_api_game(self, game_dict):
        game = ApiGameParser(game_dict)
        if not game.parse_success:
            return

        game_is_new = self.db.add_game(game)
        db_game = self.db.get_game_by_id(game.id)

        if game.id not in self.synced_games_list:
            self.synced_games_list.append(game.id)

        if game_is_new:
            if not db_game.home_team_id in self.new_games_map:
                self.new_games_map[db_game.home_team_id] = []
            if not db_game.away_team_id in self.new_games_map:
                self.new_games_map[db_game.away_team_id] = []

            self.new_games_map[db_game.home_team_id].append(db_game.game_id)
            self.new_games_map[db_game.away_team_id].append(db_game.game_id)

    def tracked_external_team_ids(self):
        try:
            tracked_teams = self.db.get_rostered_teams()
        except AttributeError:
            try:
                tracked_teams = self.db.get_teams()
            except AttributeError:
                return set()

        team_ids = set()
        for team in tracked_teams:
            try:
                external_id = int(team.external_id)
            except (AttributeError, TypeError, ValueError):
                continue
            if external_id > 0:
                team_ids.add(external_id)

        return team_ids

    def api_config_from_soup(self, soup, source_url=None):
        root = (
            soup.find(id='standings-root')
            or soup.find(id='schedule-root')
            or soup.find(id='team-root')
            or soup.find(id='scorebug-root')
        )
        if not root:
            return {
                'api_base': self.SHARKS_ICE_API_BASE_URL,
                'api_key': self.SHARKS_ICE_API_KEY,
                'api_secret': self.SHARKS_ICE_API_SECRET,
                'league_id': 1,
                'season_id': 0,
                'stat_class': 1,
                'proxy_base': '',
                'proxy_session': '',
            }

        return {
            'api_base': root.get('data-api-base') or self.SHARKS_ICE_API_BASE_URL,
            'api_key': root.get('data-api-key') or self.SHARKS_ICE_API_KEY,
            'api_secret': self.rot13(root.get('data-api-secret') or '') or self.SHARKS_ICE_API_SECRET,
            'league_id': int(root.get('data-league') or 1),
            'season_id': int(root.get('data-season') or 0),
            'stat_class': int(root.get('data-stat-class') or 0),
            'proxy_base': urljoin(source_url or self.SHARKS_ICE_BASE_URL, root.get('data-proxy-base') or ''),
            'proxy_session': root.get('data-proxy-session') or '',
        }

    def default_stat_class(self, league, api_config):
        for value in (league.get('default_stat_class_tag'), api_config.get('stat_class'), 1):
            try:
                stat_class = int(value)
            except (TypeError, ValueError):
                continue
            if stat_class > 0:
                return stat_class

        return 1

    def teams_from_standings(self, standings_json):
        teams = {}
        for league in standings_json.get('standings', {}).get('leagues', []):
            for level in league.get('levels', []):
                for conference in level.get('conferences', []):
                    for team in conference.get('teams', []):
                        teams[int(team['id'])] = (team.get('team_name') or team.get('name') or '').strip()

        return teams

    def rot13(self, value):
        result = ''
        for char in value:
            if 'a' <= char <= 'z':
                result += chr(ord('a') + (ord(char) - ord('a') + 13) % 26)
            elif 'A' <= char <= 'Z':
                result += chr(ord('A') + (ord(char) - ord('A') + 13) % 26)
            else:
                result += char

        return result

    def open_api_json(self, endpoint, params, api_config=None):
        api_config = api_config or {}
        headers = dict(self.SHARKS_ICE_REQUEST_HEADERS)

        if api_config.get('proxy_base') and api_config.get('proxy_session'):
            url = self.proxy_api_url(endpoint, params, api_config)
            headers['X-Proxy-Session'] = api_config['proxy_session']
        else:
            url = self.api_url(endpoint, params, api_config)

        try:
            req = requests.get(
                url,
                headers=headers,
                timeout=self.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            write_log('ERROR', f'Failed TimeToScore API request for {endpoint}: {error}')
            return None

        try:
            return req.json()
        except ValueError:
            body_preview = req.text[:300].replace('\n', ' ')
            write_log('ERROR', f'Failed TimeToScore API JSON for {endpoint}: status={req.status_code} body={body_preview}')
            return None

    def proxy_api_url(self, endpoint, params, api_config):
        proxy_params = {
            'endpoint': endpoint,
        }

        for key, value in (params or {}).items():
            if value is None or value == '' or value == -1:
                continue
            proxy_params[key] = str(value)

        query_string = '&'.join(
            f'{quote_plus(key)}={quote_plus(proxy_params[key])}'
            for key in sorted(proxy_params)
        )

        return f'{api_config["proxy_base"]}?{query_string}'

    def api_url(self, endpoint, params, api_config=None):
        api_config = api_config or {}
        api_base = api_config.get('api_base') or self.SHARKS_ICE_API_BASE_URL
        api_key = api_config.get('api_key') or self.SHARKS_ICE_API_KEY
        api_secret = api_config.get('api_secret') or self.SHARKS_ICE_API_SECRET

        signed_params = {
            'auth_key': api_key,
            'auth_timestamp': str(int(time.time())),
            'body_md5': self.EMPTY_BODY_MD5,
        }

        for key, value in (params or {}).items():
            if value is None or value == '' or value == -1:
                continue
            signed_params[key] = str(value)

        query_string = '&'.join(
            f'{quote_plus(key)}={quote_plus(signed_params[key])}'
            for key in sorted(signed_params)
        )
        to_sign = f'GET\n/{endpoint}\n{query_string}'
        signature = hmac.new(
            api_secret.encode(),
            to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f'{api_base.rstrip("/")}/{endpoint}?{query_string}&auth_signature={signature}'

    def open_season_page(self, url):
        req = requests.get(
            url,
            headers=self.SHARKS_ICE_REQUEST_HEADERS,
            timeout=self.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
        )
        req.raise_for_status()
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')

        return req.url, soup


    def open_team_page(self, team_endpoint):
        url = f'{self.SHARKS_ICE_BASE_URL}{team_endpoint}'
        req = requests.get(
            url,
            headers=self.SHARKS_ICE_REQUEST_HEADERS,
            timeout=self.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
        )
        req.raise_for_status()
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')

        return req.url, soup

    def open_page(self, url):
        req = requests.get(
            url,
            headers=self.SHARKS_ICE_REQUEST_HEADERS,
            timeout=self.SHARKS_ICE_REQUEST_TIMEOUT_SECONDS,
        )
        req.raise_for_status()
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')
        body_preview = req.text[:120].replace('\n', ' ')
        write_log('INFO', f'Fetched page {url} status={req.status_code} bytes={len(data)} final_url={req.url} body={body_preview}')

        return url, soup

    ## For local testing
    def sync_local_file(self, path):
        ''' notify runs periodically to the check the datetime of upcoming games
            and sends out email notifications to everyone on those teams '''
        self.db = Database()

        source, soup = self.open_test_file(path)
        team_parser = TeamPageParser(source, soup)
        success = team_parser.parse()

        if not success:
            print_log(f'Failed synchronization of website')
            return

        for game in team_parser.games:
            self.db.add_game(game)

        print_log(f'Synchronization complete')

    def open_test_file(self, path):
        f = open(path)
        soup = BeautifulSoup(f, 'html.parser')

        return path, soup
