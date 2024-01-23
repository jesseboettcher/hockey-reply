'''
data_synchronizer

Top level class to pull data from the shark's ice web site, feed it into the html parsers, and use
the parser output to update the database with the latest data.
'''
import os
import requests

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from bs4 import BeautifulSoup

from webserver.database.hockey_db import Database, get_db
from webserver.email import send_game_coming_soon
from webserver.website_parsers import LockerRoomPageParser, TeamPageParser
from webserver.logging import print_log, write_log

class Synchronizer:

    SHARKS_ICE_BASE_URL = 'https://stats.sharksice.timetoscore.com/'
    SHARKS_ICE_SEASON_ENDPOINTS = [
        'display-stats.php?league=1',
    ]
    SHARKS_ICE_TEAM_ENDPOINT = 'display-schedule'
    SHARKS_ICE_LOCKROOM_ENDPOINT = 'display-lr-assignments.php'

    SYNCHRONIZE_INTERVAL_HOURS = 4
    NOTIFY_CHECK_INTERVAL_HOURS = 1
    LOCKER_ROOM_INTERVAL_SECONDS = 15

    def __init__(self):
        self.db = None
        self.new_games_map = {}

        executors = {
            'default': {'type': 'threadpool', 'max_workers': 1},
            'processpool': ProcessPoolExecutor(max_workers=1)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        self.scheduler = BackgroundScheduler()
        self.scheduler.configure(executors=executors, job_defaults=job_defaults)
        self.scheduler.add_job(self.sync, 'interval', hours=self.SYNCHRONIZE_INTERVAL_HOURS)
        self.scheduler.add_job(self.notify, 'interval', hours=self.NOTIFY_CHECK_INTERVAL_HOURS)
        self.scheduler.add_job(self.locker_room_assignment_check, 'interval', seconds=self.LOCKER_ROOM_INTERVAL_SECONDS)

        if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
            self.scheduler.start()

    def locker_room_assignment_check(self):
        self.db = Database()

        locker_room_source, locker_room_soup = self.open_page(f'{self.SHARKS_ICE_BASE_URL}{self.SHARKS_ICE_LOCKROOM_ENDPOINT}')
        locker_room_parser = LockerRoomPageParser(locker_room_source, locker_room_soup)
        locker_room_parser.parse()

        self.db.update_locker_rooms(locker_room_parser)

    def notify(self):
        ''' notify runs periodically to the check the datetime of upcoming games
            and sends out email notifications to everyone on those teams '''
        write_log('INFO', f'Notify sync')
        self.db = Database()

        for team_id in self.new_games_map.keys():
            write_log('INFO', f'Games added {self.new_games_map[team_id]}')
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

            if game.id not in self.synced_games_list:
                write_log('INFO', f'Game DELETED game_id {game.id}')
                # TODO
                # self.db.remove_game_by_id(game.id)
                # notify teams

    def sync(self):
        write_log('INFO', f'Synchronization started')
        self.db = Database()
        self.new_games_map = {}
        self.synced_games_list = []

        any_sync_failures = False

        for season in self.SHARKS_ICE_SEASON_ENDPOINTS:
            url = f'{self.SHARKS_ICE_BASE_URL}{season}'
            if not self.sync_season(url):
                any_sync_failures = True

        if not any_sync_failures:
            self.check_deleted_games()

        write_log('INFO', f'Synchronization complete')
        return True

    def sync_season(self, url):

        source, soup = self.open_season_page(url)
        for link in soup.find_all('a'):
            
            href = link.get('href')
            if href.find(self.SHARKS_ICE_TEAM_ENDPOINT) == -1:
                print_log(f'SKIPPING {link}, not a team page')
                continue

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

    def open_season_page(self, url):
        req = requests.get(url)
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')

        return url, soup


    def open_team_page(self, team_endpoint):
        url = f'{self.SHARKS_ICE_BASE_URL}{team_endpoint}'
        req = requests.get(url)
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')

        return url, soup

    def open_page(self, url):
        req = requests.get(url)
        data = req.content
        soup = BeautifulSoup(data, 'html.parser')

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
