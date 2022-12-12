"""View utilities."""

from .notifications import notifications

from functools import wraps
from flask_socketio import SocketIO
from flask_login import AnonymousUserMixin
from flask import url_for as flask_url_for
from flask import render_template
from flask import request
from flask import g
from flask import current_app

import flask_login

login_manager = flask_login.LoginManager()
socketio = SocketIO(async_mode='eventlet')


# Anonymous User definition
class Anonymous(AnonymousUserMixin):
    """The anonymous user object class."""

    def can(self, *permission):
        """The anonymous user cannot do anything."""
        return False

login_manager.anonymous_user = Anonymous


def current_user():
    """Return currently-logged-in user."""
    return flask_login.current_user


def render(template: str, **kwargs) -> str:
    """Render with settings."""
    for k, v in current_app.config.items():
        kwargs.setdefault('app_config_%s' % k, v)
    return render_template(
        template,
        banner_message=notifications.get(
            int(request.args.get('notification', None) or -1), None),
        request=request,
        logout=request.args.get('logout', False),
        the_url=url_for,
        current_url=current_url,
        **kwargs)


def anonymous_required(f):
    """Decorator for views that require anonymous users (e.g., sign in)."""
    from .models import User

    @wraps(f)
    def decorator(*args, **kwargs):
        user = flask_login.current_user
        if user.is_authenticated:
            return User.get_home(user)
        return f(*args, **kwargs)
    return decorator


def requires(*permissions) -> str:
    """Decorator for views, restricting access to the roles listed."""
    from quupod.queue.views import render_queue

    def wrap(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            user = flask_login.current_user
            if not all(user.can(perm) for perm in permissions):
                return render_queue(
                    'error.html',
                    message='Permission Denied.',
                    action='Home',
                    url=url_for('queue.home'))
            return f(*args, **kwargs)
        return decorator
    return wrap


def login_required_else(message: str):
    """If user is not logged in, prompt for login with the provided message."""
    def wrap(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            if not current_user().is_authenticated:
                return render(
                    'confirm.html',
                    title='Login Required',
                    message=message)
            return f(*args, **kwargs)
        return decorator
    return wrap


def strip_subdomain(string):
    """Strip subdomain prefix if applicable."""
    if '/subdomain' not in request.path or not getattr(g, 'queue', None):
        return string
    string = string.replace('/subdomain', '')
    if '/%s/' % g.queue.url in string:
        string = string.replace('/%s/' % g.queue.url, '/', 1)
    return string


def current_url():
    """Return current URL."""
    return strip_subdomain(request.path)


def url_for(*args, **kwargs):
    """Special url function for subdomain websites."""
    return strip_subdomain(flask_url_for(*args, **kwargs))


##################
# ERROR HANDLERS #
##################

def standard_error(error):
    """Show error page."""
    return render(
        'error.html',
        back=current_app.config['DOMAIN'],
        code=error.code,
        title='Oops.',
        message=error.description,
        url=current_app.config['DOMAIN'],
        action='Return to homepage?'), error.code


def error_not_found(error):
    """Show custom 404 page if page not found."""
    return standard_error(
        ApplicationException('Oops.', 'This page doesn\'t exist!', 404))


def error_server(error):
    """Show custom 500 page if uncaught server exception occurs."""
    from .models import db

    db.session.rollback()
    return render_template(
        '500.html',
        domain=current_app.config['DOMAIN'],
        title='500. Hurr.',
        code=500,
        message='Sorry. Here is the error: <br><code>%s</code><br> Please file'
        ' an issue on the <a '
        'href="https://github.com/alvinwan/quupod/issues">Github issues '
        'page</a>, with the above code if it has not already been submitted.'
        % str(error)), 500
