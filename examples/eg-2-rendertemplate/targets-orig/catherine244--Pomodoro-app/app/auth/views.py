from app import app, db
from .models import Member, Todos, TimerDetails, Feedbacks
from forms import LoginForm, RegisterForm
from flask import render_template, flash, redirect, url_for, session, logging, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import logging

# initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
	return Member.query.get(int(user_id))

# Home page
@main.route('/')
def index():	
	return render_template('home.html')




# Login page
@main.route('/login', methods=["GET", "POST"])
def login():
	form = LoginForm()

	if form.validate_on_submit():
		member = Member.query.filter_by(username=form.username.data).first()
		if member:
			if check_password_hash(member.password, form.password.data):
				login_user(member, remember=form.remember.data)
				session['logged_in'] = True
				return redirect(url_for('pomodoro'))
		else:
			flash('Incorrect username or password. Please try again.', 'danger')

	return render_template('login.html',form=form)


# user registration page
@main.route('/register', methods=["GET", "POST"])
def register():
	form = RegisterForm()

	if form.validate_on_submit():
		# check if username already exists
		existingUser = Member.query.filter_by(username=form.username.data).first()
		if existingUser:
			flash('Username already exists. Please enter a different username.', 'danger')
			return render_template('register.html',form=form)
		else:
			hashed_password = generate_password_hash(form.password.data, method='sha256')
			new_member = Member(username=form.username.data, password=hashed_password, email=form.email.data)
			db.session.add(new_member)
			db.session.commit()
			session['registrationRedirect'] = True
			return redirect(url_for('login'))
	else:
		return render_template('register.html',form=form)


# logout user
@main.route('/logout')
@login_required
def logout():
	session['logged_in'] = False
	logout_user()
	return redirect(url_for('index'))


