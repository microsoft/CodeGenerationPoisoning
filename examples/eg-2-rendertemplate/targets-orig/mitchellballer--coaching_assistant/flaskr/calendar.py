from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
import datetime
import time

from flaskr.auth import login_required
from flaskr.db import get_db
from .utils import strava_utils
from .utils.my_calendar import Month, Week

bp = Blueprint('calendar', __name__)


# get the activities to display on the calendar. Return them with the render template
@bp.route('/list')
def list():
    db = get_db()
    activities = db.execute(
        'SELECT p.id, title, description, start_date, athlete_id, username, distance, duration'
        ' FROM activity p JOIN athlete u ON p.athlete_id = u.id'
        ' ORDER BY start_date DESC'
    ).fetchall()

    return render_template('calendar/list.html', activities=activities)


@bp.route('/')
@login_required
def index():
    return redirect(url_for('calendar.month', year=datetime.datetime.now().year, month=datetime.datetime.now().month))


@bp.route('/month/<int:year>/<int:month>')
@login_required
def month(year, month):
    new_month = Month(year, month)
    new_month.add_activities(g.athlete['id'])
    return render_template('calendar/month.html', month=new_month)

@bp.route('/week/<int:year>/<int:month>/<int:week>')
@login_required
def week(year, month, week):
    month = Month(year, month)
    # week is valid so set it to that.
    if week < len(month.weeks):
        week = month.weeks[week]
    # week is invalid. TODO: create a relevant error page here
    else:
        flash("That week doesn't exist")
        return redirect(url_for('calendar.index', year=year, month=month))

    week.add_activities(g.athlete['id'])
    return render_template('calendar/week.html', week=week, month=month)

# create view. Must be logged in to view
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_date_month = int(request.form['start_date_month'])
        start_date_year = request.form['start_date_year']
        start_date_day = int(request.form['start_date_day'])
        distance = request.form['distance']
        duration = request.form['duration'].split(":")
        error = None

        if not title:
            error = 'Title is required'

        #is a valid year
        if start_date_year.isdigit() and int(start_date_year) > 1960:
            start_date_year = int(start_date_year)
        else:
            error = "year must be an integer year"

        # All date inputs result in a valid date
        try:
            user_date = datetime.datetime(start_date_year, start_date_month, start_date_day)
        except ValueError:
            error = "Invalid date! year: %s, month: %s, day: %s" % (start_date_year, start_date_month, start_date_day)
        
        if not distance.isdigit():
            error = "Invalid distance: %s" % distance
        
        # if they don't provide distance, mark as zero
        if not distance:
            distance = 0

        hour = 0
        minute = 0
        second = 0
        microsecond = 0
        # if they don't provide a duration, mark as zero?
        if not duration:
            duration = 0
        # they gave hours, minutes and seconds
        elif len(duration) == 3:
            hour = duration[0]
            minute = duration[1]
            second = duration[2].split(".")[0]
            if '.' in duration[2]:
                microsecond = duration[2].split(".")[1]
        elif len(distance) == 2:
            minute = duration[0]
            second = duration[1].split(".")[0]
            if '.' in duration[1]:
                microsecond = duration[1].split(".")[1]
        elif len(distance) == 1:
            second = duration[0].split(".")[0]
            if '.' in duration[0]:
                microsecond = duration[0].split(".")[1]
        else:
            error = "Invalid duration format"
        
        try:
            formatted_duration = datetime.time(hour=int(hour), minute=int(minute), second=int(second), microsecond=int(microsecond))
        except ValueError:
            error = "Invalid duration format"

        if error is not None:
            flash(error)
        else:
            duration_seconds = (formatted_duration.hour * 3600) + (formatted_duration.minute * 60) + formatted_duration.second + formatted_duration.microsecond
            db = get_db()
            db.execute(
                'INSERT INTO activity (title, description, start_date, athlete_id, distance, duration)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (title, description, user_date, g.athlete['id'], distance, duration_seconds)
            )
            db.commit()
            return redirect(url_for('calendar.list'))
    months = [['January', 1], ['February', 2], ['March', 3], ['April', 4], ['May', 5], ['June', 6], ['July', 7], ['August', 8],['September', 9], ['October', 10], ['November', 11], ['December', 12]]
    curr = datetime.datetime.now()
    return render_template('activity/create.html', months=months, curr=curr)


@bp.route('/pull', methods=('GET', 'POST'))
@login_required
def pull():
    if request.method == 'POST':
        bearer_token = g.athlete['strava_bearer_token']
        athlete_id = g.athlete['id']
        refresh_token = g.athlete['strava_refresh_token']
        pull_range = request.form['range']
        before = int(time.time())
        after = int(time.time())
        max_activities = 30
        flash(f"Range: {pull_range}")

        if pull_range == "most_recent":
            after = 0
            max_activities = 1
            #strava_utils.strava_activities(bearer_token, athlete_id, time.time(), 0, 1)
        elif pull_range == "today":
            after = int(time.time() - (60 * 60 * 24))
            # no one has more than 30 activities in a day.. right?
        elif pull_range == "week":
            after = int(time.time() - (60 * 60 * 24 * 7))
            max_activities = 100
        elif pull_range == "month":
            #TODO need a more elegant way of saying the past month/day/week.
            after = int(time.time() - (60 * 60 * 24 * 7 * 30))
        strava_utils.strava_activities(bearer_token, athlete_id, before, after, max_activities, refresh_token)

        return redirect(url_for('calendar.list'))

    return render_template('activity/pull.html')