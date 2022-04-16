'''
game

All the webserver APIs for querying games and player replies.
'''
import datetime
import os
import sys
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, g, make_response, request

from webserver.api.auth import check_login
from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db, get_current_user
from webserver.logging import write_log

'''
APIs for managing updates to user profiles
'''
blueprint = Blueprint('profile', __name__, url_prefix='/api')


@blueprint.route('/profile', methods=['GET', 'POST'])
def update_player_number():
    ''' Update the jersey number of a player on the team
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    user = get_current_user()

    if request.method == 'POST':

        # check for required fields
        if 'user_id' not in request.json:
            write_log('ERROR', f'api/profile: missing request fields to make updates')
            return {'result': 'error'}, 400

        if request.json['user_id'] != user.user_id:
            write_log('ERROR', f'api/profile: profiles can only be updated by owning user')
            return {'result': 'error'}, 400

        if 'first_name' in request.json:
            user.first_name = request.json['first_name']
        if 'last_name' in request.json:
            user.last_name = request.json['last_name']
        if 'phone_number' in request.json:
            user.phone_number = request.json['phone_number']
        if 'usa_hockey_number' in request.json:
            user.usa_hockey_number = request.json['usa_hockey_number']

        db.commit_changes()
        write_log('INFO', f'api/profile: profile updated for {user.user_id}')
        return {'result': 'success'}, 200

    response_dict = {}
    response_dict['user_id'] = user.user_id
    response_dict['first_name'] = user.first_name
    response_dict['email'] = user.email
    response_dict['last_name'] = user.last_name
    response_dict['phone_number'] = user.phone_number
    response_dict['usa_hockey_number'] = user.usa_hockey_number

    return make_response(response_dict)
