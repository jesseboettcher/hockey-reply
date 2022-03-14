'''
data_synchronizer

Top level class to pull data from the shark's ice web site, feed it into the html parsers, and use
the parser output to update the database with the latest data.
'''

import requests

from bs4 import BeautifulSoup

from webserver.database.hockey_db import Database
from webserver.website_parsers import TeamPageParser

class Synchronizer:

    SHARKS_ICE_BASE_URL = 'https://stats.sharksice.timetoscore.com/'
    SEASON_ENDPOINT = 'display-stats.php?league=1'
    TEAM_ENDPOINT = 'display-schedule'
    TEST_FILE_PATH = 'test/team.html'

    def __init__(self):
        pass

    def sync(self):
        db = Database(False)

        source, soup = self.open_season_page()
        for link in soup.find_all('a'):
            
            href = link.get('href')
            if href.find(self.TEAM_ENDPOINT) == -1:
                print(f'SKIPPING {link}')
                continue

            print(f'Parsing {link}')
            team_source, team_soup = self.open_team_page(href)
            team_parser = TeamPageParser(team_source, team_soup)
            success = team_parser.parse()

            if not success:
                print(f'Failed synchronization of website')
                return False

            for game in team_parser.games:
                db.add_game(game)

        print(f'Synchronization complete')
        return True

    def sync_local_file(self):
        db = Database(True)

        source, soup = self.open_test_file()
        team_parser = TeamPageParser(source, soup)
        success = team_parser.parse()

        if not success:
            print(f'Failed synchronization of website')
            return

        for game in team_parser.games:
            db.add_game(game)

        print(f'Synchronization complete')

    def open_test_file(self):
        f = open(self.TEST_FILE_PATH)
        soup = BeautifulSoup(f, 'html.parser')

        return self.TEST_FILE_PATH, soup

    def open_season_page(self):
        url = f'{self.SHARKS_ICE_BASE_URL}{self.SEASON_ENDPOINT}'
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
