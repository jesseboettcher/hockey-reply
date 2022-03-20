from datetime import datetime
import os
import sys

from flask import current_app, g, make_response, request

from webserver import app
from webserver.database.alchemy_models import User, Team
from webserver.database.hockey_db import get_db
from webserver.logging import write_log


'''
APIs for managing updates to games
'''