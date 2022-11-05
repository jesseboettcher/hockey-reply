'''
game

All the webserver APIs for querying games and player replies.
'''
from datetime import datetime, timezone
import os
import sys
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, g, make_response, request
import humanize

from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db, get_current_user
from webserver.email import send_reply_was_changed
from webserver.logging import write_log
from webserver.api.auth import check_login
from webserver.utils import timeuntil


'''
APIs for managing updates to games
'''
blueprint = Blueprint('game', __name__, url_prefix='/api')


def is_logged_in_user_in_team(team_id, and_has_been_accepted):
    if current_app.config['TESTING']:
        return True

    user_in_team = False
    for team in get_current_user().teams:
        if team.team_id == team_id:

            if and_has_been_accepted:
                player = get_db().get_team_player(team_id, get_current_user().user_id)
                if not player or player.role == '':
                    # membership is pending
                    return False

            return True

    return False

@blueprint.route('/games/', methods=['GET'])
@blueprint.route('/games/<team_id>', methods=['GET'])
def get_games(team_id = None):
    '''
    Returns all games for the specified team. Includes flag for whether the game was completed.
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    # Structure of response data
    result = { 'games': [] }

    db = get_db()
    upcomingOnly = 'upcomingOnly' in request.args

    teams = []
    if team_id is not None:
        team = db.get_team_by_id(int(team_id))

        if not team:
            write_log('ERROR', f'api/games: team {team_id} not found')
            return {'result': 'error'}, 400

        teams.append(team)
    else:
        for team in get_current_user().teams:
            teams.append(team)

    for team in teams:

        games = db.get_games_for_team(team.team_id)

        for game in games:

            if upcomingOnly and (game.completed == 1 or game.scheduled_at < datetime.now(timezone.utc)):
                continue

            home_team = db.get_team_by_id(game.home_team_id)
            away_team = db.get_team_by_id(game.away_team_id)

            if home_team is None or away_team is None:
                write_log('ERROR', f'/api/game/<game>: Team for game {game.game_id} is not found')
                return {'result': 'error'}, 400

            if game.home_team_id != team.team_id and game.away_team_id != team.team_id:
                write_log('ERROR', f'/api/game/<game>: Team ({team.team_id}) is not in game {game.game_id}')
                return {'result': 'error'}, 400

            user_is_home = False
            if is_logged_in_user_in_team(game.home_team_id, False):
                user_is_home = True

            user_team_id = game.away_team_id if not user_is_home else game.home_team_id,

            user_reply = ''
            replies = db.game_replies_for_game(game.game_id, user_team_id)

            # Send user role to the front end for the case where the user has not been accepted
            # to the team yet. In that case, it will hide the reply box.
            user_role = ''
            user_team = db.get_team_by_id(user_team_id)
            for player in user_team.players:
                if player.user_id == get_current_user().user_id:
                    user_role = player.role

            for reply in replies:
                if reply.user_id == get_current_user().user_id:
                    user_reply = reply.response
                    break

            pacific = ZoneInfo('US/Pacific')
            game_dict = {
                'game_id' : game.game_id,
                'scheduled_at_dt': game.scheduled_at,
                'scheduled_at': game.scheduled_at.astimezone(pacific).strftime("%a, %b %d @ %I:%M %p"),
                'scheduled_how_soon': timeuntil(datetime.now(timezone.utc).astimezone(pacific), game.scheduled_at.astimezone(pacific)).replace(' ', ' '),
                'completed': game.completed,
                'rink': game.rink,
                'level': game.level,
                'home_team_id': game.home_team_id,
                'away_team_id': game.away_team_id,
                'user_team': home_team.name if user_is_home else away_team.name,
                'vs': home_team.name if not user_is_home else away_team.name,
                'user_team_id': user_team_id,
                'home_goals': game.home_goals,
                'away_goals': game.away_goals,
                'game_type': game.game_type,
                'user_reply': user_reply,
                'user_role': user_role
            }
            result['games'].append(game_dict)
            result['games'] = sorted(result['games'], key=lambda game: game['scheduled_at_dt'])

    return make_response(result)


@blueprint.route('/game/<game_id>/for-team/<team_id>', methods=['GET'])
def get_game(game_id, team_id):
    '''
    Returns the details for the specified game: game date/time, rink, home/away, vs
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    team_id = int(team_id)
    game_id = int(game_id)

    db = get_db()
    game = db.get_game_by_id(game_id)

    if not game:
        write_log('ERROR', f'/api/game/<game>: game {game_id} not found')
        return {'result': 'error'}, 400

    home_team = db.get_team_by_id(game.home_team_id)
    away_team = db.get_team_by_id(game.away_team_id)

    if home_team is None or away_team is None:
        write_log('ERROR', f'/api/game/<game>: Team for game {game_id} is not found')
        return {'result': 'error'}, 400

    if game.home_team_id != team_id and game.away_team_id != team_id:
        write_log('ERROR', f'/api/game/<game>: Team ({team_id}) is not in game {game_id}')
        return {'result': 'error'}, 400

    user_role = None
    player = get_db().get_team_player(team_id, get_current_user().user_id)
    if player:
        user_role = player.role

    user_reply = ''
    if user_role != '':
        replies = db.game_replies_for_game(game_id, team_id)

        for reply in replies:
            if reply.user_id == get_current_user().user_id:
                user_reply = reply.response
                break

    result = { 'games': [] }

    pacific = ZoneInfo('US/Pacific')
    game_dict = {
        'game_id' : game.game_id,
        'scheduled_at': game.scheduled_at.astimezone(pacific).strftime("%a, %b %d @ %I:%M %p"),
        'scheduled_how_soon': timeuntil(datetime.now(timezone.utc).astimezone(pacific), game.scheduled_at.astimezone(pacific)).replace(' ', ' '),
        'completed': game.completed,
        'rink': game.rink,
        'level': game.level,
        'home_team_id': game.home_team_id,
        'home_team_name': home_team.name,
        'away_team_id': game.away_team_id,
        'away_team_name': away_team.name,
        'user_team': home_team.name if game.away_team_id != team_id else away_team.name,
        'vs': home_team.name if game.away_team_id == team_id else away_team.name,
        'user_team_id': game.away_team_id if game.away_team_id == team_id else game.home_team_id,
        'home_goals': game.home_goals,
        'away_goals': game.away_goals,
        'game_type': game.game_type,
        'is_user_membership_pending': True if user_role == '' else False,
        'is_user_on_team': is_logged_in_user_in_team(team_id, False),
        'user_reply': user_reply
    }
    result['games'].append(game_dict)

    return make_response(result)

