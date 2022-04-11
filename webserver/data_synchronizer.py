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
from webserver.website_parsers import TeamPageParser
from webserver.logging import write_log

class Synchronizer:

    SHARKS_ICE_BASE_URL = 'https://stats.sharksice.timetoscore.com/'
    SHARKS_ICE_SEASON_ENDPOINT = 'display-stats.php?league=1'
    SHARKS_ICE_TEAM_ENDPOINT = 'display-schedule'

    SYNCHRONIZE_INTERVAL_HOURS = 4
    NOTIFY_CHECK_INTERVAL_HOURS = 1

    def __init__(self):
        self.db = None

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

        if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
            self.scheduler.start()

    def notify(self):
        ''' notify runs periodically to the check the datetime of upcoming games
            and sends out email notifications to everyone on those teams '''
        write_log('INFO', f'Notify sync')
        self.db = Database()

        coming_soon = self.db.get_games_coming_soon()

        for game in coming_soon:
            write_log('INFO', f'Notify coming soon {game.game_id} ({game.scheduled_at})')
            send_game_coming_soon(self.db, game)
            game.did_notify_coming_soon = True

        # save updates to game was-notification-sent
        self.db.commit_changes()

    def sync(self):
        write_log('INFO', f'Synchronization started')
        self.db = Database()

        source, soup = self.open_season_page()
        for link in soup.find_all('a'):
            
            href = link.get('href')
            if href.find(self.SHARKS_ICE_TEAM_ENDPOINT) == -1:
                print(f'SKIPPING {link}, not a team page')
                continue

            print(f'Parsing {link}')
            team_source, team_soup = self.open_team_page(href)
            team_parser = TeamPageParser(team_source, team_soup)
            success = team_parser.parse()

            if not success:
                print(f'Failed synchronization of website')
                return False

            for game in team_parser.games:
                self.db.add_game(game)

        write_log('INFO', f'Synchronization complete')
        return True

    def open_season_page(self):
        url = f'{self.SHARKS_ICE_BASE_URL}{self.SHARKS_ICE_SEASON_ENDPOINT}'
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

    ## For local testing
    def sync_local_file(self, path):
        ''' notify runs periodically to the check the datetime of upcoming games
            and sends out email notifications to everyone on those teams '''
        self.db = Database()

        source, soup = self.open_test_file(path)
        team_parser = TeamPageParser(source, soup)
        success = team_parser.parse()

        if not success:
            print(f'Failed synchronization of website')
            return

        for game in team_parser.games:
            self.db.add_game(game)

        print(f'Synchronization complete')

    def open_test_file(self, path):
        f = open(path)
        soup = BeautifulSoup(f, 'html.parser')

        return path, soup
