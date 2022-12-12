from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, SignupForm
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():

    # dont need to log the user in if theyre already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()

    #returns true if request method is POST, GET if false
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        # if credentials are invalid then prompt for correct credentials
        if user is None or not user.check_password(form.password.data):
            flash('Invalid Username or password')
            return redirect(url_for('auth.login'))

        #actually does the user login
        login_user(user, remember=form.remember_me.data)
        

        #returns the user to the page they tried to access if they tried to
        #   access a page that requires authentication
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.home') 
        return redirect(next_page) 
    
    return render_template('auth/login.html', title ='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home')) #TODO this should redirect to /home

    form = SignupForm()

    #returns true if request method is POST, GET if false
    if form.validate_on_submit():    

        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user) # ignore these errors
        db.session.commit()
        flash('Successfully registered!')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', title = 'Sign up', form=form)

