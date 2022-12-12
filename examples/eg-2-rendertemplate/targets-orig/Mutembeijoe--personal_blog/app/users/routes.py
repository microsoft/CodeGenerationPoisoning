from flask import Blueprint, render_template, flash, redirect, url_for,request
from app.users.forms import RegistrationForm, LoginForm, UpdateUserForm
from app import bcrypt,db
from app.models import User
from flask_login import login_user,current_user,logout_user, login_required
from app.email import mail_message

from app.users.utils import save_picture

users = Blueprint('users', __name__)

@users.route('/register', methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        mail_message("Welcome to the flask Blog","email/welcome_user",user.email,user=user)
        flash(f'Account was successfully created, you can now login!', "success")
        return redirect(url_for('users.login'))
    return render_template('register.html', form = form )

@users.route("/login", methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Invalid email or password', 'danger')
    return render_template('login.html', form = form)

@users.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route('/account', methods = ['GET','POST'] )
@login_required
def account():
    form = UpdateUserForm()
    avatar = url_for('static', filename=f'profile_pics/{current_user.image_file}')
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash(f'Account credentials were successfully updated', "success")
        return redirect(url_for('users.account'))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', avatar = avatar, form=form)