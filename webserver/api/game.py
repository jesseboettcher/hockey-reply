import datetime
import os
import sys

from flask import Blueprint, current_app, g, make_response, request
import humanize

from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db
from webserver.logging import write_log
from webserver.api.auth import check_login


'''
APIs for managing updates to games
'''
blueprint = Blueprint('game', __name__, url_prefix='/api')


def is_logged_in_user_in_team(team_id):
    if current_app.config['TESTING']:
        return True

    user_in_team = False
    for team in g.user.teams:
        if team.team_id == team_id:
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
        for team in g.user.teams:
            teams.append(team)

    for team in teams:

        games = db.get_games_for_team(team.team_id)

        for game in games:

            if upcomingOnly and game.completed == 1:
                continue

            home_team = db.get_team_by_id(game.home_team_id)
            away_team = db.get_team_by_id(game.away_team_id)

            if home_team is None or away_team is None:
                write_log('ERROR', f'/api/game/<game>: Team for game {game.game_id} is not found')
                return {'result': 'error'}, 400

            if game.home_team_id is not team.team_id and game.away_team_id is not team.team_id:
                write_log('ERROR', f'/api/game/<game>: Team ({team.team_id}) is not in game {game.game_id}')
                return {'result': 'error'}, 400

            game_dict = {
                'game_id' : game.game_id,
                'scheduled_at': game.scheduled_at.strftime("%a, %b %d @ %I:%M %p"),
                'scheduled_how_soon': humanize.naturaldelta(game.scheduled_at - datetime.datetime.now(datetime.timezone.utc)).replace(' ', ' '),
                'completed': game.completed,
                'rink': game.rink,
                'level': game.level,
                'home_team_id': game.home_team_id,
                'away_team_id': game.away_team_id,
                'vs': home_team.name if game.away_team_id == team.team_id else away_team.name,
                'home_goals': game.home_goals,
                'away_goals': game.away_goals,
                'game_type': game.game_type
            }
            result['games'].append(game_dict)

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

    if game.home_team_id is not team_id and game.away_team_id is not team_id:
        write_log('ERROR', f'/api/game/<game>: Team ({team_id}) is not in game {game_id}')
        return {'result': 'error'}, 400

    result = { 'games': [] }

    game_dict = {
        'game_id' : game.game_id,
        'scheduled_at': game.scheduled_at.strftime("%a, %b %d @ %I:%M %p"),
        'scheduled_how_soon': humanize.naturaldelta(game.scheduled_at - datetime.datetime.now(datetime.timezone.utc)).replace(' ', ' '),
        'completed': game.completed,
        'rink': game.rink,
        'level': game.level,
        'home_team_id': game.home_team_id,
        'home_team_name': home_team.name,
        'away_team_id': game.away_team_id,
        'away_team_name': away_team.name,
        'vs': home_team.name if game.away_team_id == team_id else away_team.name,
        'home_goals': game.home_goals,
        'away_goals': game.away_goals,
        'game_type': game.game_type
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

    if request.method == 'GET':

        if not is_logged_in_user_in_team(team_id):
            write_log('ERROR', f'/api/game/reply: {g.user.email} does not have access to replies for game {game_id} and {team_id}')
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

            if reply_player is None:
                # player was removed from the team
                continue

            reply_dict = {
                'reply_id': reply.reply_id,
                'game_id': reply.game_id,
                'user_id': reply.user_id,
                'name': f'{reply_player.player.first_name} ({reply_player.role})',
                'response': reply.response,
                'message': reply.message
            }
            replies_dict[reply.user_id] = reply_dict

        result['replies'] = list(replies_dict.values())

        # Collect the players who have not yet responded
        team = db.get_team_by_id(team_id)
        for player in team.players:
            if player.user_id not in replies_dict:
                reply_dict = {
                    'reply_id': 0,
                    'user_id': player.user_id,
                    'name': f'{player.player.first_name} ({player.role})'
                }
                result['no_response'].append(reply_dict)

        # Add the logged in user information
        team_player = db.get_team_player(team_id, g.user.user_id)
        result['user'] = {}
        result['user']['user_id'] = g.user.user_id
        result['user']['role'] = team_player.role

        return make_response(result)

    if request.method == 'POST':
        # check for required fields
        if 'response' not in request.json:
            write_log('ERROR', f'api/reply: missing request fields')
            return {'result': 'error'}, 400

        user_id = g.user.user_id
        if 'user_id' in request.json:
            user_id = request.json['user_id']

        message = None
        if 'message' in request.json:
            message = request.json['message']

        response = None
        if 'response' in request.json:
            response = request.json['response']

        # check if logged in user == user_id || loged in user == captain on team
        team_player = db.get_team_player(team_id, user_id)
        if team_player is None:
            write_log('ERROR', f'api/reply: player is not on team')
            return {'result': 'error'}, 400

        if not current_app.config['TESTING'] and user_id != g.user.user_id:

            logged_in_player = db.get_team_player(team_id, g.user.user_id)
            if logged_in_player is None:
                write_log('ERROR', f'api/reply: player is not on team')
                return {'result': 'error'}, 400

            if logged_in_player and logged_in_player.role == 'captain':
                # this is ok
                pass
            elif g.user.admin:
                # this is ok
                pass
            else:
                write_log('ERROR', f'api/reply: {g.user.user_id} does not have access to edit reply for {user_id}')
                return {'result': 'error'}, 400

        db.set_game_reply(game_id, team_id,
                          user_id,
                          response,
                          message)

        write_log('INFO', f'api/game/reply: {user_id} says {response} for game {game_id}')
        return make_response({ 'result' : 'success' })
