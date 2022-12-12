from flask import render_template,redirect,url_for,request,flash
from . import auth
from ..models import User
from .. import db
from flask_login import login_user,logout_user,login_required
from .forms import RegistrationForm,LoginForm
from ..email import email_message

@auth.route('/register',methods=["GET","POST"])
def register():

    '''
    views function returns the register template and its contents
    '''
    register_form = RegistrationForm()

    if register_form.validate_on_submit():
        user = User(email=register_form.email.data,username=register_form.username.data,password=register_form.password.data)

        db.session.add(user)
        db.session.commit()

        email_message('Welcome To Our Blogging Community','email/welcome_user',user.email, user=user)

        return redirect(url_for('.login'))

        title = 'New Account'

    return render_template("auth/register.html", register_form=register_form)

@auth.route('/login', methods=["GET","POST"])
def login():

    '''
    view function renders template that contains login form
    '''
    login_form = LoginForm()

    if login_form.validate_on_submit():
        user=User.query.filter_by(email=login_form.email.data).first()

        if user is not None and user.verify_password(login_form.password.data):
            login_user(user,login_form.remember.data)
            return redirect(url_for('main.index'))
        flash('Invalid password or username')
    
    title = "Login"

    return render_template('auth/login.html',login_form=login_form,title=title)

@auth.route('/logout')
@login_required
def logout():

    '''
    view function logs out authenticated user
    '''
    logout_user()
    return redirect(url_for('main.index'))

