'''
website_parsers

Classes to handle parsing of html data and aggregate it into python data structures that are used
to synchronize with the database. Specifically for Sharks Ice at San Jose Adult League.
'''

import datetime
import traceback
from urllib.parse import urlparse
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
        self.external_id = None
        self.season_num = None

    def parse(self):
        ''' Finds the important tables in the teams page and initiates parsing of each of them '''
        self.parse_url()

        for table in self.soup.body.find_all('table'):

            try:
                name = self.table_name(table)
                if name in self.parsers:
                    self.parsers[name](table)

            except Exception as error:
                write_log('ERROR', f'Failed parsing of {self.url} {traceback.print_exc()}')
                return False

        return True

    def parse_url(self):
        query = urlparse(self.url).query
        try:
            for query_item in query.split('&'):
                if query_item.split('=')[0] == 'team':
                    self.external_id = int(query_item.split('=')[1])
                if query_item.split('=')[0] == 'season':
                    self.season_num = int(query_item.split('=')[1])

        except Exception as e:
            write_log('ERROR', f'Failed to parse team external id from page url params {e}') 

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
            game_parser = GameParser(game_dict, self.season_num)

            if not game_parser.parse_success:
                # a game was skipped in a non-fatal way
                continue

            self.games.append(game_parser)

        return True

    def parse_players(self, table):
        rows = table.find_all('tr')
        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        self.player_stats = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            player_details = self.table_row_contents(row)
            player_dict = dict(zip(column_names, player_details))

            self.player_stats.append(player_dict)

        return True

    def parse_goalies(self, table):
        rows = table.find_all('tr')
        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        self.goalie_stats = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            player_details = self.table_row_contents(row)
            player_dict = dict(zip(column_names, player_details))

            self.goalie_stats.append(player_dict)

        return True

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

def hack_for_game_413541(game_id):
    # game 413541 was set to completed at least 10 hours before it started
    # causing it to disappear from choking hazards upcoming games list. game is Sep 10 @ 430pm PDT
    if int(game_id) == 413541:
        return True

    return False

class GameParser(BaseParser):

    def __init__(self, game_dict, parsed_season_num):

        self.id = self.parse_id(game_dict['Game'])
        self.completed = 0 if game_dict['Game'].find('*') == -1 or hack_for_game_413541(self.id) else 1

        # Wed Jan 19
        # 9:45 PM
        SEASON_NUM = parsed_season_num
        year = self.calculate_year(game_dict['Date'], SEASON_NUM)


        # Noon formatting breaks the parser. Replace with a valid time string
        time_str = game_dict['Time'].replace('12 Noon', '12:00 PM')

        try:
            dt = datetime.datetime.strptime(f'{year} {game_dict["Date"]} {time_str}',
                                                      f'%Y %a %b %d %I:%M %p')
        except:
            if game_dict['Game'] == '536764':
                # This game has an invalid date 2025 Wed Feb 29 9:00 PM
                pass
            else:
                # if it was not a known issue, log a monitored message
                write_log('ERROR', f'Failed synchronization of game {game_dict}')

            self.parse_success = False
            return

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

        self.parse_success = True

    def parse_id(self, id_str):
        id_str = id_str.replace('*', '') # completed games
        id_str = id_str.replace('^', '') # in progress games

        return int(id_str)

    def calculate_year(self, date_str, season_num):
        ''' The Sharks Ice site does not include years on their datetime indicators for games,
            so the year needs to be inferred.

            This logic will work for seasons over the last few years, but will not for parsing
            historical ones
        '''
        target_day_of_week = date_str.split(' ')[0]
        target_date_month_day = ' '.join(date_str.split(' ')[1:])

        current_year = datetime.datetime.now().year

        # Create a range of years to check
        year_range = range(current_year - 3, current_year + 2)

        # Iterate over the years and find the one where the day of week matches the one provided
        # by the web site parser
        year = current_year

        for test_year in year_range:

            try: # in case we try something invalid: Feb 29th on a non-leap year
                date = datetime.datetime.strptime(f'{str(test_year)} {target_date_month_day}', "%Y %b %d")
            except:
                continue

            day_name = date.strftime("%a")

            if day_name == target_day_of_week:
                year = test_year

        return year

    def __repr__(self):
        return self.instance_attributes_string()

    def __str__(self):
        print(self.instance_attributes_string())

class ApiGameParser(BaseParser):
    """
    Adapts TimeToScore API game JSON to the GameParser shape used by Database.add_game.
    """

    def __init__(self, game_dict):
        self.id = int(game_dict['game_id'])
        self.completed = 1 if game_dict.get('game_status') == 'CLOSED' else 0

        self.parse_success = False
        timezone = ZoneInfo(game_dict.get('timezn') or 'US/Pacific')

        try:
            if game_dict.get('date') and game_dict.get('time'):
                dt = datetime.datetime.strptime(
                    f'{game_dict["date"]} {game_dict["time"]}',
                    '%Y-%m-%d %H:%M:%S',
                )
                self.datetime = dt.replace(tzinfo=timezone)
            elif game_dict.get('gmt_time'):
                dt = datetime.datetime.strptime(
                    game_dict['gmt_time'].split('.')[0],
                    '%Y-%m-%d %H:%M:%S',
                )
                self.datetime = dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(timezone)
            else:
                return
        except Exception:
            write_log('ERROR', f'Failed API synchronization of game {game_dict}')
            return

        self.rink = (game_dict.get('location') or '').strip()
        self.league = (game_dict.get('league_name') or '').strip()
        self.level = (game_dict.get('level_name') or game_dict.get('level_ab') or '').strip()
        self.home_team = (game_dict.get('home_team') or '').strip()
        self.away_team = (game_dict.get('away_team') or '').strip()
        self.type = (game_dict.get('gtype_name') or '').strip()
        self.home_goals = self.parse_goals(game_dict.get('home_goals'))
        self.away_goals = self.parse_goals(game_dict.get('away_goals'))
        self.shootout = 1 if game_dict.get('result_flag') == 'S' else 0
        self.parse_success = bool(self.home_team and self.away_team)

    def parse_goals(self, goals):
        try:
            return int(goals)
        except:
            return 0

