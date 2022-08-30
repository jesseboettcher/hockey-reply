'''
routes

Miscellaneous routes for development and testing.
'''
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
    '''
    Initiates a synchronization of the database with the Sharks Ice website. Just used for
    testing, so will return an error if accessed on production.
    '''
    if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
        return { 'result' : 'not allowed' }
    
    synchronizer = Synchronizer()
    synchronizer.sync()

    return { 'result' : 'success' }

@blueprint.route('/send-email-reminder/<game_id>')
def test_email(game_id):
    '''
    Test route for validating email changes. If using this make sure to add a whitelist
    in email.send_email to guard against spamming real users with tests.
    '''
    game_id = int(game_id)

    if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
        return { 'result' : 'not allowed' }

    game = get_db().get_game_by_id(game_id)
    send_game_coming_soon(get_db(), game)
    return { 'result' : 'success' }
