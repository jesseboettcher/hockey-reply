from datetime import datetime
import os
import sys

from flask import Blueprint, current_app, g, make_response, request

from webserver.database.alchemy_models import User, Team
from webserver.database.hockey_db import get_db
from webserver.logging import write_log
from webserver.api.auth import check_login


'''
APIs for managing updates to games
'''
blueprint = Blueprint('game', __name__, url_prefix='/api')

@blueprint.route('/games/<team_id>', methods=['GET'])
def get_games(team_id):
    '''
    Returns all games for the specified team. Includes flag for whether the game was completed.
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    games = db.get_games_for_team(team_id)

    result = { 'games': [] }
    print(len(games), flush=True)
    print(team_id, flush=True)

    for game in games:

        print(game.game_id, flush=True)
        game_dict = {
            'game_id' : game.game_id,
            'scheduled_at': game.scheduled_at,
            'completed': game.completed,
            'rink': game.rink,
            'level': game.level,
            'home_team_id': game.home_team_id,
            'away_team_id': game.away_team_id,
            'home_goals': game.home_goals,
            'away_goals': game.away_goals,
            'game_type': game.game_type
        }
        result['games'].append(game_dict)

    return make_response(result)


@blueprint.route('/game/<game_id>', methods=['GET'])
def get_game(team_id):
    '''
    Returns the details for the specified game: game date/time, rink, home/away, vs, player replies
    '''
    return make_response({'result': 'success'})


@blueprint.route('/game/reply', methods=['GET', 'POST'])
def game_reply(team_id):
    '''
    POST with game_id, response (yes|no|maybe), message
    GET for replies from email links with url params containing the same fields
    '''
    return make_response({'result': 'success'})