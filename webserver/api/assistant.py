'''
assistant

This module contains the API endpoints for the assistant.
'''
from flask import Blueprint, request

from webserver.assistant import Assistant
from webserver.api.auth import check_login
from webserver.database.hockey_db import get_db, get_current_user
from webserver.logging import write_log

'''
APIs for interacting with the assistant
'''
blueprint = Blueprint('assistant', __name__, url_prefix='/api')

@blueprint.route('/find-goalie', methods=['POST'])
def find_goalie():
    """
    Find a goalie for a game
    """
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    user = get_current_user()

    # check for required fields
    if 'game_id' not in request.json or 'team_id' not in request.json:
        write_log('ERROR', f'api/find-goalie: missing request fields')
        return {'result': 'error'}, 400

    game_id = int(request.json['game_id'])
    team_id = int(request.json['team_id'])

    team_player = db.get_team_player(team_id, user.user_id)
    if not team_player or team_player.role != 'captain':
        result = {}
        result['result'] = "USER_NOT_CAPTAIN"
        result['team_id'] = team_id
        write_log('ERROR', f'api/find-goalie: unauthorized user attempted to initiate a goalie search for team {team_id}, user {user.user_id}')
        return result, 200

    assistant = Assistant.get_instance()
    success, msg = assistant.initiate_goalie_search(team_id, game_id)
    if not success:
        write_log('ERROR', f'api/find-goalie: error initiating goalie search for game {game_id} and team {team_id}: {msg}')
        return {'result': 'error', 'message': msg}, 400

    searches = assistant.describe_goalie_searches_for_team(team_id)

    write_log('INFO', f'api/find-goalie: goalie search initiated for game {game_id} and team {team_id}')
    return searches, 200

@blueprint.route('/goalie-searches/<team_id_input>', methods=['GET'])
def goalie_searches(team_id_input):
    """
    Find a goalie for a game
    """
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    user = get_current_user()

    team_id = int(team_id_input)

    team_player = db.get_team_player(team_id, user.user_id)
    if not team_player or team_player.role != 'captain':
        result = {}
        result['result'] = "USER_NOT_CAPTAIN"
        result['team_id'] = team_id
        return result, 200

    assistant = Assistant.get_instance()
    searches = assistant.describe_goalie_searches_for_team(team_id)

    write_log('INFO', f'api/goalie-searches: returned goalie searches for team {team_id}')
    return searches, 200
