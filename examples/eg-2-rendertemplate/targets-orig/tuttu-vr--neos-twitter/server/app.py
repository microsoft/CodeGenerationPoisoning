import os
import sys
import datetime
import traceback
from requests.exceptions import ConnectionError
from urllib.parse import quote
from logging import getLogger
from flask import Flask, request, render_template, redirect, url_for, session
from flask_babel import Babel
from werkzeug.exceptions import (
    BadRequestKeyError,
    BadRequest,
    InternalServerError
)

from lib import oauth, notification
from lib.session import (
    validate_token,
    generate_new_session,
    validate_session_id
)
from lib.settings import logging_config, get_arguments, TWEET_DELIMITER
from lib.model_utils.messages import get_recent_messages
from common import configs
from common.lib import crypt, datetime_utils
from common.models import neotter_user

import api.v2.response

app = Flask(__name__)
babel = Babel(app)
logger = getLogger(__name__)


DELIMITER = TWEET_DELIMITER
DATETIME_FORMAT = configs.datetime_format

DEFAULT_BACKTIME_MINUTES = 30

TIMEZONE_LOCAL = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
TIMEZONE_UTC = datetime.timezone(datetime.timedelta(hours=+0), 'UTC')


def _process_messages(messages, start_time):
    # TODO process have to be into Message class
    def process_message(mes):
        utc_time = datetime_utils.neotter_inner_to_datetime(
            mes['created_datetime'])
        local_time_str = utc_time.astimezone(
            TIMEZONE_LOCAL).strftime(DATETIME_FORMAT)
        try:
            return ';'.join([
                quote(local_time_str),
                quote(mes['name']),
                quote(mes['icon_url']),
                quote(mes['attachments']) if mes['attachments'] else '',
                mes['message']
            ])
        except TypeError:
            logger.error(traceback.format_exc())
            for key in mes.keys():
                logger.error('%s=%s' % (key, str(mes[key])))
            return None
    text_list = list(
        filter(lambda x: x, [process_message(mes) for mes in messages]))
    response = DELIMITER.join(text_list)
    return f'{start_time}|{len(text_list)}|{response}'


def _get_user(token: str, remote_addr: str) -> neotter_user.NeotterUser:
    if not validate_token(token):
        raise ValueError('Error: no valid token found')
    user = neotter_user.get_by_token(token)
    if not user:
        raise ValueError(f'Error: invalid token {token}')
    if user.enable_ip_confirm \
            and crypt.decrypt(user.remote_addr) != remote_addr:
        raise ValueError(f'Error: invalid addr {remote_addr}')
    return user


def _get_remote_addr(request):
    logger.debug(request.remote_addr)
    logger.debug(request.headers.get('X-Real-IP'))
    if os.getenv('APPLICATION_ENV') == 'production':
        remote_addr = request.headers.get('X-Real-IP')
        if not remote_addr:
            raise EnvironmentError('X-Real-IP must be set in production')
    else:
        remote_addr = request.remote_addr
    return remote_addr


def _get_start_time(start_time: str):
    if not start_time:
        start_time_utc = datetime.datetime.now(TIMEZONE_UTC) - \
            datetime.timedelta(minutes=DEFAULT_BACKTIME_MINUTES)
        start_time = start_time_utc.astimezone(
            TIMEZONE_LOCAL).strftime(DATETIME_FORMAT)
        return start_time, start_time_utc
    try:
        start_time_local = datetime.datetime.strptime(
            start_time, DATETIME_FORMAT).replace(tzinfo=TIMEZONE_LOCAL)
        start_time_utc = start_time_local.astimezone(TIMEZONE_UTC)
        logger.debug(start_time_utc)
        return start_time, start_time_utc
    except ValueError:
        # to avoid sql injection
        raise ValueError(
            f'Error: start time format must be '
            f'"{DATETIME_FORMAT}" but "{start_time}"')


message_processer = {
    'v1': _process_messages,
    'v2': api.v2.response.get_recent_response
}


def _get_recent(
        count: int, offset: int, start_time: str, user_token: str,
        remote_addr: str, version: str = 'v1'):
    user = _get_user(user_token, remote_addr).to_dict()
    start_time, start_time_utc = _get_start_time(start_time)

    logger.debug(f'count={count} offset={offset} start_time={start_time}')

    messages = get_recent_messages(
        count, offset, start_time_utc.strftime(DATETIME_FORMAT), user['id'])
    neotter_user.extend_expiration(user['id'])
    response = message_processer[version](messages, start_time)
    return response


