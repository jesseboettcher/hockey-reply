from datetime import datetime
import os
import sys

from flask import current_app, g, make_response, request

from webserver import app
from webserver.database.alchemy_models import User, Team, TeamPlayer
from webserver.database.hockey_db import get_db
from webserver.logging import write_log
from webserver.api.auth import check_login

'''
APIs for managing team membership
'''
def validate_role(role):
    if role != 'captain' and role != 'full' and role != 'half' and role != 'sub':
        return False

    return True

def find_player(team, user_id):
    for player in team.players:
        if player.user_id == user_id:
            return player

    return None

@app.route('/api/team/', methods=['GET'])
@app.route('/api/team/<team_id>', methods=['GET'])
def get_teams(team_id=None):
    print('api/team/{team_id}', flush=True)
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    teams = db.get_teams()

    result = { 'teams': [] }

    if request.args.get('all') and g.user.admin:
        for team in teams:
            team_dict = {
                'team_id': team.team_id,
                'name': team.name,
                'player_count': len(team.players)
            }
            result['teams'].append(team_dict)
    elif team_id is None:
        for player_team in g.user.teams:
            team = db.get_team_by_id(player_team.team_id)
            team_dict = {
                'team_id': team.team_id,
                'name': team.name,
                'player_count': len(team.players)
            }
            result['teams'].append(team_dict)
    else:
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


@app.route('/api/join-requests/', methods=['GET'])
@app.route('/api/join-requests/<team_id>', methods=['GET'])
def get_join_requests(team_id=None):

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    result = { 'join_requests': [] }

    if g.user.admin and team_id is None:
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


@app.route('/api/join-team', methods=['POST'])
def join_team():

    print(request.json, flush=True)

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    # check for required fields
    if 'team_id' not in request.json:
        write_log('ERROR', f'api/join-team: missing request fields')
        return {'result': 'error'}, 400

    team = db.get_team_by_id(request.json['team_id'])

    if not team:
        write_log('ERROR', f'api/join-team: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    user_to_add = g.user
    if request.json['user_id']: # TODO if admin
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

    write_log('INFO', f'api/join-team: {g.user.email} requested {team.name}')
    return make_response({ 'result' : 'success' })


@app.route('/api/accept-join', methods=['POST'])
def accept_join():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    print(request.json, flush=True)

    # check for required fields
    if 'team_id' not in request.json or \
       'user_id' not in request.json:

        write_log('ERROR', f'api/accept-join: missing request fields')
        return {'result': 'error'}, 400

    team = db.get_team_by_id(request.json['team_id'])

    if not team:
        write_log('ERROR', f'api/join-team: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    # get current user and check for authorization to accept join requests
    logged_in_user_player_obj = find_player(team, g.user.user_id)
    requesting_user = find_player(team, request.json['user_id'])

    if not requesting_user:
        write_log('ERROR', f'api/accept-join: player request to join team not found')
        return {'result': 'error'}, 400

    if (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain') and not g.user.admin:
        write_log('ERROR', f'api/accept-join: logged in user does not have permissions to accept join requests')
        return {'result': 'error'}, 400

    # find the player, accept the request, and apply any role changes
    for player in team.players:
    
        if player.user_id == g.user.user_id and player.pending_status:
            player.pending_status = False
            player.joined_at = datetime.now()

            if 'role' in request.json and validate_role(request.json['role']):
                player.role = request.json['role']

            db.commit_changes()

            write_log('INFO', f'api/accept-join: {player.player.email} accepted to {team.name} by {g.user.email}')
            return make_response({ 'result' : 'success' })

    write_log('ERROR', f'api/accept-join: player request to join team not found')
    return {'result': 'error'}, 400


@app.route('/api/remove-player', methods=['POST'])
def remove_player():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    print(request.json, flush=True)

    # check for required fields
    if 'team_id' not in request.json or \
       'user_id' not in request.json:

        write_log('ERROR', f'api/accept-join: missing request fields')
        return {'result': 'error'}, 400

    team = db.get_team_by_id(request.json['team_id'])

    if not team:
        write_log('ERROR', f'api/remove-player: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    player_to_remove = find_player(team, request.json['user_id'])

    if not player_to_remove:
        write_log('ERROR', f'api/remove-player: player is not on the team')
        return {'result': 'error'}, 400

    if not g.user.admin:
        write_log('ERROR', f'api/remove-player: logged in user does not have permissions to accept join requests')
        return {'result': 'error'}, 400

    team.players.remove(player_to_remove)
    db.commit_changes()

    write_log('INFO', f'api/remove-player: {player_to_remove.player.email} removed from {team.name} by {g.user.email}')
    return make_response({ 'result' : 'success' })
