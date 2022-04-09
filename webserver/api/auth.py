import datetime
import os
import secrets
import sys

from flask import Blueprint, current_app, g, make_response, request
import jwt

from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
import webserver.email
from webserver.logging import write_log

blueprint = Blueprint('auth', __name__, url_prefix='/api')

def decode_token():
    token = None

    if request.headers['Authorization'].find('Bearer') == 0:
        token = request.headers['Authorization'].split(' ')[1]

    if not token:
        g.token = {}
        return

    try:
        g.token = jwt.decode(token, os.environ.get("SECRET_KEY", "placeholder_key"), algorithms='HS256')
    except jwt.InvalidTokenError as err:
        print(str(err), flush=True)
        abort(401)


def create_token(external_id):
    token = jwt.encode({ 'external_id': external_id, 'date': datetime.datetime.now().isoformat() },
                       os.environ.get("SECRET_KEY", "placeholder_key"),
                       algorithm='HS256')
    return token

def require_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'id' not in g.token:
            print('No authorization provided', flush=True)
            abort(401)

        g.user = get_db().get_user_by_external_id(g.token['external_id'])

        if not g.user:
            response = make_response('', 401)
            response.set_cookie('user', '')
            return response

        return func(*args, **kwargs)

    return wrapper


def check_login():
    if current_app.config['TESTING']:
        return True;

    decode_token()

    if not 'token' in g or 'external_id' not in g.token:
        print('no token!', flush=True)
        return False

    g.user = get_db().get_user_by_external_id(g.token['external_id'])

    if not g.user:
        return False

    return True


@blueprint.route('/hello')
def hello_world():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    result = {}
    result['user_id'] = g.user.user_id
    result['name'] = g.user.first_name

    return make_response(result)


@blueprint.route('/new-user', methods=['POST'])
def new_user():
    db = get_db()

    print(request.json, flush=True)

    # check for required fields
    if 'first_name' not in request.json or \
       'email' not in request.json or \
       'password' not in request.json:

        print(f'api/new-user: missing request fields', flush=True)
        return {'result': 'error'}, 400

    # check if user already has an account
    user_email = request.json['email']
    user = db.get_user(user_email)

    if user:
        # User already exists
        print(f'api/new-user: {user_email} already exists', flush=True)
        return {'result': 'error'}, 400

    # create new user
    user = User(email=user_email.strip().lower(),
                first_name=request.json['first_name'],
                last_name=request.json['last_name'] if 'last_name' in request.json else '',
                created_at=datetime.datetime.now(),
                logged_in_at=datetime.datetime.now(),
                admin=False
                )
    user.password = request.json['password']

    db.add_user(user)
    # TODO error checking on DB op?

    token = create_token(user.external_id);
    response = make_response({ 'result' : 'success', 'token' : token })
    response.set_cookie('user', token)
    write_log('INFO', f'api/sign-up: new user: {user_email}')
    return response


@blueprint.route('/sign-in', methods=['POST'])
def sign_in():
    db = get_db()

    # check for required fields
    if 'email' not in request.json or request.json['email'] == ''\
       'password' not in request.json or request.json['email'] == '':

        print(f'api/sign-in: missing request fields', flush=True)
        return {'result': 'error'}, 400

    # check if user already has an account
    user_email = request.json['email']
    user = db.get_user(user_email)

    if not user:
        # No User
        print(f'api/sign-in: {user_email} not found', flush=True)
        return {'result': 'error'}, 400

    if not user.verify_password(request.json['password']):
        # Sign in failed
        write_log('INFO', f'api/sign-in: {user_email} password verification failed')
        return {'result': 'bad login'}, 400

    user.logged_in_at = datetime.datetime.now()
    get_db().commit_changes()

    token = create_token(user.external_id);
    response = make_response({ 'result' : 'success', 'token' : token })
    response.set_cookie('user', token)
    write_log('INFO', f'api/sign-in: {user_email} success')
    return response


@blueprint.route('/forgot-password', methods=['POST'])
def forgot_password():
    '''
    Generates a 10min expiring token and sends it out to specified email address.
    Tested via postman, not covered in unit tests.
    '''
    if 'email' not in request.json:
        print(f'api/forgot-password: missing request fields', flush=True)
        return {'result': 'error'}, 400

    db = get_db()
    user = db.get_user(request.json['email'])

    if not user:
        write_log('ERROR', f'api/forgot-password: Error {request.json["email"]} does not match any account')
        return {'result': 'success'}, 200

    # set token in user table. set expiry time
    user.password_reset_token = secrets.token_urlsafe(16)
    user.password_reset_token_expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)
    db.commit_changes()

    webserver.email.send_forgot_password(request.json['email'], user.password_reset_token)

    return { 'result' : 'success' }, 200


@blueprint.route('/reset-password', methods=['POST'])
def reset_password():
    '''
    Generates a 10min expiring token and sends it out to specified email address.
    Tested via postman, not covered in unit tests.
    '''
    if 'token' not in request.json or \
       'password' not in request.json:
        print(f'api/reset-password: missing request fields', flush=True)
        return {'result': 'error'}, 400

    db = get_db()
    user = db.get_user_by_password_reset_token(request.json['token'])

    if not user:
        write_log('ERROR', f'api/reset-password: Error user for {request.json["token"]} not found')
        return {'result': 'failed'}, 400

    if datetime.datetime.now(datetime.timezone.utc) > user.password_reset_token_expires_at:

        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        db.commit_changes()

        write_log('ERROR', f'api/reset-password: {request.json["token"]} is expired for {user.email}')
        return {'result': 'expired token'}, 400

    user.password = request.json['password']
    user.password_reset_token = None
    user.password_reset_token_expires_at = None
    db.commit_changes()

    write_log('INFO', f'api/reset-password: Updated password for {user.email}')
    return { 'result' : 'success' }, 200
