# DEPLOY frontend and webserver to ec2
# Expects cwd is root of project /hockey-reply
# Requires a file of env exports in hockey-reply/kes/prod_env.txt

echo "Beginning deploy to ec2"

echo "\tSending scripts"
rsync deployment/webserver_deploy.sh ec2-user@hockeyreply.com:/home/ec2-user/
rsync keys/prod_env.txt ec2-user@hockeyreply.com:/home/ec2-user/
ssh ec2-user@hockeyreply.com chmod +x /home/ec2-user/webserver_deploy.sh

# copy latest build
echo "\tCopying latest build"
echo $(git log -1 --format=format:%H) > webserver/COMMIT
rsync -r frontend/build/ ec2-user@hockeyreply.com:/home/ec2-user/www
rsync -r webserver ec2-user@hockeyreply.com:/home/ec2-user/
rm webserver/COMMIT

echo "\tRestarting webserver"
ssh ec2-user@hockeyreply.com /home/ec2-user/webserver_deploy.sh
ssh ec2-user@hockeyreply.com rm /home/ec2-user/prod_env.txt

echo "Finished deploy"
