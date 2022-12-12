from logging import getLogger

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from werkzeug.http import parse_authorization_header

from observatory.forms.user import LoginForm
from observatory.models.user import User
from observatory.start.extensions import LOGIN_MANAGER

BLUEPRINT_USER = Blueprint('user', __name__)
LOG = getLogger(__name__)


@LOGIN_MANAGER.user_loader
def user_loader(prime):
    return User.by_prime(prime)


@LOGIN_MANAGER.request_loader
def request_loader(req):
    auth = parse_authorization_header(req.headers.get('authorization'))
    if auth is not None:
        if auth.username is not None and auth.password is not None:
            user = User.by_username(auth.username)
            if user is not None and user.check_password(auth.password):
                return user
    return None


@BLUEPRINT_USER.route('/user/logout')
@login_required
def logout():
    LOG.info('logout for user "%s"', current_user.username)
    logout_user()
    flash('See you soon!', 'dark')
    return redirect(url_for('main.index'))


@BLUEPRINT_USER.route('/user/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if request.method == 'POST' and form.validate_on_submit():
        user = form.action()
        if user is not None:
            flash(f'Welcome {user.username}!', 'dark')
            return redirect(request.args.get('next') or url_for('user.home'))

    return render_template(
        'page_form.html', title='Tickets, please!', form=form
    )


@BLUEPRINT_USER.route('/user')
@login_required
def home():
    return render_template('user/home.html', title='Welcome home!')
