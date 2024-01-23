# hockey-reply
Web app to manage attendance to Sharks/Solar4America San Jose Adult Hockey League (SIAHL) games

# setup
Using python version 3.9.5:
* `python -m pip venv venv`
* `source venv/bin/activate`
* `pip install -r webserver/requirements.txt`
  * `psycopg2-binary` will fail if `postgresql` and `openssl` are not installed
  * `brew install postgresql`
  * `brew install openssl`

# running locally
* backend
  * `export FLASK_APP=webserver`
  * `export GOOGLE_APPLICATION_CREDENTIALS=[path to creds]`
  * `export POSTGRES_PASSWORD=[insert password here]`
  * `export SECRET_KEY=[insert key]`
  * `export SENDGRID_API_KEY=[insert api key]`
  * `flask run`
* frontend
  * `cd frontend`
  * `npm run start`
  * goto `http://127.0.0.1:3000`

# issue tracking
* https://hockey-reply.youtrack.cloud/issues

# deployments
* database: AWS postgres
* logging: Google Cloud Logging
* email: SendGrid
* to deploy latest to prod:
  * `./deployment/deployall.sh`

# testing
* run backend tests: `python -m unittest`

# screenshots

Check out the the [docs](https://hockeyreply.com/docs) for a full feature list and explanations of how things work.

The homepage shows your latest upcoming games, and a preview of yes/no/goalie status of your teammates.
<div>
 <img src="https://github.com/jesseboettcher/hockey-reply/blob/master/frontend/public/game_details.jpg?raw=true" width="500"/>
</div> <br/>


The game detail page lets you know who replied what and other specifics like your teams' locker room assignment.
<div>
 <img src="https://github.com/jesseboettcher/hockey-reply/blob/master/frontend/public/games_list.jpg?raw=true" width="500"/>
</div> <br/>

Notifications come through email. You'll receive a heads up when a game is upcoming. Other notifications are sent for important changes.
<div>
 <img src="https://github.com/jesseboettcher/hockey-reply/blob/master/frontend/public/email_notification.jpg?raw=true" width="500"/>
</div> <br/>
