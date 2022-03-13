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
* `export POSTGRES_PASSWORD`
* `cd webserver`
* `python data_synchronizer.py`
