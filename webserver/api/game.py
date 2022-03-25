from datetime import datetime
import os
import sys

from flask import Blueprint, current_app, g, make_response, request

from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db
from webserver.logging import write_log
from webserver.api.auth import check_login


'''
APIs for managing updates to games
'''
blueprint = Blueprint('game', __name__, url_prefix='/api')

@blueprint.route('/games/<team_id>', methods=['GET'])
def get_games(team_id):
    '''
    Returns all games for the specified team. Includes flag for whether the game was completed.
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()
    games = db.get_games_for_team(team_id)

    result = { 'games': [] }
    for game in games:

        game_dict = {
            'game_id' : game.game_id,
            'scheduled_at': game.scheduled_at,
            'completed': game.completed,
            'rink': game.rink,
            'level': game.level,
            'home_team_id': game.home_team_id,
            'away_team_id': game.away_team_id,
            'home_goals': game.home_goals,
            'away_goals': game.away_goals,
            'game_type': game.game_type
        }
        result['games'].append(game_dict)

    return make_response(result)


@blueprint.route('/game/<game_id>', methods=['GET'])
def get_game(game_id):
    '''
    Returns the details for the specified game: game date/time, rink, home/away, vs
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

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

    result = { 'games': [] }
    game_dict = {
        'game_id' : game.game_id,
        'scheduled_at': game.scheduled_at,
        'completed': game.completed,
        'rink': game.rink,
        'level': game.level,
        'home_team_id': game.home_team_id,
        'home_team_name': home_team.name,
        'away_team_id': game.away_team_id,
        'away_team_name': away_team.name,
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
    GET list of replies for a game
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    if request.method == 'GET':
        replies = db.game_replies_for_game(game_id, team_id)

        result = { 'replies': [] }

        for reply in replies:
            reply_dict = {
                'reply_id': reply.reply_id,
                'game_id': reply.game_id,
                'user_id': reply.user_id,
                'response': reply.response,
                'message': reply.message
            }
            result['replies'].append(reply_dict)

        return make_response(result)

    if request.method == 'POST':
        # check for required fields
        if 'user_id' not in request.json or \
           'response' not in request.json:
            write_log('ERROR', f'api/reply: missing request fields')
            return {'result': 'error'}, 400

        # check if logged in user == user_id || loged in user == captain on team
        team_player = db.get_team_player(team_id, request.json['user_id'])
        if team_player is None:
            write_log('ERROR', f'api/reply: player is not on team')
            return {'result': 'error'}, 400

        if not current_app.config['TESTING'] and user_id != g.user.id:

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
                write_log('ERROR', f'api/reply: {g.user.user_id} does not have access to edit reply for {response.json["user_id"]}')
                return {'result': 'error'}, 400

        db.set_game_reply(game_id, team_id,
                          request.json['user_id'],
                          request.json['response'],
                          request.json['message'])

        write_log('INFO', f'api/game/reply: {request.json["user_id"]} says {request.json["response"]} for game {game_id}')
        return make_response({ 'result' : 'success' })
