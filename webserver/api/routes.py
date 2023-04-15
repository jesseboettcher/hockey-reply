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
from webserver.assistant import Assistant
from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
from webserver.email import send_game_coming_soon
from webserver.sms import SMS
from webserver.logging import write_log

blueprint = Blueprint('routes', __name__, url_prefix='/api')

@blueprint.route('/sms', methods=['POST'])
def receive_sms():
    '''
    Receives an SMS message from Twilio and passes it to the assistant.
    '''
    ai = Assistant.get_instance()
    ai.receive_message(request.form.get("From"),request.form.get("Body"))

    return "", 200

@blueprint.route('/test-sms/<msg>', methods=['GET'])
def test_sms(msg):
    '''
    Tests sending an SMS message to the assistant.
    '''
    sms_client = SMS()
    sms_client.send(['+14082197030'], msg)
    return "", 200

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


@blueprint.route('/sync-locker-rooms')
def sync_locker_rooms():
    '''
    Initiates a synchronization of the database with the Sharks Ice website. Just used for
    testing, so will return an error if accessed on production.
    '''
    if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
        return { 'result' : 'not allowed' }

    synchronizer = Synchronizer()
    synchronizer.locker_room_assignment_check()

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

@blueprint.route('/test-assistant')
def test_assistant():
    """
    Test route for validating assistant changes.
    """
    placeholder_game_id = 382236
    placeholder_team_id = 247

    if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
        return { 'result' : 'not allowed' }

    ai = Assistant.get_instance()

    # fake numbers
    ai.receive_message('408-7777777','hey there')
    ai.receive_message('408-7777777','love that the nhl playoffs are happening. so much great hockey to watch')
    ai.receive_message('408-7777777','hey we need a goalie for our next game')
    ai.receive_message('408-7777777','yes, thanks')
    ai.receive_message('4081111111','who are you?')
    ai.receive_message('4081111111','oh, i see')
    ai.receive_message('4081111111','nope, i am skiing this weekend')
    ai.receive_message('4082222222','definitely count me in!')

    return { 'result' : 'success' }
