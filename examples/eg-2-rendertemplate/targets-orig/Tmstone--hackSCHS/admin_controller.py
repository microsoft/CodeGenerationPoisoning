''' Admin controller '''
from flask import render_template, redirect, request, session, flash
from config import db, datetime
from admin_model import Organizer
from models import *

##admin routes##
#admin dashboard
def admin():
    if 'admin_id' not in session:
        return redirect('/')
    admin = session['first_name']
    attendees = User.get_all_users()
    schools = School.get_all()
    parents = Parent.get_all()
    #gender = Gender.by_gender(id)
    print('*'*80)
    print(admin)
    print(attendees)
    print(schools)
    print(parents)
    return render_template('admindash.html',
    name = admin, hackers = attendees, schools = schools, parents = parents
    )

def pi():
    return render_template('login.html')

#log in admin
def admin_in(): 
    admin = Organizer.validate_login(request.form)
    if admin:
        session['admin_id'] = admin.id
        session['first_name'] = admin.first_name
        print('*'*90)
        print(session['admin_id'], session['first_name'])
        return redirect('/admindash')
    flash('Email and password do not match')
    return redirect('/')

def admin_account():
    if 'admin_id' not in session:
        return redirect('/')
    admin = session['first_name']
    user = Organizer.get(session['admin_id'])
    print('*'*90)
    print(user)
    return render_template('adminacc.html', name = admin, user = user
    )
def attendee(id):
    if 'admin_id' not in session:
        return redirect('/')
    admin = session['first_name']
    user = User.get(id)
    parent = Parent.get_parent(user.id)
    school = School.get_school(user.id)
    bonus = Bonus.get_bonus(user.id)
    gender = Gender.get_gender(user.id)
    race = Ethnicity.get_ethnicity(user.id)
    grad = Graduation.get_graduation(user.id)
    goal = Goal.get_goal(user.id)
    return render_template('attendee.html',
    name = admin, hacker = user, contact = parent,
    sdata = school, extra = bonus, gender = gender,
    race = race, year = grad, hack = goal
    )
#pull all records

def admin_logout():
    session.clear()
    return redirect('/')