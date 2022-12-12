from flask import render_template, redirect, request, session, flash
from config import db, datetime
from models import *

### Controller Functions ###
#render index
def index():
    return render_template('index.html')

#register form
def register():
    return render_template('register.html')

#Add new user
def new_user():
    errors = User.validate_attendee(request.form)
    if errors:
        for error in errors:
            flash(error)
        return redirect('/register')
    user = User.add_user(request.form)
    session['user_id'] = user.id
    return redirect('/dashboard')

#login user
def login():
    user = User.validate_login(request.form)
    if user:
        session['user_id'] = user.id
        session['first_name'] = user.first_name
        return redirect('/dashboard')
        print('*'*90)
        print(session['user_id'])
    flash('Email and password do not match')
    return redirect('/')

#Adding first name
def first():
    user = User.query.get(session['user_id'])
    print (user)
    return user.first_name

#display dashboard
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user = User.get(session['user_id'])
    user_id = session['user_id']
    session['first_name'] = user.first_name
    details = Parent.get_parent(user_id)
    school = School.get_school(user_id)
    print(details)
    return render_template('dashboard.html',
    user = user, data = details, sdata = school
    )

#display user update page
def account():
    if 'user_id' not in session:
        return redirect('/')
    user = User.get(session['user_id'])
    parent = Parent.get_parent(session['user_id'])
    school = School.get_school(session['user_id'])
    session['first_name'] = user.first_name
    print('*'*90)
    print(session['user_id'])
    print(school)
    return render_template('account.html',
    user = user, contact = parent, sdata = school
    )

#update user
def update():
    if 'user_id' not in session:
        return redirect('/')
    user_id = session['user_id'] 
    errors = []
    errors+=User.validate_name(request.form['first_name'], request.form['last_name'])
    errors+=User.validate_email(request.form['email'])
    errors+=User.validate_phone(request.form['phone'])
    errors+=User.validate_parent(request.form['parent_first'], request.form['parent_last'])
    errors+=User.validate_parent_email(request.form['parent_email'])
    errors+=User.validate_parent_phone(request.form['parent_phone'])
    for error in errors:
        flash(error)
    if not errors:
        update = User.edit_user(user_id, request.form)
        update_parent = Parent.edit_parent(user_id, request.form)
        user = User.get(user_id)
    return redirect('/dashboard')

#logout user
def logout():
    session.clear()
    return redirect('/')