@blueprint.route('/game/reply/<game_id>/for-team/<team_id>', methods=['POST', 'GET'])
def game_reply(game_id, team_id):
    '''
    POST with game_id, response (yes|no|maybe), message
    GET dictionary with list of 'replies', list of 'no_response' for the game, and current 'user' dictionary
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    team_id = int(team_id)
    game_id = int(game_id)

    db = get_db()

    # user_id < 0 is used to represent one-time subs
    def is_anonymous_sub(check_user_id):
        return check_user_id < 0

    if request.method == 'GET':

        if not is_logged_in_user_in_team(team_id, True):
            write_log('ERROR', f'/api/game/reply: {get_current_user().email} does not have access to replies for game {game_id} and {team_id}')
            return {'result': 'error'}, 401

        # Structure of response data
        result = {}
        result['replies'] = []
        result['no_response'] = []
        result['user'] = {}

        replies = db.game_replies_for_game(game_id, team_id)
        replies_dict = {}

        # Collect the replies
        for reply in replies:
            reply_player = db.get_team_player(team_id, reply.user_id)

            if reply_player is None and not is_anonymous_sub(reply.user_id):
                # player was removed from the team
                continue

            player_name = 'Anonymous Sub'
            if reply_player:
                player_name = f'{reply_player.player.first_name} {reply_player.player.last_name} ({reply_player.role})'

            if reply.response == None:
                # this user has a message, but no reponse. Put them in the no_response dictionary
                continue

            reply_dict = {
                'reply_id': reply.reply_id,
                'game_id': reply.game_id,
                'user_id': reply.user_id,
                'name': player_name,
                'response': reply.response,
                'message': reply.message,
                'is_goalie': reply.is_goalie
            }
            replies_dict[reply.user_id] = reply_dict

        result['replies'] = list(replies_dict.values())

        # Collect the players who have not yet responded
        team = db.get_team_by_id(team_id)
        for player in team.players:
            if player.user_id not in replies_dict and player.role != '':
                reply_dict = {
                    'reply_id': 0,
                    'user_id': player.user_id,
                    'name': f'{player.player.first_name} {player.player.last_name} ({player.role})'
                }
                result['no_response'].append(reply_dict)

        # Add the logged in user information
        if not current_app.config['TESTING']:
            team_player = db.get_team_player(team_id, get_current_user().user_id)
            result['user'] = {}
            result['user']['user_id'] = get_current_user().user_id
            result['user']['role'] = team_player.role

        return make_response(result)

    if request.method == 'POST':
        # check for required fields
        if 'response' not in request.json:
            write_log('ERROR', f'api/reply: missing request fields')
            return {'result': 'error'}, 400

        user_id = get_current_user().user_id if not current_app.config['TESTING'] else None
        if 'user_id' in request.json:
            user_id = int(request.json['user_id'])

        message = None
        if 'message' in request.json:
            message = request.json['message']

        response = None
        if 'response' in request.json:
            response = request.json['response']

        is_goalie = False
        if 'is_goalie' in request.json:
            is_goalie = request.json['is_goalie']

        # check if logged in user == user_id || loged in user == captain on team
        team_player = db.get_team_player(team_id, user_id)
        if (team_player is None or team_player.role == '') and not is_anonymous_sub(user_id):
            write_log('ERROR', f'api/reply: player is not on team')
            return {'result': 'error'}, 400

        if not current_app.config['TESTING'] and user_id != get_current_user().user_id:

            logged_in_player = db.get_team_player(team_id, get_current_user().user_id)
            if logged_in_player is None and not is_anonymous_sub(user_id):
                write_log('ERROR', f'api/reply: player is not on team')
                return {'result': 'error'}, 400

            if logged_in_player and logged_in_player.role == 'captain':
                # this is ok
                pass
            elif get_current_user().admin:
                # this is ok
                pass
            else:
                write_log('ERROR', f'api/reply: {get_current_user().user_id} does not have access to edit reply for {user_id}')
                return {'result': 'error'}, 400

        db.set_game_reply(game_id, team_id,
                          user_id,
                          response,
                          message,
                          is_goalie)

        if get_current_user().user_id != user_id and response != None and not is_anonymous_sub(user_id):

            user = db.get_user_by_id(user_id)
            team = db.get_team_by_id(team_id)
            game = db.get_game_by_id(game_id)

            send_reply_was_changed(db, user, team, game, response, get_current_user())

        write_log('INFO', f'api/game/reply: {user_id} says {response} for game {game_id} set by {get_current_user().user_id}')
        return make_response({ 'result' : 'success' })
