from . import auth
from flask import render_template,redirect,url_for,flash,request
from .forms import RegistrationForm,LoginForm
from .. import db
from ..models import User
from flask_login import login_user,logout_user,login_required
from werkzeug.security import check_password_hash
from flask_mail import Message

@auth.route('/login',methods = ['POST','GET'])
def login():
    login_form = LoginForm()
    title = 'authentication for the pitch'
    if login_form.validate_on_submit():
        user = User.query.filter_by(email = login_form.email.data).first()
        if user == None:
            flash('Invalid username or password')
            return render_template("auth/login.html",login_form = login_form,title = title)
        is_correct_password = check_password_hash(user.password_hash,login_form.password.data)
        if is_correct_password == False:
            flash('Invalid username or password')
            return render_template("auth/login.html",login_form = login_form,title = title)
        else:
            login_user(user,remember=login_form.remember.data)
            return redirect(request.args.get('next') or url_for('main.index'))
    
    return render_template('auth/login.html',login_form = login_form,title = title)


@auth.route('/registration', methods = ['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username = form.username.data,email = form.email.data,password = form.password.data)
        db.session.add(user)
        db.session.commit()
        try:
            message = Message("Hello Welcome to the pitch",sender=("The Pitch","devnyota254@gmail.com"),recipients=[form.email.data])
            mail.send(message)
        except Exception as e:
            print("mail not sent")
        return redirect(url_for('auth.login'))
    title = 'New Account Registration'
    return render_template('auth/registration.html',title = title,registration_form = form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))