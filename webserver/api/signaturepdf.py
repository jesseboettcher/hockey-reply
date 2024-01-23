'''
game

All the webserver APIs for querying games and player replies.
'''
import os

from flask import Blueprint, current_app, g, make_response, request, send_from_directory
import io
from PyPDF4 import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from webserver.api.auth import check_login
from webserver.api.game import is_logged_in_user_in_team
from webserver.database.alchemy_models import User, Team
from webserver.database.hockey_db import get_db, get_current_user
from webserver.logging import write_log

'''
APIs for managing updates to games
'''
blueprint = Blueprint('signaturepdf', __name__, url_prefix='/api')


@blueprint.route('/signin-sheet/<team_name_or_id>', methods=['GET'])
def get_signin_sheet(team_name_or_id):
    ''' Generates a signin sheet for the team with the list of players rendered into the 
        signin sheet template.
    '''
    if not check_login():
        return { 'result' : 'needs login' }, 400

    db = get_db()

    team_id = None
    try:
        team_id = int(team_name_or_id)
    except Exception as e:
        # must be a name
        team = db.get_team(team_name_or_id.replace('-', ' '))
        if team:
            team_id = team.team_id

    team = db.get_team_by_id(team_id)

    if not team:
        write_log('ERROR', f'/signin-sheet/<team_id>: team {team_name_or_id} not found')
        return {'result': 'error'}, 400

    # Use the division listed by the next game for the team
    division_string = None
    games = db.get_games_for_team(team.team_id)
    if len(games):
        division_string = f' ({games[0].level})'

    if not is_logged_in_user_in_team(team_id, True):
        write_log('ERROR', f'/signin-sheet/<team_id>: user {get_current_user().user_id} does not have accesss to team {team_name_or_id} not found')
        return {'result': 'error'}, 400

    # Draw canvas with player names and numbers
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    JERSEY_POS_X = 41
    NAME_POS_X = 85
    TEAM_POS_X = 285
    TEAM_POS_Y = 713
    FIRST_BOX_Y = 675
    INCREMENT_Y = -16

    current_y = FIRST_BOX_Y
    can.setFont('Helvetica-Bold', 10)
    can.drawCentredString(TEAM_POS_X, TEAM_POS_Y, f'{team.name}{division_string}')
    can.setFont('Helvetica', 10)

    players = []

    # Create sored list of players
    for player in team.players:
        if player.role == '':
            # do not include players whose memebership has not been accepted
            continue

        players.append( { 'first_name': player.player.first_name,
                           'last_name': player.player.last_name,
                           'number': player.number if player.number else ''
                        })
    players = sorted(players, key=lambda player: player['last_name'])

    # Draw the player info
    for player in players:
        can.drawString(JERSEY_POS_X, current_y, f'{player["number"]}')
        can.drawString(NAME_POS_X, current_y, f'{player["first_name"]} {player["last_name"]}')
        current_y += INCREMENT_Y

    can.save()
    packet.seek(0) #move to the beginning of the StringIO buffer

    # Merge the template and the drawn team information
    new_pdf = PdfFileReader(packet)

    existing_pdf = PdfFileReader(open('webserver/data/signin_sheet_template.pdf', 'rb'))
    output = PdfFileWriter()

    page = existing_pdf.getPage(0)
    page.mergePage(new_pdf.getPage(0))
    output.addPage(page)

    outputStream = open(f'webserver/data/{team.name} signin sheet.pdf'.replace(' ', '_'), "wb")
    output.write(outputStream)
    outputStream.close()

    write_log('INFO', f'api/signin-sheet: {team_name_or_id} ({team.name})')
    return send_from_directory(directory=current_app.config['DATA_DIR'],
                               path=f'{team.name} signin sheet.pdf'.replace(' ', '_'))
                               # path=os.path.join(current_app.config['DATA_DIR'], f'{team.name} signin sheet.pdf'.replace(' ', '_')))

