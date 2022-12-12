from flask import render_template
from . import auth
from flask import render_template,redirect,url_for, flash,request
from flask_login import login_user,logout_user,login_required
from ..models import User
from .forms import LoginForm,RegistrationForm
from flask_login import current_user
from .. import db
from ..email import mail_message

@auth.route('/signup', methods=['POST','GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email = form.email.data, username = form.username.data,password = form.password.data)
        db.session.add(user)
        db.session.commit()
        mail_message('Welcome to lastest Pitches','email/welcome_subscriber',user.email,user=user)
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
        title = "New Account"
    return render_template('admin/register.html',registration_form = form) 


@auth.route('/login', methods=['POST','GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = User.query.filter_by(email = login_form.email.data).first()
        if user is not None and user.verify_password(login_form.password.data):
            login_user(user,login_form.remember.data)
            return redirect(request.args.get('next') or url_for('main.index'))

        flash('Invalid username or Password')

    title = "Pitch login"
    return render_template('admin/login.html',form = login_form,title=title)
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('you are logout','success')
    return redirect(url_for('auth.login'))    