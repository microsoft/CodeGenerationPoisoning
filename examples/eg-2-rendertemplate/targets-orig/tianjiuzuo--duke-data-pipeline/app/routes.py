from flask import render_template, flash, redirect, url_for, request, send_file, send_from_directory, current_app
from flask_login import login_user, logout_user, current_user, login_required
from flask_user import roles_required
from sqlalchemy.sql.operators import as_
from werkzeug.urls import url_parse
from app import app, db, mail
from app.forms import LoginForm, RegistrationForm, CollectionForm, ChangePasswordForm
from werkzeug.security import generate_password_hash
from app.models import User, Update, Request, Role
import sqlite3, csv, os
from flask_mail import Message
from sqlalchemy.sql import text
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil import relativedelta

def emailReminders():
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_date = tomorrow.strftime('%d')
    if tomorrow_date == "25":
        with app.app_context():
           msg = Message("Submisson Reminder",
                  sender = os.environ.get('EMAIL'),
                  recipients=[os.environ.get('EMAIL')])
                #  sender = 'demo@gmail.com',
                #  recipients = ['qixuankhoo@gmail.com'])
           msg.body = "This is a reminder to submit your shelter's data. The window for submission opens tomorrow."
           mail.send(msg)
    
    week = datetime.now() + timedelta(days=7)
    week_date = week.strftime('%d')
    if week_date == "31":
        with app.app_context():
            msg = Message("Submisson Reminder",
                  sender = os.environ.get('EMAIL'),
                  recipients=[os.environ.get('EMAIL')])
                #  sender = 'demo@gmail.com',
                #  recipients = ['qixuankhoo@gmail.com'])

            msg.body = "This is a reminder to submit your shelter's data. The window for submission opens next week."
            mail.send(msg)

scheduler = BackgroundScheduler()
scheduler.add_job(func=emailReminders, trigger="interval", days=1)
scheduler.start()


@app.route('/')
@app.route('/index')
@login_required
def index():
    posts = [{
        'author': {
            'username': 'John'
        },
        'body': 'Beautiful day in Portland!'
    }, {
        'author': {
            'username': 'Susan'
        },
        'body': 'The Avengers movie was so cool!'
    }]
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name == 'admin' or current_user.role.name == 'policymaker':
        return redirect(url_for('admin_dashboard'))

    return render_template('index.html', title='Home', posts=posts, template='base.html')
    


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/changePassword', methods=['GET', 'POST'])
@login_required
def changePassword():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=current_user.username).first()
        user.password_hash = generate_password_hash(form.password.data)
        user.pwPrompted = True
        db.session.commit()
        flash('Password Updated!', "error")
        return redirect(url_for('index'))
    if not current_user.pwPrompted and request.method == 'GET':
        flash("You MUST change your password to access other pages","error")
    return render_template('changePassword.html', title='Change Password', form=form, template=admin_template_validation())

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name == 'shelter':
        return redirect(url_for('index'))

    form = RegistrationForm()
    available_roles = [role.name for role in Role.query.all()]

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, organization=form.organization.data, county=form.county.data)
        role = Role.query.filter_by(name=form.role.data).first()
        user.role = role
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form, roles = available_roles, template = "base-admin.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/collectionform', methods=['GET', 'POST'])
@login_required
def collectionform():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    form = CollectionForm()
    if form.validate_on_submit():
        submission = Update(user_id=current_user.get_id(),
                            number_of_victims=form.number_of_victims.data,
                            capacity=form.capacity.data)
        db.session.add(submission)
        db.session.commit()
        #send_mail()

        nextmonth = datetime.today() + relativedelta.relativedelta(months=1)
        nextmonth = nextmonth.strftime('%B') + " 1st"
        return render_template('confirmation.html', nextmonth = nextmonth)

        flash('Form Completed!')
    return render_template('collectionform.html',
                           title='Collection Form',
                           user=current_user,
                           form=form)


