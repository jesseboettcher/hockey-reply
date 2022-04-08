from datetime import datetime
import os
import sys

from flask import Blueprint, current_app, g, make_response, request

from webserver.database.alchemy_models import User, Team, TeamPlayer
from webserver.database.hockey_db import get_db, get_current_user
from webserver.logging import write_log
from webserver.api.auth import check_login

'''
APIs for managing team membership
'''
blueprint = Blueprint('team', __name__, url_prefix='/api')

def validate_role(role):
    if role != 'captain' and role != 'full' and role != 'half' and role != 'sub':
        return False

    return True

def find_player(team, user_id):
    for player in team.players:
        if int(player.user_id) == int(user_id):
            return player

    return None

@blueprint.route('/team/', methods=['GET'])
@blueprint.route('/team/<team_id>', methods=['GET'])
def get_teams(team_id=None):

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    teams = db.get_teams()

    result = { 'teams': [] }

    if request.args.get('all'):
        for team in teams:
            team_dict = {
                'team_id': team.team_id,
                'name': team.name,
                'player_count': len(team.players)
            }
            result['teams'].append(team_dict)
    elif team_id is None:
        for player_team in get_current_user().teams:
            team = db.get_team_by_id(player_team.team_id)
            team_dict = {
                'team_id': team.team_id,
                'name': team.name,
                'player_count': len(team.players)
            }
            result['teams'].append(team_dict)
    else:
        team_id = int(team_id)
        team = db.get_team_by_id(team_id)

        if not team:
            write_log('ERROR', f'/api/team/<team_id>: team {team_id} not found')
            return {'result': 'error'}, 400

        result = { 'teams': [] }
        team_dict = {
            'team_id': team.team_id,
            'name': team.name,
            'player_count': len(team.players)
        }
        result['teams'].append(team_dict)

    return make_response(result)


@blueprint.route('/team-players/<team_name_or_id>', methods=['GET'])
def get_team_players(team_name_or_id=None):

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    team_id = None
    try:
        team_id = int(team_name_or_id)
    except Exception as e:
        # must be a name
        team = db.get_team(team_name_or_id.replace('-', ' '))
        if team:
            team_id = team.team_id

    team = db.get_team_by_id(team_id)

    if not team:
        write_log('ERROR', f'/api/team/<team_id>: team {team_name_or_id} not found')
        return {'result': 'error'}, 400

    team_player = db.get_team_player(team_id, get_current_user().user_id)
    if not team_player:
        result = {}
        result['result'] = 'USER_NOT_ON_TEAM'
        result['team_id'] = team_id
        result['team_name'] = team.name
        return result, 200

    result = { 'players': [] }

    for player in team.players:

        requesting_player = db.get_user_by_id(player.user_id)
        player_name = requesting_player.first_name
        if requesting_player.last_name:
            player_name += f' {requesting_player.last_name}'

        request_dict = {
            'team' : team.name,
            'team_id': team.team_id,
            'user_id': player.user_id,
            'name': player_name,
            'email': requesting_player.email,
            'role': player.role,
            'requested_at': player.joined_at,
            'player_count': len(team.players)
        }
        result['players'].append(request_dict)

    result['user'] = {}
    result['user']['user_id'] = get_current_user().user_id
    result['user']['role'] = team_player.role
    result['team_id'] = team_id
    result['team_name'] = team.name

    return make_response(result)


@blueprint.route('/join-requests/', methods=['GET'])
@blueprint.route('/join-requests/<team_id>', methods=['GET'])
def get_join_requests(team_id=None):

    if not check_login():
        return { 'result' : 'needs login' }, 400

    team_id = int(team_id)

    db = get_db()

    result = { 'join_requests': [] }

    if get_current_user().admin and team_id is None:
        for player in db.get_team_players():
            if not player.pending_status:
                continue

            requesting_player = db.get_user_by_id(player.user_id)
            player_name = requesting_player.first_name
            if requesting_player.last_name:
                player_name += f' {requesting_player.last_name}'

            team = db.get_team_by_id(player.team_id)

            request_dict = {
                'team' : team.name,
                'team_id': team.team_id,
                'user_id': player.user_id,
                'name': player_name,
                'name': f'{requesting_player.first_name} {requesting_player.last_name}',
                'email': requesting_player.email,
                'requested_at': player.joined_at,
                'player_count': len(team.players)
            }
            result['join_requests'].append(request_dict)
    else:
        team = db.get_team_by_id(team_id)

        if not team:
            write_log('ERROR', f'api/join-team: team {team_id} not found')
            return {'result': 'error'}, 400

        for player in team.players:
            if not player.pending_status:
                continue

            requesting_player = db.get_user_by_id(player.user_id)
            player_name = requesting_player.first_name
            if requesting_player.last_name:
                player_name += f' {requesting_player.last_name}'

            request_dict = {
                'team' : team.name,
                'team_id': team.team_id,
                'user_id': player.user_id,
                'name': player_name,
                'email': requesting_player.email,
                'requested_at': player.joined_at,
                'player_count': len(team.players)
            }
            result['join_requests'].append(request_dict)

    return make_response(result)


