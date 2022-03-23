import os
import sys

from flask import Blueprint, current_app, g, make_response, request
import jwt

from webserver.data_synchronizer import Synchronizer
from webserver.database.alchemy_models import User
from webserver.database.hockey_db import get_db
from webserver.logging import write_log

blueprint = Blueprint('routes', __name__, url_prefix='/api')


@blueprint.route('/sync')
def sync():
    synchronizer = Synchronizer()
    
    if synchronizer.sync():
        return { 'result' : 'success' }
    else:
        return { 'result' : 'faled',
                 'reason' : 'testing' }

