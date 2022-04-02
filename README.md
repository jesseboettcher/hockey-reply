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

# running
* backend
  * `export POSTGRES_PASSWORD=[insert password here]`
  * `export FLASK_APP=webserver`
  * `export GOOGLE_APPLICATION_CREDENTIALS=[path to creds]`
  * `export SENDGRID_API_KEY=[insert api key]`
  * `flask run`
* frontend
  * `cd frontend`
  * `npm run start`

# issue tracking
* https://hockey-reply.youtrack.cloud/issues

# deployments
* database: `hockey-data.cb53hszvt88d.us-west-2.rds.amazonaws.com`
* logging: Google Cloud Logging. `hockey-reply` project
* email: SendGrid. `hockey.reply@ourano.com` replies linked to `hockey.reply@gmail.com`

# testing
* run backend tests: `python -m unittest`
