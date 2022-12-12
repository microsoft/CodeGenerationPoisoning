from flask import render_template,redirect,url_for,flash,request
from app.models import User
from .forms import RegistrationForm,LoginForm
from .. import db
from . import auth 
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user
from ..email import mail_message


@auth.route('/register',methods = ["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email= form.email.data, username= form.username.data,pass_secure= generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        
        mail_message("Welcome to PitchSocial","email/welcome_user", user.email, user=user)
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html',registration_form = form)


@auth.route('/login', methods = ["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = User.query.filter_by(email=login_form.email.data).first()
        if user is not None and user.verify_password(login_form.password.data):
            login_user(user,login_form.remember_me)
            return redirect(request.args.get('next') or url_for('main.home'))
        flash('invalid username or password')
    return render_template('auth/login.html', login_form=login_form)



@auth.route('/logout')
def logout():
    logout_user()
    
    return redirect(url_for('main.home'))