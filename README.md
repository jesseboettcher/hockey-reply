# hockey-reply
Web app to manage attendance to Sharks/Solar4America San Jose Adult Hockey League (SIAHL) games

# setup
Using python version 3.9.5:
* `python -m pip venv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`
  * `psycopg2-binary` will fail if `postgresql` and `openssl` are not installed
  * `brew install postgresql`
  * `brew install openssl`

# running
* backend
  * `export POSTGRES_PASSWORD=[insert password here]`
  * `export FLASK_APP=webserver`
  * `python -m flask run`
* frontend
  * `cd frontend`
  * `npm run start`

# issue tracking
* https://hockey-reply.youtrack.cloud/issues
