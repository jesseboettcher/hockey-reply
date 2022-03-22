from datetime import datetime
import os
import sys

from flask import current_app, g, make_response, request

from webserver import app
from webserver.database.alchemy_models import User, Team
from webserver.database.hockey_db import get_db
from webserver.logging import write_log


'''
APIs for managing updates to games
'''

@app.route('/api/games/<team_id>', methods=['GET'])
def get_games(team_id):
    '''
    Returns all games for the specified team. Includes flag for whether the game was completed.
    '''
    return make_response({'result': 'success'})


@app.route('/api/game/<game_id>', methods=['GET'])
def get_game(team_id):
    '''
    Returns the details for the specified game: game date/time, rink, home/away, vs, player replies
    '''
    return make_response({'result': 'success'})


@app.route('/api/game/reply', methods=['GET', 'POST'])
def game_reply(team_id):
    '''
    POST with game_id, response (yes|no|maybe), message
    GET for replies from email links with url params containing the same fields
    '''
    return make_response({'result': 'success'})