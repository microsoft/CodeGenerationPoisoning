from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from passlib.hash import sha256_crypt

from project import db
from project.models import *
from project.users.forms import LoginForm, RegisterForm, UpdateAccountForm,\
                                RequestResetForm, ResetPasswordForm
                                
from project.users.utils import send_reset_email

users = Blueprint('users', __name__)

@users.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST' and form.validate_on_submit():
        default_role = Role.query.filter_by(name='user').first()
        user = User(
            name=form.name.data,
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            roles= [default_role, ]
        )
        db.session.add(user)
        db.session.commit()
        flash('You are successfully registered.', 'success')
        # login_user(user)
        return redirect(url_for('users.login'))
    return render_template('register.html', form=form)


@users.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print(current_user.name)
        return redirect(url_for('main.index'))
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is not None and sha256_crypt.verify(form.password.data, user.password):
                login_user(user)
                next_page = request.args.get('next')
                flash('You are logged in', 'success')
                return redirect(next_page) if next_page else redirect(url_for('main.index'))
            else:
                flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@users.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You are successfully logged out', 'success')
    return redirect(url_for('users.login'))


@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)



@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        password = sha256_crypt.encrypt(str(form.password.data))
        user.password = password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@users.route('/delete', methods=['GET','POST'])
@login_required
def delete_account():
    if current_user.is_authenticated:
        db.session.delete(current_user)
        db.session.commit()
        flash('Your account has been deleted.', 'success')
        return redirect(url_for('users.login'))