import os
import sys

from flask import Blueprint, current_app, g, make_response, request
import jwt

from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
from webserver.logging import write_log

blueprint = Blueprint('routes', __name__, url_prefix='/api')

@blueprint.route('/goodbye', methods=['GET', 'POST'])
def goodbye():
    if request.method == 'GET':
        write_log('INFO', 'received goodbye event')
        return { 'result' : 'unhandled' }, 400

    print("POST api/goodbye", flush=True)
    print(f"{request.json}", flush=True)
    return { 'result' : 'success' }, 200


@blueprint.route('/sync')
def sync():
    synchronizer = Synchronizer()
    
    if synchronizer.sync():
        return { 'result' : 'success' }
    else:
        return { 'result' : 'faled',
                 'reason' : 'testing' }

