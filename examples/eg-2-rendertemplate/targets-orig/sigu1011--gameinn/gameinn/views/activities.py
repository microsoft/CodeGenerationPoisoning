import datetime
import bcrypt
from flask import request, render_template, session, jsonify
from functools import wraps
from sqlalchemy import func
from gameinn import db
from gameinn import activity_schema
from gameinn.models.users import User
from gameinn.models.activity import Activity
from gameinn.views.views import login_required
from flask import Blueprint
from jsonschema import Draft7Validator

activity = Blueprint('activity', __name__)


# Decorated validation
def validate_schema(schema):
    validator = Draft7Validator(schema)

    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            data = request.get_json()
            errors = [error.message for error in validator.iter_errors(data)]
            if errors:
                response = jsonify(dict(success=False, message='invalid request', error=errors))
                response.status_code = 406
                return response
            else:
                return func(*args, **kwargs)

        return wrapped

    return wrapper


def get_days(start, end):
    terms = []
    t = start
    while t <= end:
        terms.append(t)
        t += datetime.timedelta(days=1)
    return terms


def get_terms(start, end):
    terms = []
    t = start
    while t < end:
        terms.append(t)
        t += datetime.timedelta(hours=1)
    return terms


@activity.route('/')
@login_required
def show_dashboard():
    # Create data for Heatmap
    key_activity = [{'name': '7days ago', 'data': []},
                    {'name': '6days ago', 'data': []},
                    {'name': '5days ago', 'data': []},
                    {'name': '4days ago', 'data': []},
                    {'name': '3days ago', 'data': []},
                    {'name': '2days ago', 'data': []},
                    {'name': '1day ago', 'data': []},
                    {'name': 'Today', 'data': []}]
    mouse_activity = [{'name': '7days ago', 'data': []},
                      {'name': '6days ago', 'data': []},
                      {'name': '5days ago', 'data': []},
                      {'name': '4days ago', 'data': []},
                      {'name': '3days ago', 'data': []},
                      {'name': '2days ago', 'data': []},
                      {'name': '1day ago', 'data': []},
                      {'name': 'Today', 'data': []}]

    end_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_day = end_day - datetime.timedelta(days=7)
    days = get_days(start_day, end_day)
    # This is a list of dates to be calculated activities.
    # example [2019-11-20 00:00:00, 2019-11-21 00:00:00, ...]
    for i, d in enumerate(days):
        start_time = d
        end_time = start_time + datetime.timedelta(days=1)
        terms = get_terms(start_time, end_time)
        # activity is calculated every hour.
        # example 2019-11-20 00:00:00 <-> 2019-11-20 01:00:00, 2019-11-20 01:00:00 <-> 2019-11-20 02:00:00, ...
        for j, time in enumerate(terms):
            if j == (len(terms) - 1):
                break
            begin = time
            end = terms[j + 1]

            data = db.session.query(func.sum(Activity.keyboard_activity), func.sum(Activity.mouse_activity)).filter(
                Activity.created_at >= begin,
                Activity.created_at < end,
                Activity.user_id == session['user_id']
            ).all()

            key_activity[i]['data'].append(data[0][0])
            mouse_activity[i]['data'].append(data[0][1])

        key_activity[i]['data'] = [0 if n is None else n for n in key_activity[i]['data']]
        mouse_activity[i]['data'] = [0 if n is None else n for n in mouse_activity[i]['data']]

    key_score = max(key_activity[7]['data'])
    mouse_score = max(mouse_activity[7]['data'])

    # Get favorite app name
    today_begin = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Select [(app_name, count(app_name)), ...]
    app_list = db.session.query(Activity.active_app_name, func.count(Activity.active_app_name)).filter(
        Activity.created_at >= today_begin,
        Activity.created_at < today_begin + datetime.timedelta(days=1),
        Activity.user_id == session['user_id']
    ).group_by(Activity.active_app_name).all()

    most_active_app = None
    if len(app_list) > 0:
        most_active_app = max(app_list, key=lambda x: x[1])[0]

    return render_template('activities/dashboard.html', key_score=key_score, mouse_score=mouse_score,
                           key_activity=key_activity, mouse_activity=mouse_activity, app_name=most_active_app)


@activity.route('/activities', methods=['POST'])
@validate_schema(activity_schema)
def add_activities():
    data = request.get_json()
    username = data['username']
    password = data['password']
    try:
        user = User.query.filter_by(username=username).first()
    except:
        response = jsonify(dict(success=False, message='Authentication error', error=['This user does not exist']))
        response.status_code = 403
        return response

    if username != user.username:
        response = jsonify(dict(success=False, message='Authentication error', error=['This user does not exist']))
        response.status_code = 403
        return response
    elif bcrypt.hashpw(password.encode(), user.salt.encode()).decode() != user.password:
        response = jsonify(dict(success=False, message='Authentication error', error=['This password is incorrect']))
        response.status_code = 403
        return response
    else:
        activity = Activity(
            alphanumeric_key_count=data['alphanumeric_key_count'],
            special_key_count=data['special_key_count'],
            keyboard_activity=data['keyboard_activity'],
            mouse_movement=data['mouse_movement'],
            mouse_click_count=data['mouse_click_count'],
            mouse_scroll_count=data['mouse_scroll_count'],
            mouse_activity=data['mouse_activity'],
            active_app_name=data['app_name'],
            user_id=user.id
        )
        db.session.add(activity)
        db.session.commit()
        response = jsonify(dict(success=True, message='success'))
        response.status_code = 200
        return response
