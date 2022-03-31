from flask import Flask, g

def create_app(testing=False):
	app = Flask(__name__)

	from webserver.api import auth
	from webserver.api import game
	from webserver.api import routes
	from webserver.api import team

	app.register_blueprint(auth.blueprint)
	app.register_blueprint(game.blueprint)
	app.register_blueprint(routes.blueprint)
	app.register_blueprint(team.blueprint)

	app.config['TESTING'] = testing

	@app.teardown_appcontext
	def close_connection(exception):
	    db = getattr(g, '_database', None)
	    if db is not None:
	        db.close()


	return app
