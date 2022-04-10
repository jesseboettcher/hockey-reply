import datetime
import os
from zoneinfo import ZoneInfo

import humanize
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from webserver.logging import write_log

FROM_ADDRESS = 'jesse@hockeyreply.com'
TEMPLATE_GAME_COMING_SOON = 'd-b94dc2cebcec407caf3c8e03789d4c34'
TEMPLATE_JOIN_REQUEST = 'd-f3ad573de30f425aac2657377e7f06af'
TEMPLATE_ROLE_UPDATED = 'd-683a41dc2a694123815a1fe3ea8a7881'
TEMPLATE_REMOVED_FROM_TEAM = 'd-0e95577f623d4b5ca53307296856c0f9'

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

def send_email(template, data, to_emails):
    message = Mail(
        from_email=FROM_ADDRESS,
        to_emails=to_emails)

    message.dynamic_template_data = data
    message.template_id = template

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
    except Exception as e:
        print(e)

def send_game_schedule_change():
    pass

def send_new_games():
    pass

def send_removed_from_team(team, removed_user, updated_by_user):

    email_data = {
        'name': removed_user.first_name,
        'team': team.name,
        'updated_by': updated_by_user.first_name,
    }

    send_email(TEMPLATE_REMOVED_FROM_TEAM, email_data, removed_user.email)
    write_log('INFO', f'Notify role change to {removed_user.email}')

def send_team_role_change(team, updated_player, updated_by_user):

    email_data = {
        'name': updated_player.player.first_name,
        'team': team.name,
        'updated_by': updated_by_user.first_name,
        'role': updated_player.role
    }

    send_email(TEMPLATE_ROLE_UPDATED, email_data, updated_player.player.email)
    write_log('INFO', f'Notify role change to {updated_player.player.email}')

def send_player_join_request(requesting_player, team):

    email_data = {
        'name': requesting_player.player.first_name,
        'team': team.name,
        'team_id': team.team_id
    }
    to_emails = []

    for player in team.players:

        if player.role == 'captain':
            to_emails.append(player.player.email)
            # to_emails += f'{player.player.email},'

    send_email(TEMPLATE_JOIN_REQUEST, email_data, to_emails)
    write_log('INFO', f'Notify join request {requesting_player.player.email} to {to_emails}')

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

            pacific = ZoneInfo('US/Pacific')
            user = db.get_user_by_id(player.user_id)
            email_data = {
                'name': user.first_name,
                'user_id': user.user_id,
                'game_id': game.game_id,
                'user_team_id': team.team_id,
                'team': team.name,
                'scheduled_at': game.scheduled_at.astimezone(pacific).strftime("%a, %b %d @ %I:%M %p"),
                'scheduled_how_soon': humanize.naturaldelta(game.scheduled_at - datetime.datetime.now(datetime.timezone.utc)).replace(' ', ' '),
                'rink': game.rink,
                'vs': vs_team.name,
                'reply': user_reply.capitalize(),
                'confirmed_players': f'{confimed_yes}',
                'goalie': goalie
            }

            send_email(TEMPLATE_GAME_COMING_SOON, email_data, user.email)
            write_log('INFO', f'Notify coming soon {game.game_id} to {user.email}')
