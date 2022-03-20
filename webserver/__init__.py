from flask import Flask

app = Flask(__name__)
import webserver.api.auth
import webserver.api.game
import webserver.api.routes
import webserver.api.team
