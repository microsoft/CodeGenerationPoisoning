# -*- coding: utf-8 -*-
"""
Accounts
####################

*Module* ``project.user.account``


This module defines routes to manage accounts of users.

"""

from flask import render_template, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from . import user_app
from .forms import LoginForm, RegisterForm
from .. import db
from ..models import User

# User - Login
@user_app.route('/login', methods=['GET','POST'])
def login():
	"""
	Manage a user login within the user system at ``/user/login``.
	
	Returns:
		user profile page at ``/user/<some_name>``, if account is valid.
	
	Error:
		Error message emerges if there is invalid username or password.
		
	"""
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		
		login_user(user, remember=form.remember.data)
		return redirect(url_for('user.profile', some_name=user.username))
		
	return render_template('user/login.html', form = form)


# User - Registration
@user_app.route('/signup', methods=['GET','POST'])
def signup():
	"""
	Manage signup of a user account within the user system at ``/user/signup``.

	Returns:
		user homepage if valid account is created.
	
	Error:
		Error message emerges if there is invalid username or email.
		
	"""
	form = RegisterForm()
	if form.validate_on_submit(): 
		new_user = User(username=form.username.data, email=form.email.data, 
						password=form.password.data) 
		db.session.add(new_user)
		db.session.commit()

		flash(u'New user has been created', 'new_user')
		return redirect(url_for('user.main'))
		
	return render_template('user/signup.html', form = form)


# User - Logout
@user_app.route('/logout')
@login_required
def logout():
	"""
	Manage an account logout at ``/user/logout``.
	
	Returns:
		User Homepage at ``/user``.
	
	Error:
		Error message emerges if there is no currently logged in user.
	"""
	logout_user()
	flash(u'You have logged out!', 'new_user')
	return redirect(url_for('user.main'))
