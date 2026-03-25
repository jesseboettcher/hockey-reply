import json
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from enum import Enum
import html
from string import Template

def load_secrets():
    secrets_path = Path(__file__).resolve().parents[2] / 'secrets.json'
    with open(secrets_path, 'r') as f:
        return json.load(f)

def get_ses_client():
    secrets = load_secrets()
    return boto3.client(
        'ses',
        region_name='us-west-2',
        aws_access_key_id=secrets['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=secrets['AWS_SECRET_ACCESS_KEY'],
    )

class EmailTemplate(Enum):
    # name -> corresponds to template filenames
    # e.g. forgot_password.html, forgot_password.txt, forgot_password.subject 
    #
    # value -> corresponds to SendGrid template ID

    FORGOT_PASSWORD    = 'd-16832cb2df954c6cba5cfc41db35a4e1'
    GAME_COMING_SOON   = 'd-b94dc2cebcec407caf3c8e03789d4c34'
    GAME_TIME_CHANGED  = 'd-a252a5f879964f9c88725f31475915a4'
    JOIN_REQUEST       = 'd-f3ad573de30f425aac2657377e7f06af'
    NEW_GAMES          = ''
    ROLE_UPDATED       = 'd-683a41dc2a694123815a1fe3ea8a7881'
    REMOVED_FROM_TEAM  = 'd-0e95577f623d4b5ca53307296856c0f9'
    REPLY_CHANGED      = 'd-a837b5fd27544b688ce72a5315f6bd65'

def send_email_aws_test(template, data, to_emails):
    ''' Sends out email via AWS. All emails funnel through this function
    '''
    client = get_ses_client()

    text_content = None
    html_content = None
    subj_content = None
    with open(f'webserver/email_templates/{template.name.lower()}.html', 'r') as f:
        html_content = f.read()
    with open(f'webserver/email_templates/{template.name.lower()}.txt', 'r') as f:
        text_content = f.read()
    with open(f'webserver/email_templates/{template.name.lower()}.subj', 'r') as f:
        subj_content = f.read()

    html_escaped = html.escape(html_content)
    html_populated = Template(html_content).substitute(data)
    text_populated = Template(text_content).substitute(data)
    subj_populated = Template(subj_content).substitute(data)

    try:
        response = client.send_email(
            Source='jesse@hockeyreply.com',
            Destination={
                'ToAddresses': to_emails
            },
            Message={
                'Subject': {
                    'Data': subj_populated,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_populated,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_populated,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
    except NoCredentialsError:
        print("Error: No AWS credentials found.")
    except PartialCredentialsError:
        print("Error: Incomplete AWS credentials found.")
    except Exception as e:
        print(f"Error: {e}")


# Example usage
subject = "Test Email !"
to_addresses = INSERT_ARRAY_OF_EMAILS
from_address = "jesse@hockeyreply.com"

d = {}
d['name'] = 'Diamond Dog'
d['team'] = 'Con Air'
d['scheduled_how_soon'] = 'a short time'
d['scheduled_at'] = '2024-06-01 22:51:33.409398'
d['rink'] = 'Petit'
d['vs'] = 'losers'
d['reply'] = 'No'
d['goalie'] = 'Nope'
d['confirmed_players'] = 8
d['game_id'] = '283kD'
d['user_team_id'] = '134'
d['user_id'] = 4
d['token'] = 'DEADBEEF'
d['old_scheduled_at'] = 'tomorrow'
d['team_id'] = 'c0ed'
d['updated_by'] = 'the sheriff'
d['role'] = 'inmate'
d['game_count'] = '2'
d['games_label'] = 'games'
d['verb'] = 'have'
d['games_text'] = '''Tue, Mar 24 @ 10:30 PM (in 2 days) vs Barracuda
Thu, Mar 26 @ 09:45 PM (in 4 days) vs Penguins'''
d['open_path'] = 'http://hockeyreply.com/team/134'
d['open_label'] = 'Open Team'
# send_email_aws(EmailTemplate.GAME_COMING_SOON, d, ["jesse@hockeyreply.com"])
# send_email_aws(EmailTemplate.FORGOT_PASSWORD, d, ["jesse@hockeyreply.com"])
# send_email_aws(EmailTemplate.GAME_TIME_CHANGED, d, ["jesse@hockeyreply.com"])
# send_email_aws(EmailTemplate.JOIN_REQUEST, d, ["jesse@hockeyreply.com"])
# send_email_aws(EmailTemplate.NEW_GAMES, d, ["jesse.boettcher@gmail.com"])
# send_email_aws(EmailTemplate.ROLE_UPDATED, d, ["jesse@hockeyreply.com"])
# send_email_aws(EmailTemplate.REMOVED_FROM_TEAM, d, ["jesse@hockeyreply.com"])
send_email_aws_test(EmailTemplate.NEW_GAMES, d, to_addresses)
