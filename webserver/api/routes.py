import json
import os
import sys

from flask import Blueprint, current_app, g, make_response, request
import jwt

from webserver.api.game import get_game
from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
from webserver.email import send_game_coming_soon
from webserver.logging import write_log

blueprint = Blueprint('routes', __name__, url_prefix='/api')


@blueprint.route('/sync')
def sync():
    synchronizer = Synchronizer()
    
    if synchronizer.sync():
        return { 'result' : 'success' }
    else:
        return { 'result' : 'faled',
                 'reason' : 'testing' }


@blueprint.route('/test-email')
def test_email():
    game_response = get_game(311307, 211)
    game_dict = json.loads(game_response.data)
    game_dict = game_dict['games'][0]
    print(game_dict, flush=True)

    replies = get_db().game_replies_for_game(game_dict['game_id'], game_dict['user_team_id'])
    user_reply = ''
    confimed_yes = 0
    goalie = ''

    for reply in replies:
        if reply.user_id == g.user.user_id:
            user_reply = reply.response

        if reply.response == 'yes':
            confimed_yes += 1

    email_data = {
        'name': g.user.first_name,
        'user_id': g.user.user_id,
        'game_id': game_dict['game_id'],
        'user_team_id': game_dict['user_team_id'],
        'team': game_dict['user_team'],
        'scheduled_how_soon': game_dict['scheduled_how_soon'],
        'scheduled_at': game_dict['scheduled_at'],
        'rink': game_dict['rink'],
        'vs': game_dict['vs'],
        'reply': user_reply,
        'confirmed_players': f'{confimed_yes}',
        'goalie': '?'
    }
    send_game_coming_soon(email_data)
    return { 'result' : 'success' }