@app.route('/recent')
def get_recent():
    # deprecated
    count = request.args.get('count', default=3, type=int)
    offset = request.args.get('offset', default=0, type=int)
    start_time = request.args.get('start_time', default=None, type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    return _get_recent(count, offset, start_time, user_token, remote_addr)


@app.route('/api/v2/recent')
def get_recent_v2():
    # deprecated
    count = request.args.get('count', default=3, type=int)
    offset = request.args.get('offset', default=0, type=int)
    start_time = request.args.get('start_time', default=None, type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    return _get_recent(
        count, offset, start_time, user_token, remote_addr, version='v2')


def _get_home_timeline(
        user: neotter_user.NeotterUser, from_id: int, count: int):
    neotter_user.extend_expiration(user.id)
    return api.v2.response.get_home_timeline(user, from_id, count)


@app.route('/api/v2/home-timeline')
def get_home_timeline():
    count = request.args.get('count', default=3, type=int)
    from_id = request.args.get('from_id', default=None, type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    try:
        user = _get_user(user_token, remote_addr)
    except ValueError as e:
        if 'invalid token' in str(e):
            return api.v2.response.get_error_message(
                'Token may be wrong or have expired. Please try re-login.'
                ' / トークンの期限が切れている、もしくは間違っています。'
                '再度ログインをお試しください。')
        else:
            raise e
    return _get_home_timeline(user, from_id, count)


@app.route('/api/v2/status-list')
def get_status_list():
    request_status_id = request.args.get('status_ids', default='', type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    user = _get_user(user_token, remote_addr)
    return api.v2.response.get_status_list(request_status_id, user)


@app.route('/api/v2/user-timeline')
def get_user_timeline():
    twitter_user_id = request.args.get('user_id', default=None, type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    user = _get_user(user_token, remote_addr)
    return api.v2.response.get_user_timeline(user, twitter_user_id)


@app.route('/api/v2/search-result')
def get_search_result():
    search_query = request.args.get('query', default='', type=str)
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    logger.debug(search_query)
    if not search_query:
        raise BadRequest('Error: No search query.')
    user = _get_user(user_token, remote_addr)
    return api.v2.response.get_search_result(user, search_query)


@app.route('/api/v2/neotter-user')
def get_neotter_users():
    user_token = request.args.get('key', default=None, type=str)
    remote_addr = _get_remote_addr(request)
    user = _get_user(user_token, remote_addr)
    return api.v2.response.neotter_user_info(user)


@app.route('/login')
def login():
    try:
        endpoint = oauth.get_authenticate_endpoint()
    except ConnectionError:
        logger.error(traceback.format_exc())
        raise InternalServerError(
            'Failed to access twitter. Please try again later.')
    return render_template(
        'login.html', endpoint=endpoint, title='Neotter login')


@app.route('/api/v2/message', methods=['POST'])
def create_message():
    try:
        message = request.form['message']
        user_token = request.form['key']
        media = request.form.get('media')
        remote_addr = _get_remote_addr(request)
    except BadRequestKeyError:
        logger.error(traceback.format_exc())
        raise BadRequest('Missing parameter')
    if not media:
        media_url_list = []
    else:
        media_url_list = media.split(',')

    user = _get_user(user_token, remote_addr)
    return api.v2.response.create_message(user, message, media_url_list)


@app.route('/api/v2/like', methods=['POST'])
def add_like_reaction():
    try:
        message_id = request.form['message_id']
        user_token = request.form['key']
        remote_addr = _get_remote_addr(request)
    except BadRequestKeyError:
        logger.error(traceback.format_exc())
        raise BadRequest('Missing parameter')

    user = _get_user(user_token, remote_addr)
    return api.v2.response.create_like(user, message_id)


@app.route('/api/v2/retweet', methods=['POST'])
def retweet_tweet():
    try:
        message_id = request.form['message_id']
        user_token = request.form['key']
        remote_addr = _get_remote_addr(request)
    except BadRequestKeyError:
        logger.error(traceback.format_exc())
        raise BadRequest('Missing parameter')

    user = _get_user(user_token, remote_addr)
    return api.v2.response.create_retweet(user, message_id)


@app.route('/register')
def register():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    if not oauth_token:
        return 'Invalid access', 401

    user_data = oauth.get_access_token(oauth_token, oauth_verifier)
    logger.debug(user_data)
    user_dict = {
        'id': user_data['user_id'],
        'name': user_data['screen_name'],
        'access_key': crypt.encrypt(user_data['oauth_token']),
        'access_secret': crypt.encrypt(user_data['oauth_token_secret']),
        'client': 'twitter',
        'remote_addr': crypt.encrypt(_get_remote_addr(request))
    }

    new_session_info = generate_new_session()
    user_dict.update(new_session_info)

    try:
        neotter_user.register(user_dict)
    except ValueError as e:
        raise InternalServerError(str(e))
    session_id = new_session_info['session_id']
    session['session_id'] = session_id
    session['name'] = user_data['screen_name']
    logger.debug(session_id)
    return redirect(url_for('user_page'))


@app.route('/user-page')
def user_page():
    if 'session_id' in session and validate_session_id(session['session_id']):
        user_data = neotter_user.get_by_session(session['session_id'])
    else:
        user_data = None
    if not user_data:
        return redirect(url_for('login'))
    user = {
        'name': user_data.name,
        'token': user_data.token
    }
    return render_template(
        'user-page.html', user=user, title='Neotter user page')


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['ja', 'ja_JP', 'en'])


@app.route('/health')
def healthcheck():
    return 'OK'


def _error_notification(request):
    remote_addr = _get_remote_addr(request)
    error_log = f'`{request.url}`\n{remote_addr}\n{traceback.format_exc()}'
    notification.send_message(error_log)


@app.errorhandler(ValueError)
def handle_value_error(e: ValueError):
    _error_notification(request)
    return str(e), 400


@app.errorhandler(InternalServerError)
def handle_server_error(e: InternalServerError):
    _error_notification(request)
    return str(e.get_description())


@app.errorhandler(BadRequest)
def handle_badrequest(e: BadRequest):
    _error_notification(request)
    return str(e.get_description())


if __name__ == '__main__':
    args = get_arguments()
    logging_config(args.debug)

    secret_key = os.getenv('FLASK_SESSION_SECRET', None)
    if not secret_key:
        logger.error('Please set FLASK_SESSION_SECRET')
        sys.exit(1)
    app.secret_key = secret_key

    run_args = {
        'port': args.port,
        'host': args.host,
        'debug': args.debug,
    }
    app.run(**run_args)
