from flask import render_template, redirect, url_for, flash, request, current_app
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app import db, game_data
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User


@bp.route('/login', methods=['GET', 'POST'])
def login():
    current_app.logger.info(f"{request.method} Request for login from IP {request.remote_addr} ")
    if current_user.is_authenticated:
        current_app.logger.info(f"Redirecting to main.index, User {current_user.username} already logged in")
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        current_app.logger.debug(f"Login form validated from IP {request.remote_addr}")
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', category='error')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        current_app.logger.debug(f"Login for {user.username} successful, remember me: {form.remember_me.data}")
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        current_app.logger.info(f"Redirecting to {next_page}")
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form, style='signin')


@bp.route('/logout')
def logout():
    current_app.logger.info(f"{request.method} Request for logout from IP {request.remote_addr} ")
    logout_user()
    current_app.logger.debug("User logged out")
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    current_app.logger.info(f"{request.method} Request for register from IP {request.remote_addr} ")
    if current_user.is_authenticated:
        current_app.logger.info(f"Redirecting to main.index, User {current_user.username} already logged in")
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        current_app.logger.debug(f"Registration form validated from IP {request.remote_addr}")
        user = User(username=form.username.data, initial=form.initial.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        userid = User.query.filter_by(username=form.username.data).first_or_404().id
        game_data.newUser(userid)
        current_app.logger.debug(f"New User: id:{userid}, username:{form.username.data}")
        flash('Congratulations, you are now a registered user!', category='success')
        current_app.logger.info("Redirecting to auth.login")
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form, style='signin')
