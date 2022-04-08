import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

def send_game_coming_soon(data):

    message = Mail(
        from_email=FROM_ADDRESS,
        to_emails='jesse.boettcher@gmail.com')

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
