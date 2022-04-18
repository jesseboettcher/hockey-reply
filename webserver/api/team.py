'''
team

All the webserver APIs for querying teams, their players, and making changes to team membership.
'''
from datetime import datetime
import os
import sys

from flask import Blueprint, current_app, g, make_response, request

from webserver.database.alchemy_models import User, Team, TeamPlayer
from webserver.database.hockey_db import get_db, get_current_user
from webserver.email import send_player_join_request, send_team_role_change, send_removed_from_team
from webserver.logging import write_log
from webserver.api.auth import check_login

'''
APIs for managing team membership
'''
blueprint = Blueprint('team', __name__, url_prefix='/api')

''' Errors that are parsed and handled by the frontend in the content of the 'result' field
'''
USER_NOT_ON_TEAM_ERROR = 'USER_NOT_ON_TEAM'

def validate_role(role):
    ''' Make sure that only known role strings make it into the database
    '''
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
    ''' Returns an array of teams with [team_id, name, player_count]. If no team_id is specific
        will return only the logged in users teams.
    '''
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

            if team.external_id != 0:
                team_dict['calendar_url'] = f'https://stats.sharksice.timetoscore.com/team-cal.php?team={team.external_id}&tlev=0&tseq=0&format=iCal'

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
        if team.external_id != 0:
            team_dict['calendar_url'] = f'https://stats.sharksice.timetoscore.com/team-cal.php?team={team.external_id}&tlev=0&tseq=0&format=iCal'

        result['teams'].append(team_dict)

    return make_response(result)


@blueprint.route('/team-players/<team_name_or_id>', methods=['GET'])
def get_team_players(team_name_or_id=None):
    ''' Returns a list of players who are part of the provided team. Used for the roster page.
        Results:
            [] players
            {} user details for currently logged in user
               name of the team
    '''
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
        result['result'] = USER_NOT_ON_TEAM_ERROR
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
            'phone_number': requesting_player.phone_number,
            'usa_hockey_number': requesting_player.usa_hockey_number,
            'role': player.role,
            'number': player.number if player.number else '',
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


@blueprint.route('/join-team', methods=['POST'])
def join_team():
    ''' API for users to request to join a team. The first user to join a team automatically
        becomes the captain. Subsequent users will not get a role until the existing captain(s)
        assign one (or remove them).
    '''
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
    if player_role != 'captain':
        send_player_join_request(join_team_as_player, team)

    return make_response({ 'result' : 'success' })


@blueprint.route('/player-role', methods=['POST'])
def update_player_role():
    ''' Update the role of a player on the team. Only players with the role captain are able
        to make this change.
    '''
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
        write_log('ERROR', f'api/player-role: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    # get current user and check for authorization to accept join requests
    logged_in_user_player_obj = find_player(team, get_current_user().user_id)

    if (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain') and not get_current_user().admin:
        write_log('ERROR', f'api/player-role: logged in user does not have permissions to modify player roles')
        return {'result': 'error'}, 400

    captain_count = 0
    for player in team.players:
        if player.role == 'captain':
            captain_count += 1

    # find the player, accept the request, and apply any role changes
    for player in team.players:
    
        if player.user_id == request.json['user_id']:

            if player.pending_status:
                player.pending_status = False
                player.joined_at = datetime.now()

            if captain_count == 1 and player.role == 'captain' and request.json['role'] != 'captain':
                write_log('WARNING', f'api/player-role: teams must have at least one captain')
                return {'result': 'error: teams must have at least one captain'}, 400

            if 'role' in request.json and validate_role(request.json['role']):
                player.role = request.json['role']

            db.commit_changes()

            write_log('INFO', f'api/player-role: {player.player.email} updated to {player.role} on {team.name} by {get_current_user().email}')
            send_team_role_change(team, player, get_current_user())

            return make_response({ 'result' : 'success' })

    write_log('ERROR', f'api/player-role: player not found in team')
    return {'result': 'error'}, 400


@blueprint.route('/player-number', methods=['POST'])
def update_player_number():
    ''' Update the jersey number of a player on the team
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    # check for required fields
    if 'team_id' not in request.json or \
       'user_id' not in request.json or \
       'number' not in request.json:

        write_log('ERROR', f'api/player-number: missing request fields')
        return {'result': 'error'}, 400

    team = db.get_team_by_id(request.json['team_id'])

    if not team:
        write_log('ERROR', f'api/player-number: team {request.json["team_id"]} not found')
        return {'result': 'error'}, 400

    # get current user and check for authorization to accept join requests
    logged_in_user_player_obj = find_player(team, get_current_user().user_id)
    player_obj_to_update = find_player(team, request.json['user_id'])

    # If the player to update is not the logged in user
    # And the logged in user is not a captain
    if (not player_obj_to_update or player_obj_to_update.player.user_id != get_current_user().user_id) and\
       (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain'):
        write_log('ERROR', f'api/player-role: logged in user does not have permissions to modify player roles')
        return {'result': 'error'}, 400

    # find the player, make the change
    for player in team.players:

        if player.player.user_id == int(request.json['user_id']):

            player.number = request.json['number'];
            db.commit_changes()

            write_log('INFO', f'api/player-number: {player.player.email} updated to {player.number} on {team.name} by {get_current_user().email}')
            return make_response({ 'result' : 'success' })

    write_log('ERROR', f'api/player-number: player not found in team')
    return {'result': 'error'}, 400

@blueprint.route('/remove-player', methods=['POST'])
def remove_player():
    ''' API to remove a player from a team. Only captains may remove other players from the team.
        Users may remove themselves though (which is used for cancel-join-team UI).
    '''
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

    if (not logged_in_user_player_obj or logged_in_user_player_obj.role != 'captain') and\
        player_to_remove.player.user_id != get_current_user().user_id and\
        not get_current_user().admin:
        write_log('ERROR', f'api/remove-player: logged in user does not have permissions to remove players')
        return {'result': 'error'}, 400

    captain_count = 0
    for player in team.players:
        if player.role == 'captain':
            captain_count += 1

    if captain_count == 1 and player_to_remove.role == 'captain' and len(team.players) > 1:
        write_log('WARNING', f'api/player-role: teams must have at least one captain')
        return {'result': 'error: teams must have at least one captain'}, 400

    removed_user = player_to_remove.player
    email = removed_user.email
    who = get_current_user().email

    team.players.remove(player_to_remove)
    db.commit_changes()

    write_log('INFO', f'api/remove-player: {email} removed from {team.name} by {who}')
    if removed_user.user_id != get_current_user().user_id:
        send_removed_from_team(team, removed_user, get_current_user())

    return make_response({ 'result' : 'success' })
