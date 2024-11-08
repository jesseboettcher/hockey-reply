from flask import Flask, g

def create_app(testing=False):
    app = Flask(__name__)

    from webserver.api import assistant
    from webserver.api import auth
    from webserver.api import calendar
    from webserver.api import game
    from webserver.api import profile
    from webserver.api import routes
    from webserver.api import signaturepdf
    from webserver.api import team
    from webserver.api.chat import blueprint as chat_blueprint

    app.register_blueprint(assistant.blueprint)
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(calendar.blueprint)
    app.register_blueprint(game.blueprint)
    app.register_blueprint(profile.blueprint)
    app.register_blueprint(routes.blueprint)
    app.register_blueprint(team.blueprint)
    app.register_blueprint(signaturepdf.blueprint)
    app.register_blueprint(chat_blueprint)

    from webserver.assistant import Assistant
    app.config['assistant'] = Assistant()

    from webserver.data_synchronizer import Synchronizer
    app.config['synchronizer'] = Synchronizer()

    from webserver.logging import write_log
    import os
    if os.getenv('HOCKEY_REPLY_ENV') == 'prod':
        commit = ''

        try:
            f = open('webserver/COMMIT', 'r')
            commit = f.read().strip('\n')
        except:
            pass

        write_log('INFO', f'Starting up {commit}')

    app.config['TESTING'] = testing
    app.config['DATA_DIR'] = os.path.join(app.root_path, 'data')

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    return app
