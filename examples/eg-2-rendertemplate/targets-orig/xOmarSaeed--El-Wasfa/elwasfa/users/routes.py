from elwasfa.users.forms import RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm
from elwasfa.models import User
from flask import flash, redirect, render_template, request, session, url_for, Blueprint, current_app
from flask_login import login_user, current_user, logout_user, login_required
from elwasfa import mail, db, bcrypt
import os, boto3
from elwasfa.users.utils import save_picture, send_reset_email

users = Blueprint('users', __name__)


@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        default_image = 'https://elwasfa-bucket.s3.eu-central-1.amazonaws.com/profile/default.png'
        user = User(displayname=form.displayname.data, username=form.username.data, email=form.email.data, image_file = default_image, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', form=form)

@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('users.login'))
    return render_template('login.html', form=form)

@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            s3 = boto3.resource('s3')
            pic_name= current_user.image_file.split("/")[-1:]
            key = "profile/" + pic_name[0]
            if key != 'default.png':
                s3.Object('elwasfa-bucket', key).delete()
            current_user.image_file = save_picture(form.picture.data)


            #ex_picture = current_user.image_file
            #picture_file = save_picture(form.picture.data)
            #current_user.image_file = picture_file
            #if ex_picture != 'default.jpg':
            #    os.remove(os.path.join(current_app.root_path, 'static/pictures/profile', ex_picture)) 

        current_user.displayname = form.displayname.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.profile'))
    elif request.method == 'GET':
        form.displayname.data = current_user.displayname
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('profile.html', form=form)

@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        send_reset_email(current_user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('users.profile'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', form=form)


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', form=form)