class LockerRoomPageParser:
    """
    Parses a Sharks Ice page for locker room assignments for each game.
    """

    # row 0 -> -> column headers, row 3+ -> data
    TABLE_DATA_COLUMN_HEADERS_INDEX = 0
    TABLE_DATA_START_INDEX = 1

    def __init__(self, url, team_soup):
        """
        Initializes the class with the URL and BeautifulSoup object of the Sharks Ice page to be parsed.

        Args:
        url (str): URL of the Sharks Ice page to be parsed.
        team_soup (bs4.BeautifulSoup): BeautifulSoup object representing the content of the Sharks Ice page.
        """
        self.url = url
        self.soup = team_soup

        self.locker_rooms = {}

    def parse(self):
        """
        Finds the important tables in the Sharks Ice page and initiates parsing of each of them.

        Returns:
        bool: Always returns True.
        """
        if not self.soup.body:
            write_log('ERROR', f'Locker room parser found no body at {self.url}')
            return True

        direct_rows = [
            row for row in self.soup.body.find_all('tr')
            if row.find(class_='lr-game-id')
        ]
        if direct_rows:
            self.parse_current_locker_room_rows(direct_rows)
            return True

        tables = self.soup.body.find_all('table')
        write_log('INFO', f'Locker room parser diagnostics tables={len(tables)} lr_game_rows=0 title={self.page_title()}')
        for table in tables:

            self.parse_locker_rooms(table)

        return True

    def page_title(self):
        if not self.soup.title:
            return ''

        return self.cell_contents(self.soup.title)

    def parse_current_locker_room_rows(self, rows):
        for row in rows:
            details = self.table_row_contents(row)
            if len(details) < 9:
                continue

            self.locker_rooms[details[0]] = {
                'Home LR': details[6],
                'Away LR': details[8],
            }

    def cell_contents(self, cell):
        """
        Returns a string with the contents of a table cell.

        Args:
        cell (bs4.Tag): BeautifulSoup tag representing a table cell.

        Returns:
        str: Contents of the table cell, stripped of any whitespace.
        """
        result = cell.get_text()
        result = result.strip()

        return result

    def table_row_contents(self, row):
        """
        Returns an array with the contents of each cell in a table row.

        Args:
        row (bs4.Tag): BeautifulSoup tag representing a table row.

        Returns:
        List[str]: List of strings, each representing the contents of a cell in the row.
        """
        result_array = []

        cell_type = 'td' if row.td else 'th'

        for cell in row.find_all(cell_type):
            result_array.append(self.cell_contents(cell))

        return result_array

    def parse_locker_rooms(self, table):
        """
        Parses the locker room information from the HTML table.
        The locker room information is stored in the dictionary 'self.locker_rooms' with the game ID as the key.
        The game ID maps to a dictionary with keys 'Home LR' and 'Away LR' that contain the corresponding locker room numbers.

        :param table: The BeautifulSoup HTML table element that contains the locker room information.
        :return: None
        """
        rows = table.find_all('tr')
        if not rows:
            return

        column_names = self.table_row_contents(rows[self.TABLE_DATA_COLUMN_HEADERS_INDEX])

        # adjust duplicate column names of "LR" to "Home LR" and "Away LR"
        for i in range(len(column_names)):
            if column_names[i] == 'LR':

                if column_names[i - 1] == 'Aray': # TYPO in sharks ice page
                    column_names[i] = f'Away LR'
                elif column_names[i - 1] == 'Away' or column_names[i - 1] == 'Home':
                    column_names[i] = f'{column_names[i - 1]} LR'
                else:
                    raise Exception(f'Unexpected ordering of games table columns')

        self.games = []
        for row in rows[self.TABLE_DATA_START_INDEX:]:

            details = self.table_row_contents(row)
            if not details or len(details) < len(column_names):
                continue

            lr_assignment = {}
            lr_assignment['Away LR'] = details[column_names.index('Away LR')]
            lr_assignment['Home LR'] = details[column_names.index('Home LR')]

            self.locker_rooms[details[column_names.index('Game')]] = lr_assignment

    def get_locker_rooms_for_game(self, game_id):
        """
        Returns the home and away locker room numbers for a given game ID.

        :param game_id: The ID of the game to get the locker room numbers for.
        :return: A tuple (home_lr, away_lr) containing the home and away locker room numbers, or (None, None) if the game ID is not found in 'self.locker_rooms'.
        """
        game_id = str(game_id)
        if game_id not in self.locker_rooms:
            return None, None

        return self.locker_rooms[game_id]['Home LR'], self.locker_rooms[game_id]['Away LR']

    def get_games_with_locker_rooms(self):
        return self.locker_rooms.keys()
