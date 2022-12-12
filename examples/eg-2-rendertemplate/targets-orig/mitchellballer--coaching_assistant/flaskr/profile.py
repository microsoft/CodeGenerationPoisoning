from flask import (
    Blueprint, flash, g, redirect, render_template, url_for
)
from flaskr.auth import login_required
from requests_oauthlib import OAuth2Session
from .utils import token_utils, strava_utils, db_utils

import requests
import time

bp = Blueprint('profile', __name__)


@bp.route('/profile')
@login_required
def index():
    return render_template('profile/index.html')


@bp.route('/authorized/')
def authorized():
    return redirect(url_for('profile.index'))


@bp.route('/connect', methods=('GET', 'POST'))
@login_required
def connect():
    print('gathering prerequisites')

    client_id, secret = strava_utils.check_prerequisites()
    bearer_token = g.athlete['strava_bearer_token']
    token_exp = g.athlete['strava_bearer_token_expiration']
    refresh_token = g.athlete['strava_refresh_token']

    # put code to connect to strava here
    print('connecting to strava')

    # TODO get this redirecting to a page where we can use without the command line
    redirect_uri = 'http://localhost:5000/exchange_token'
    auth_url = 'https://www.strava.com/oauth/authorize'
    scope = 'activity:read'

    # if we don't have a bearer token or refresh token, get them.
    if bearer_token is None or refresh_token is None:
        oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=[scope])
        authorization_url, state = oauth.authorization_url(auth_url)
        authorization_url = authorization_url + '&approval_prompt=force'
        return redirect(authorization_url)

    # if we already have a short term token but it's expired, we should refresh
    elif token_exp < time.time():
        token_utils.refresh_existing_token(client_id, secret, refresh_token)

    print('redirecting to profile page')
    return redirect(url_for('profile.index'))


@bp.route('/exchange_token', methods=('GET', 'POST'))
def exchange_token():
    token_utils.exchange_token()
    return redirect(url_for('profile.index'))


@bp.route("/pull_activity/", methods=['POST'])
def hello_world():
    client_id, secret = strava_utils.check_prerequisites()
    valid_token = token_utils.has_valid_token()
    refresh_token = g.athlete['strava_refresh_token']
    bearer_token = g.athlete['strava_bearer_token']
    athlete_id = g.athlete['id']
    if g.athlete['connected_to_strava'] != 1:
        flash("you must be connected to strava")
    elif not valid_token:
        valid_token = token_utils.refresh_existing_token(client_id, secret, refresh_token)

    if valid_token:
        strava_utils.strava_activities(bearer_token, athlete_id, int(time.time()), 0, 4, refresh_token)
    else:
        print(g.athlete['connected_to_strava'])
        flash("You must be connected to strava")
    return render_template('profile/index.html')