@blueprint.route('/join-team', methods=['POST'])
def join_team():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    # check for required fields
    if ('team_id' not in request.json and 'team_name' not in request.json) or\
       'user_id' not in request.json:
        write_log('ERROR', f'api/join-team: missing request fields')
        return {'result': 'error'}, 400

    team = None
    if 'team_id' in request.json:
        team = db.get_team_by_id(request.json['team_id'])
    elif 'team_name' in request.json:
        team = db.get_team(request.json['team_name'])

    if not team:
        if 'team_id' in request.json:
            write_log('ERROR', f'api/join-team: team {request.json["team_id"]} not found')
        elif 'team_name' in request.json:
            write_log('ERROR', f'api/join-team: team {request.json["team_name"]} not found')
        return {'result': 'error'}, 400

    user_to_add = db.get_user_by_id(request.json['user_id'])

    for player in team.players:

        if player.user_id == user_to_add.user_id:
            write_log('ERROR', f'api/join-team: player already on team')
            return {'result': 'error'}, 400

    # the first player to join a team is the captain
    player_role = ''
    if len(team.players) == 0:
        player_role = 'captain'

    join_team_as_player = TeamPlayer(
                                     role=player_role,
                                     pending_status=False if player_role == 'captain' else True,
                                     joined_at=datetime.now()
                                    )
    join_team_as_player.player = user_to_add
    team.players.append(join_team_as_player)
    db.commit_changes()

    write_log('INFO', f'api/join-team: {request.json["user_id"]} requested {team.name}')
    return make_response({ 'result' : 'success' })


@blueprint.route('/player-role', methods=['POST'])
def accept_join():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    # check for required fields
    if 'team_id' not in request.json or \
       'user_id' not in request.json:

        write_log('ERROR', f'api/player-role: missing request fields')
        return {'result': 'error'}, 400

    team = db.get_team_by_id(request.json['team_id'])

    if not team:
        write_log('ERROR', f'api/join-team: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    # get current user and check for authorization to accept join requests
    logged_in_user_player_obj = find_player(team, get_current_user().user_id)

    if (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain') and not get_current_user().admin:
        write_log('ERROR', f'api/player-role: logged in user does not have permissions to modify player roles')
        return {'result': 'error'}, 400

    # find the player, accept the request, and apply any role changes
    for player in team.players:
    
        if player.user_id == request.json['user_id']:

            if player.pending_status:
                player.pending_status = False
                player.joined_at = datetime.now()

            if 'role' in request.json and validate_role(request.json['role']):
                player.role = request.json['role']

            db.commit_changes()

            write_log('INFO', f'api/player-role: {player.player.email} updated to {player.role} on {team.name} by {get_current_user().email}')
            return make_response({ 'result' : 'success' })

    write_log('ERROR', f'api/player-role: player not found in team')
    return {'result': 'error'}, 400


@blueprint.route('/remove-player', methods=['POST'])
def remove_player():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    # check for required fields
    if 'team_id' not in request.json or \
       'user_id' not in request.json:

        write_log('ERROR', f'api/remove-player: missing request fields')
        return {'result': 'error'}, 400

    team_id = int(request.json['team_id'])
    user_id = int(request.json['user_id'])

    team = db.get_team_by_id(team_id)

    if not team:
        write_log('ERROR', f'api/remove-player: team {team_id} not found')
        return {'result': 'error'}, 400

    player_to_remove = find_player(team, user_id)

    if not player_to_remove:
        write_log('ERROR', f'api/remove-player: player is not on the team')
        return {'result': 'error'}, 400


    logged_in_user_player_obj = find_player(team, get_current_user().user_id)

    if (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain') and not get_current_user().admin:
        write_log('ERROR', f'api/remove-player: logged in user does not have permissions to remove players')
        return {'result': 'error'}, 400

    email = player_to_remove.player.email
    who = get_current_user().email

    team.players.remove(player_to_remove)
    db.commit_changes()

    write_log('INFO', f'api/remove-player: {email} removed from {team.name} by {who}')
    return make_response({ 'result' : 'success' })
