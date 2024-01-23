from datetime import datetime, timedelta

import humanize

def calendardays(start, end):
    ''' Return the number of calendar days between the two dates
    '''
    start = datetime(year=start.year,
                     month=start.month,
                     day=start.day,
                     hour=0,
                     minute=0,
                     second=0,
                     microsecond=0)
    end = datetime(year=end.year,
                     month=end.month,
                     day=end.day,
                     hour=0,
                     minute=0,
                     second=0,
                     microsecond=0)
    count = 0
    while start < end:
        if count > 365:
            # something is wrong
            return -1

        start += timedelta(days=1)
        count += 1

    return count

def timeuntil(start, end):
    ''' Return a string with a human way of describing the time difference. Uses humanize module,
    	but adjusts the output for (1) cases where it under reports, like referring to days in
    	terms of a time duration instead of calendar days and (2) where it produces output that is
    	too long for the UI space

        Important: Pass in local time for the calendar calculation to be correct
    '''
    if start > end:
        return f'{timeuntil_internal(start, end)} ago'

    return f'in {timeuntil_internal(start, end)}'

def timeuntil_internal(start, end):
    delta = end - start
    delta = timedelta(days=delta.days,
                      seconds=int(delta.seconds / 60) * 60, # round to minutes
                      microseconds=0)

    if delta.total_seconds() < 3600:
        return humanize.precisedelta(delta)

    if delta.total_seconds() < 6 * 3600:
        out = humanize.precisedelta(delta)
        out = out.replace('minutes', 'min')
        out = out.replace('minute', 'min')
        out = out.replace(' and', ', ')

        return out

    if delta.days == 0:
        delta = timedelta(days=delta.days,
                          seconds=int(delta.seconds / 3600) * 3600, # round to hours
                          microseconds=0)
        return humanize.naturaldelta(delta)
        
    # create # days string based on calendar days
    cal_day_delta = calendardays(start, end)

    out = f'{cal_day_delta} day'

    if cal_day_delta > 1:
        out += f's'

    return out
