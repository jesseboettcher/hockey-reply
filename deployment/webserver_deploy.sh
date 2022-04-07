# COPIED to and RUN on ec2 host

# frontend
sudo rsync -r www/ /usr/share/nginx/html/

# webserver
source prod_env.txt
kill $(pgrep flask)
source venv/bin/activate
pip install -r webserver/requirements.txt
nohup flask run &> webserver.out &