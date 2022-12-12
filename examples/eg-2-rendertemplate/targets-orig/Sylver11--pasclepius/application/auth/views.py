from flask import Blueprint, render_template, request, redirect, url_for, flash
from application.db_users import addUser, checkUser
from flask_login import current_user, login_user, logout_user
from application.models import User
import os

auth_bp = Blueprint('auth_bp',__name__, template_folder='templates')


@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    return render_template('auth/login.html', page_title = 'Login')


@auth_bp.route("/login/redirect")
def login_redirect():
    if os.getenv('FLASK_ENV') == 'development':
        if checkUser(os.getenv('TEST_USER_EMAIL')) is None:
            status = addUser(os.getenv('TEST_USER_NAME'),
                    os.getenv('TEST_USER_SURNAME'),
                    os.getenv('TEST_USER_EMAIL'))
            if not status:
                flash('In develop: You do not have an account with us and we were not able to create one for you.')
                return redirect(url_for('auth_bp.login'))
        user = User(os.getenv('TEST_USER_EMAIL'))
        login_user(user)
        return redirect(url_for('home_bp.home'))
    if not request.remote_user:
        flash('No remote user found. Please inform the System Administrato about this incident.')
        return redirect(url_for('auth_bp.login'))
    if checkUser(request.remote_user) is None:
        status = addUser(request.headers.get('oidc-claim-given-name'),
                request.headers.get('oidc-claim-family-name'),
                request.remote_user)
        if not status:
            flash('You do not have an account with us and we were not able to create one for you. Please contact the system administrator')
            return redirect(url_for('auth_bp.login'))
        user = User(request.remote_user)
        login_user(user, remember=True)
        return redirect(url_for('home_bp.setup'))
    user = User(request.remote_user)
    login_user(user, remember=True)
    return redirect(url_for('home_bp.home'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth_bp.login') +
            '/redirect/callback?logout=https%3A%2F%2Fpasclepius.voigts.cloud%2Fauth%2Flogin')
