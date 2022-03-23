from flask import Flask, g

def create_app(testing=False):
	app = Flask(__name__)

	from webserver.api import auth
	from webserver.api import game
	from webserver.api import routes
	from webserver.api import team

	from webserver.database import hockey_db

	app.register_blueprint(auth.blueprint)
	app.register_blueprint(game.blueprint)
	app.register_blueprint(routes.blueprint)
	app.register_blueprint(team.blueprint)

	app.config['TESTING'] = testing

	return app
