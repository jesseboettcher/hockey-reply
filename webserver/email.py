import datetime
import os

import humanize
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from webserver.logging import write_log

FROM_ADDRESS = 'hockey.reply@ourano.com'

def send_welcome():
    message = Mail(
        from_email='hockey.reply@ourano.com',
        to_emails='jesse.boettcher@gmail.com',
        subject='Welcome to Hockey Reply',
        html_content='<strong>and easy to do anywhere, even with Python</strong>')
        # TODO note about settings, link to join a team
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
    except Exception as e:
        print(e)

def send_forgot_password(email, token):

    message = Mail(
        from_email=FROM_ADDRESS,
        to_emails=email)

    message.dynamic_template_data = {
                "token" : token
            }
    message.template_id = "d-16832cb2df954c6cba5cfc41db35a4e1" # Forgot password

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
    except Exception as e:
        print(e)

def send_email(data, to_emails):
    message = Mail(
        from_email=FROM_ADDRESS,
        to_emails=to_emails)

    message.dynamic_template_data = data
    message.template_id = "d-b94dc2cebcec407caf3c8e03789d4c34" # Game coming soon

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
    except Exception as e:
        print(e)

def send_game_schedule_change():
    pass

def send_new_games():
    pass

def send_team_role_change():
    pass

def send_game_coming_soon(db, game):
    '''
    send_game_coming_soon is called from the synchronizer worker thread, so use its db instance
    rather than the global requests one
    '''
    for team_id in [game.home_team_id, game.away_team_id]:

        team = db.get_team_by_id(team_id)
        vs_team = db.get_team_by_id(game.home_team_id if team_id == game.away_team_id else game.away_team_id)

        replies = db.game_replies_for_game(game.game_id, team_id)
        confimed_yes = 0
        goalie = 'NO GOALIE!'

        for reply in replies:
            if reply.response == 'yes' and not reply.is_goalie:
                confimed_yes += 1

            if reply.is_goalie:
                goalie = 'Yes'

        for player in team.players:

            if player.role == '':
                continue

            user_reply = ''
            for reply in replies:
                if reply.user_id == player.user_id:
                    user_reply = reply.response

            user = db.get_user_by_id(player.user_id)
            email_data = {
                'name': user.first_name,
                'user_id': user.user_id,
                'game_id': game.game_id,
                'user_team_id': team.team_id,
                'team': team.name,
                'scheduled_at': game.scheduled_at.strftime("%a, %b %d @ %I:%M %p"),
                'scheduled_how_soon': humanize.naturaldelta(game.scheduled_at - datetime.datetime.now(datetime.timezone.utc)).replace(' ', ' '),
                'rink': game.rink,
                'vs': vs_team.name,
                'reply': user_reply.capitalize(),
                'confirmed_players': f'{confimed_yes}',
                'goalie': goalie
            }
            game.did_notify_coming_soon = True
            db.commit_changes()

            send_email(email_data, user.email)
            write_log('INFO', f'Notify coming soon {game.game_id} to {user.email}')