@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name in ['admin', 'policymaker']:
        if current_user.role.name == 'admin': 
            update_fields = ['id', 'user_id', 'number_of_victims', 'capacity', 'timestamp']
            user_fields = ['organization']
            template = 'admin_dashboard.html'
            
        if current_user.role.name == 'policymaker':
            update_fields = ['id', 'user_id', 'number_of_victims', 'capacity', 'timestamp']
            user_fields = ['organization']
            template = 'policymaker_dashboard.html'

        # Sort --> Filter --> Paginate            

        filter_by = request.args.get('filter_by')
        filter = request.args.get('filter')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order')
        sort_query = sort_by + ' ' + sort_order if sort_by else None
        filtered = False

        if db.session.query(Update).first() == None:
            return render_template(template,
                                title='Admin Dashboard',
                                update_fields=update_fields,
                                user_fields=user_fields,
                                sort_by=sort_by,
                                sort_order=sort_order,
                                filtered=filtered,
                                start='',
                                end='',
                                # filter_by=filter_by,
                                # filters=filters,
                                updates=None)
            
        # Sort query
        if sort_query:
            if sort_by in user_fields:
                updates = db.session.query(Update).join(User).order_by(
                    getattr(User, sort_by).desc()) if sort_order == 'desc' else db.session.query(
                        Update).join(User).order_by(
                            getattr(User, sort_by).asc())
            else:
                updates = Update.query.order_by(text(sort_query))
        else:
            updates = Update.query

        #Filter query
        # Create fields and filters
        filters = {}

        for field in update_fields:
            if field not in filters:
                filters[field] = [x[0] for x in db.session.query(getattr(Update, field).distinct()).all()]

        for field in user_fields:
            if field not in filters:
                filters[field] = [x[0] for x in db.session.query(getattr(User, field).distinct()).all()]

        #Timestamp
        start = request.args.get('start_date', '')
        end = request.args.get('end_date', '')

        if not start:
            updates = updates.filter(func.DATE(Update.timestamp) >= db.session.query(func.min(Update.timestamp)).one()[0].date())
        else:
            updates = updates.filter(func.DATE(Update.timestamp) >= datetime.strptime(start, '%m/%d/%Y').date())
            filtered = True

        if not end:
            updates = updates.filter(func.DATE(Update.timestamp) <= db.session.query(func.max(Update.timestamp)).one()[0].date())
        else:
            updates = updates.filter(func.DATE(Update.timestamp) <= datetime.strptime(end, '%m/%d/%Y').date())
            filtered = True

        #Paginate
        updates_paginated = updates.paginate(per_page=per_page, page=page)

        if request.method == 'GET':
            return render_template(template,
                                title='Admin Dashboard',
                                update_fields=update_fields,
                                user_fields=user_fields,
                                sort_by=sort_by,
                                sort_order=sort_order,
                                filtered=filtered,
                                start=start,
                                end=end,
                                # filter_by=filter_by,
                                # filters=filters,
                                updates=updates_paginated)
            
        if request.method == 'POST':
            post_data = request.get_json()

            #Timestamp
            start = post_data['start_date']
            end = post_data['end_date']

            if not start:
                updates = updates.filter(func.DATE(Update.timestamp) >= db.session.query(func.min(Update.timestamp)).one()[0].date())
            else:
                updates = updates.filter(func.DATE(Update.timestamp) >= datetime.strptime(start, '%m/%d/%Y').date())
                filtered = True

            if not end:
                updates = updates.filter(func.DATE(Update.timestamp) <= db.session.query(func.max(Update.timestamp)).one()[0].date())
            else:
                updates = updates.filter(func.DATE(Update.timestamp) <= datetime.strptime(end, '%m/%d/%Y').date())

            data = []
            csvpath = os.getcwd()
            csvpath = csvpath.split('app')[0]
            csvpath = csvpath + '/app/static/csv/'
            csvheader = []

            for update in updates:
                new_row = []
                for field in update_fields:
                    if post_data[field]:
                        new_row.append(getattr(update,field))
                        if field not in csvheader:
                            csvheader.append(field)

                for field in user_fields:
                    if post_data[field]:
                        new_row.append(getattr(update.user,field))
                        if field not in csvheader:
                            csvheader.append(field)

                data.append(new_row)

            with open(csvpath+'data.csv', 'w') as demo_file:
                write = csv.writer(demo_file)
                write.writerow(csvheader)
                write.writerows(data)
            

            return render_template(template,
                                title='Admin Dashboard',
                                update_fields=update_fields,
                                user_fields=user_fields,
                                sort_by=sort_by,
                                sort_order=sort_order,
                                filtered=filtered,
                                start=start,
                                end=end,
                                # filter_by=filter_by,
                                # filters=filters,
                                updates=updates_paginated)

    else:
        return render_template('404.html')

@app.route('/download_csv', methods=['GET'])
def download_csv():
    path = 'static/csv/'
    return send_file(path+'data.csv', as_attachment=True)

@app.route('/admin_profiles', methods=['GET', 'POST'])
@login_required
def admin_profiles():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name == 'admin':
        if request.method == 'GET':
            users = User.query.all()
            user_fields = ['id', 'username', 'email', 'role', 'organization']
            update_fields = ['id', 'user_id', 'number_of_victims', 'capacity', 'timestamp']

            return render_template('profile_page.html', user_fields=user_fields, users=users)

    else:
        return render_template('404.html')

@app.route('/map', methods=['GET', 'POST'])
@login_required
def map():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name in ['policymaker', 'admin']:
        return render_template('map.html')

    else:
        return render_template('404.html')

@app.route('/admin_profiles/delete/<int:id>')
@login_required
def delete_profile(id):
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))

    if current_user.role.name == 'admin':
        user_to_delete = User.query.get(id)
        db.session.delete(user_to_delete)
        db.session.commit()

        return redirect(url_for('admin_profiles'))

    else:
        return render_template('404.html')


@app.route('/research')
@login_required
def research():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))
    return render_template('research.html', title='Research', template=admin_template_validation())


@app.route('/disclosure')
@login_required
def disclosure():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))
    return render_template('disclosure.html', title='Disclosure', template=admin_template_validation())


@app.route('/team')
@login_required
def team():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))
    return render_template('team.html', title='Team', template=admin_template_validation())


@app.route('/contact_us')
@login_required
def contact_us():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))
    return render_template('contact.html', title='Contact Us', template=admin_template_validation())


@app.route('/terms_and_privacy')
@login_required
def terms_and_privacy():
    if not current_user.pwPrompted:
        return redirect(url_for('changePassword'))
    return render_template('terms_and_privacy.html',
                           title='Please read to continue', template=admin_template_validation())

def admin_template_validation():
    if current_user.role.name == 'admin':
        return 'base-admin.html'
    return 'base.html'

def send_mail():
    msg = Message("Submisson Confirmation",
                #   sender = os.environ.get('EMAIL'),
                #   recipients=[os.environ.get('EMAIL')]
                  sender = 'demo@gmail.com',
                  recipients = [os.environ.get('EMAIL')])

    nextmonth = datetime.today() + relativedelta.relativedelta(months=1)
    nextmonth = nextmonth.strftime('%B') + " 1st"
    msg.body = "Thank you for your submission. The next collection date is " + nextmonth + "."
    mail.send(msg)

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())