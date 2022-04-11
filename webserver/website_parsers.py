'''
website_parsers

Classes to handle parsing of html data and aggregate it into python data structures that are used
to synchronize with the database. Specifically for Sharks Ice at San Jose Adult League.
'''

import datetime
import traceback
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from webserver.logging import write_log

class TeamPageParser:

    GAMES_TABLE = 'Game Results'
    PLAYERS_TABLE = 'Player Stats'
    GOALIES_TABLE = 'Goalie Stats'

    # row 0 -> title, row 1 -> column headers, row 3+ -> data
    TABLE_DATA_NAME_INDEX = 0
    TABLE_DATA_COLUMN_HEADERS_INDEX = 1
    TABLE_DATA_START_INDEX = 2

    def __init__(self, url, team_soup):
        self.url = url
        self.soup = team_soup

        self.parsers = {}
        self.parsers[self.GAMES_TABLE] = self.parse_games
        self.parsers[self.PLAYERS_TABLE] = self.parse_players
        self.parsers[self.GOALIES_TABLE] = self.parse_goalies

        self.games = []
        self.player_stats = []
        self.goalie_stats = []

    def parse(self):
        ''' Finds the important tables in the teams page and initiates parsing of each of them '''
        for table in self.soup.body.find_all('table'):

            try:
                name = self.table_name(table)
                if name in self.parsers:
                    self.parsers[name](table)

            except Exception as error:
                print(f'Failed parsing of {self.url}')
                traceback.print_exc()
                return False

        return True

    def table_name(self, table):
        ''' Retrieves the name of the table contained as the only cell in the top row '''
        rows = table.find_all('tr')

        # table title is the only cell of the first row
        if len(rows[self.TABLE_DATA_NAME_INDEX].find_all('th')) != 1:
            raise Exception(f'table_name could not be found. Expected 1 cell. '
                            f'Got {len(rows[self.TABLE_DATA_NAME_INDEX].find_all("th"))}')

        return self.cell_contents(rows[self.TABLE_DATA_NAME_INDEX].th)

    def cell_contents(self, cell):
        ''' Returns a string with the contents of a table cell, '<th></th>' '''
        
        result = cell.get_text()
        result = result.strip()

        return result

    def table_row_contents(self, row):
        ''' Returns an array with the contents of each cell in the row '''

        result_array = []

        cell_type = 'td' if row.td else 'th'

        for cell in row.find_all(cell_type):
            result_array.append(self.cell_contents(cell))

        return result_array

    def parse_games(self, table):
        rows = table.find_all('tr')
        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        # adjust duplicate column names of "Goals" to "Home Goals" and "Away Goals"
        for i in range(len(column_names)):
            if column_names[i] == 'Goals':

                if column_names[i - 1] != 'Away' and column_names[i - 1] != 'Home':
                    raise Exception(f'Unexpected ordering of games table columns')

                column_names[i] = f'{column_names[i - 1]} Goals'

        self.games = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            game_details = self.table_row_contents(row)
            game_dict = dict(zip(column_names, game_details))
            game_parser = GameParser(game_dict)

            self.games.append(game_parser)

    def parse_players(self, table):
        rows = table.find_all('tr')
        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        self.player_stats = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            player_details = self.table_row_contents(row)
            player_dict = dict(zip(column_names, player_details))

            self.player_stats.append(player_dict)

    def parse_goalies(self, table):
        rows = table.find_all('tr')
        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        self.goalie_stats = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            player_details = self.table_row_contents(row)
            player_dict = dict(zip(column_names, player_details))

            self.goalie_stats.append(player_dict)

class BaseParser:
    def __init__(self):
        pass

    def instance_attributes_string(self):
        ''' Iterates instance attributes and concatinates them into a dict-like string '''
        output = '{'
        for attribute, value in self.__dict__.items():
            if len(output) > 1:
                output = output + ', '
            output = output + f'{attribute}: '

            if type(value) == str:
                output = output + f'\'{value}\''
            else:
                output = output + f'{value}'

        output = output + '}'
        return output

class GameParser(BaseParser):

    def __init__(self, game_dict):

        self.id = self.parse_id(game_dict['Game'])
        self.completed = 0 if game_dict['Game'].find('*') == -1 else 1

        # Wed Jan 19
        # 9:45 PM
        SEASON_NUM = 52
        year = self.calculate_year(game_dict['Date'], SEASON_NUM)
        dt = datetime.datetime.strptime(f'{year} {game_dict["Date"]} {game_dict["Time"]}',
                                                  f'%Y %a %b %d %I:%M %p')
        pacific = ZoneInfo('US/Pacific')

        self.datetime = dt.replace(tzinfo=pacific)
        self.rink = game_dict['Rink']
        self.league = game_dict['League']
        self.level = game_dict['Level']
        self.home_team = game_dict['Home']
        self.away_team = game_dict['Away']
        self.type = game_dict['Type']
        self.home_goals = 0
        self.away_goals = 0
        self.shootout = 0

        try:
            self.home_goals = int(game_dict['Home Goals'].replace('S', ''))
            self.away_goals = int(game_dict['Away Goals'].replace('S', ''))

            if game_dict['Home Goals'].find('S') != -1 or game_dict['Away Goals'].find('S') != -1:
                self.shootout = 1
        except:
            pass

    def parse_id(self, id_str):
        id_str = id_str.replace('*', '') # completed games
        id_str = id_str.replace('^', '') # in progress games

        return int(id_str)

    def calculate_year(self, date_str, season_num):
        ''' The Sharks Ice site does not include years on their datetime indicators for games,
            so the year needs to be inferred.

            TODO: This current logic is rickety and needs to be updated
        '''
        year = 0

        if season_num >= 52:
            # 3 seasons a year: winter/spring, summer, fall/winter
            year = 2022 + int((season_num - 52) / 3)
        else:
            write_log('ERROR', f'Unhandled year')
        return year

    def __repr__(self):
        return self.instance_attributes_string()

    def __str__(self):
        print(self.instance_attributes_string())
