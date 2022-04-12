'''
game

All the webserver APIs for querying games and player replies.
'''
import datetime
import os
import sys
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, g, make_response, request
import humanize
from ics import Calendar, DisplayAlarm, Event

from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db, get_current_user
from webserver.logging import write_log

'''
APIs for managing updates to games
'''
blueprint = Blueprint('calendar', __name__, url_prefix='/api')


@blueprint.route('/calendar/<team_name_or_id>/hockey_calendar.ics', methods=['GET'])
def get_calendar(team_name_or_id):
    ''' Returns a calendar file for a team
    '''
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
        write_log('ERROR', f'/calendar/<team_id>: team {team_name_or_id} not found')
        return {'result': 'error'}, 400

    games = db.get_games_for_team(team_id)

    # Generate the ics
    calendar = Calendar()

    for game in games:
        home_team = db.get_team_by_id(game.home_team_id)
        away_team = db.get_team_by_id(game.away_team_id)
    
        date_format = '%Y-%m-%d %H:%M:%S' # Format for dates expected by ics module
        duration = datetime.timedelta(hours=1, minutes=15)
        game_end = game.scheduled_at + duration

        alarm = DisplayAlarm()
        alarm.trigger = datetime.timedelta(minutes=-45)

        event = Event()
        event.name = f'{away_team.name} @ {home_team.name}'
        event.begin = game.scheduled_at.strftime(date_format)
        event.end = game_end.strftime(date_format)
        event.duration = duration
        event.location = game.rink
        event.alarms = [alarm]

        calendar.events.add(event)

    write_log('INFO', f'api/calendar: {team_name_or_id} ({team.name})')

    # Write to string
    out_cal = ''
    for line in calendar:
        out_cal += line

    response = make_response(out_cal)
    response.headers['Content-Disposition'] = 'attachment; filename=calendar.ics'
    response.headers['Content-Type'] = 'text/calendar'
    return response
