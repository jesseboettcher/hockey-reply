import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

def send_forgot_password(token):
    pass

def send_game_coming_soon():
    pass

def send_game_schedule_change():
    pass

def send_new_games():
    pass

def send_team_role_change():
    pass
