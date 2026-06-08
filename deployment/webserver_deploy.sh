# COPIED to and RUN on ec2 host

# frontend
sudo rsync -r www/ /usr/share/nginx/html/

# webserver
set -a
source prod_env.txt
set +a
export HOCKEY_REPLY_ENV=prod
kill $(pgrep flask)
source venv/bin/activate
pip install -r webserver/requirements.txt
nohup flask run &> webserver.out &
