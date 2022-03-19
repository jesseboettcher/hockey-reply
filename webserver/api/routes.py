import os
import sys

from flask import current_app, g, make_response, request
import jwt

from webserver import app
from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db

@app.route('/api/goodbye', methods=['GET', 'POST'])
def goodbye():
    if request.method == 'GET':
        return { 'result' : 'unhandled' }, 400

    print("POST api/goodbye", flush=True)
    print(f"{request.json}", flush=True)
    return { 'result' : 'success' }, 200


@app.route('/api/sync')
def sync():
    synchronizer = Synchronizer()
    
    if synchronizer.sync():
        return { 'result' : 'success' }
    else:
        return { 'result' : 'faled',
                 'reason' : 'testing' }

