'''
chat

APIs for game chat functionality including messages and reactions
'''
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, g, current_app
import logging
from sqlalchemy import and_, desc
from functools import wraps

from webserver.api.auth import check_login
from webserver.database.hockey_db import get_db, get_current_user
from webserver.database.alchemy_models import GameChatMessage, GameChatReaction
from webserver.api.game import is_logged_in_user_in_team
from webserver.logging import write_log

blueprint = Blueprint('chat', __name__, url_prefix='/api/chat')

# Create a filter class to exclude messages containing a substring
class EndpointFilter(logging.Filter):
    def __init__(self, excluded_substr):
        self.excluded_substr = excluded_substr

    def filter(self, record):
        # Check if request exists in current context
        if self.excluded_substr in record.getMessage():
            return False
        return True

# Add the filter to werkzeug logger
logging.getLogger('werkzeug').addFilter(EndpointFilter('GET /api/chat/messages'))

def get_player_name(db, user_id):
    user = db.get_user_by_id(user_id)
    user_name = user.first_name
    if user.last_name:
        user_name += f' {user.last_name}'
    return user_name

@blueprint.route('/messages/<game_id>/for-team/<team_id>', methods=['GET'])
def get_messages(game_id, team_id):
    '''
    GET messages for a game, with optional parameters:
    - since: timestamp to get only newer messages
    - thread_id: get messages for specific thread
    - limit: max number of messages to return (default 50)
    '''
    if not check_login():
        return {'result': 'needs login'}, 400

    if not is_logged_in_user_in_team(int(team_id), True):
        return {'result': 'unauthorized'}, 403

    db = get_db()
    
    # Parse query parameters
    since = request.args.get('since', type=float)
    thread_id = request.args.get('thread_id', type=int)
    limit = min(int(request.args.get('limit', 50)), 100)  # Cap at 100
    
    query = db.session.query(GameChatMessage).filter(
        and_(
            GameChatMessage.game_id == game_id,
            GameChatMessage.team_id == team_id,
            GameChatMessage.is_deleted == False
        )
    )
    
    if since:
        since_dt = datetime.fromtimestamp(since, tz=timezone.utc)
        query = query.filter(GameChatMessage.created_at > since_dt)
        
    if thread_id:
        query = query.filter(GameChatMessage.parent_message_id == thread_id)
    else:
        query = query.filter(GameChatMessage.parent_message_id == None)
        
    messages = query.order_by(desc(GameChatMessage.created_at)).limit(limit).all()
    
    team = db.get_team_by_id(team_id)
    players = {
        player.user_id: get_player_name(db, player.user_id) for player in team.players
    }

    return {
        'players': players,
        'messages': [{
            'message_id': msg.message_id,
            'user_id': msg.user_id,
            'content': msg.content,
            'created_at': msg.created_at.timestamp(),
            'edited_at': msg.edited_at.timestamp() if msg.edited_at else None,
            'reactions': [
                {
                    'emoji': reaction.emoji,
                    'user_id': reaction.user_id,
                    'created_at': reaction.created_at.timestamp()
                } for reaction in msg.reactions
            ]
        } for msg in messages]
    }

@blueprint.route('/message', methods=['POST'])
def post_message():
    '''
    POST a new message with JSON body:
    {
        game_id: int,
        team_id: int,
        content: string,
        parent_message_id: int (optional)
    }
    '''
    if not check_login():
        return {'result': 'needs login'}, 400

    data = request.get_json()
    db = get_db()
    user = get_current_user()

    if not is_logged_in_user_in_team(int(data['team_id']), True):
        return {'result': 'unauthorized'}, 403

    message = GameChatMessage(
        game_id=data['game_id'],
        team_id=data['team_id'],
        user_id=user.user_id,
        content=data['content'],
        parent_message_id=data.get('parent_message_id'),
        created_at=datetime.now(timezone.utc)
    )
    
    db.session.add(message)
    db.session.commit()
    
    return {'message_id': message.message_id}

@blueprint.route('/message/<message_id>', methods=['PUT', 'DELETE'])
def update_message(message_id):
    '''
    PUT to edit message content
    DELETE to soft-delete message
    '''
    if not check_login():
        return {'result': 'needs login'}, 400
        
    db = get_db()
    user = get_current_user()
    
    message = db.session.query(GameChatMessage).get(message_id)
    if not message or message.user_id != user.user_id:
        return {'result': 'unauthorized'}, 403
    
    if request.method == 'PUT':
        data = request.get_json()
        message.content = data['content']
        message.edited_at = datetime.now(timezone.utc)
    else:  # DELETE
        message.is_deleted = True
        
    db.session.commit()
    return {'result': 'success'}

@blueprint.route('/reaction', methods=['POST', 'DELETE'])
def toggle_reaction():
    '''
    POST to add reaction, DELETE to remove
    JSON body: {
        message_id: int,
        emoji: string
    }
    '''
    if not check_login():
        return {'result': 'needs login'}, 400
        
    data = request.get_json()
    db = get_db()
    user = get_current_user()
    
    existing = db.session.query(GameChatReaction).filter(
        and_(
            GameChatReaction.message_id == data['message_id'],
            GameChatReaction.user_id == user.user_id,
            GameChatReaction.emoji == data['emoji']
        )
    ).first()
    
    if request.method == 'POST' and not existing:
        reaction = GameChatReaction(
            message_id=data['message_id'],
            user_id=user.user_id,
            emoji=data['emoji'],
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(reaction)
        
    elif request.method == 'DELETE' and existing:
        db.session.delete(existing)
        
    db.session.commit()
    return {'result': 'success'}
