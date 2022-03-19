from datetime import datetime
import os
import sys

from flask import current_app, g, make_response, request
import jwt

from webserver import app
from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
from webserver.logging import write_log

def decode_cookie():
    cookie = request.cookies.get('user')

    if not cookie:
        g.cookie = {}
        return

    print(cookie, flush=True)
    try:
        g.cookie = jwt.decode(cookie, os.environ.get("SECRET_KEY", "placeholder_key"), algorithms='HS256')
        print(g.cookie, flush=True)
    except jwt.InvalidTokenError as err:
        print(str(err), flush=True)
        abort(401)


def create_cookie(external_id):
    token = jwt.encode({ 'external_id': external_id, 'date': datetime.now().isoformat() },
                       os.environ.get("SECRET_KEY", "placeholder_key"),
                       algorithm='HS256')
    return token

def require_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'id' not in g.cookie:
            print('No authorization provided', flush=True)
            abort(401)

        g.user = get_db().get_user_by_id(g.cookie['external_id'])

        if not g.user:
            response = make_response('', 401)
            response.set_cookie('user', '')
            return response

        return func(*args, **kwargs)

    return wrapper


def check_login():
    decode_cookie()

    if not 'cookie' in g or 'external_id' not in g.cookie:
        print('no cookie!', flush=True)
        return False

    g.user = get_db().get_user_by_id(g.cookie['external_id'])

    if not g.user:
        return False

    return True


@app.route('/api/hello')
def hello_world():

    if not check_login():
        return { 'result' : 'needs login' }, 400

    return { 'result' : 'success' }


@app.route('/api/new-user', methods=['POST'])
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
                created_at=datetime.now(),
                logged_in_at=datetime.now()
                )
    user.password = request.json['password']

    db.add_user(user)
    # TODO error checking on DB op?

    response = make_response({ 'result' : 'success' })
    response.set_cookie('user', create_cookie(user.external_id))
    write_log('INFO', f'api/sign-up: new user: {user_email}')
    return response


@app.route('/api/sign-in', methods=['POST'])
def sign_in():
    db = get_db()

    print(request.json, flush=True)

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

    user.logged_in_at = datetime.now()
    get_db().commit_changes()

    response = make_response({ 'result' : 'success' })
    response.set_cookie('user', create_cookie(user.external_id))
    write_log('INFO', f'api/sign-in: {user_email} success')
    return response


@app.route('/api/forgot-password')
def forgot_password():
    return { 'result' : 'unhandled' }, 400
