from webserver import app
from webserver.data_synchronizer import Synchronizer

@app.route('/api/goodbye')
def goodbye():
    return '<p>see you later!</p>'

@app.route('/')
def hello_world():
    return '<p>hello!</p>'

@app.route('/api/sync')
def sync():
    synchronizer = Synchronizer()
    
    if synchronizer.sync():
        return { 'result' : 'success' }
    else:
        return { 'result' : 'faled',
                 'reason' : 'testing' }
