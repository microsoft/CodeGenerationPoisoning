from flask import render_template,redirect,url_for,request,flash
from . import auth
from .forms import LoginForm,RegistrationForm
from .. import db,mail
from ..models import User
from flask_login import login_user,logout_user,login_required
from ..send_mail import mail_message
from flask_mail import Message


@auth.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user,form.remember.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or Password')

    title='Login'
    return render_template('auth/login.html',form=form,title=title)

@auth.route('/register', methods=['GET','POST'])
def register():
    register=RegistrationForm()
    if register.validate_on_submit():
        user=User(username=register.username.data,email=register.email.data,password=register.password.data)
        db.session.add(user)
        db.session.commit()

        # msg=Message('Welcome To Pitch Master', sender='dmbugua66@gmail.com',recipients=['dmbugua@gmail.com'])
        # msg.body='''Hello {{user.username}}
        #         Welcome to Pitch Master
        #         Pitch Master is an interactive platforms where careers are build by guiding and facilitating all neccecities needed to build a person's confidence.'''
        # mail.send(msg)        
        flash('Account successfully created!')
        return redirect(url_for('auth.login'))
        # title="Create Account"
    return render_template('auth/register.html',register=register,title='Create Account')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))