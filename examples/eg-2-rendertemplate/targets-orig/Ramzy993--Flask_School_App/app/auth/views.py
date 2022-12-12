from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User, UserContact, UserRole, Permission, Student, Staff, Parent
from .forms import LoginForm, RegisterForm, StudentForm, ParentForm, StaffForm
from ..email import send_mail
import time
from .forms import STAFF_OFFSET
from ..picture_handler import add_profile_pic


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('Invalid email or password.')
    return render_template('login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session['email'] = form.email.data.lower()
        session['user_name'] = form.user_name.data.lower()
        session['password'] = form.password.data
        session['user_type'] = form.user_type.data
        return redirect(url_for('auth.register_next'))
    return render_template('register.html', form=form)


@auth.route('/register_next', methods=['GET', 'POST'])
def register_next():
    if session.get('user_type') == 1:
        form = StudentForm()
        permission = Permission.roles['Student']
    elif session.get('user_type') == 2:
        form = ParentForm()
        permission = Permission.roles['Parent']
    else:
        form = StaffForm()
        if session.get('user_type') == 3:
            permission = Permission.roles['Teacher']
        elif session.get('user_type') == 4:
            permission = Permission.roles['Management']
        else:
            permission = Permission.roles['Administrator']

    if form.validate_on_submit():
        user = User(user_name=session.get('user_name'), email=session.get('email'), password=session.get('password'))
        db.session.add(user)
        db.session.commit()

        user_role = UserRole()
        user_role.user_id = user.id
        user_role.add_permissions(permission)

        user_contact = UserContact(mobile_number=form.mobile_number.data, address=form.address.data)
        user_contact.user_id = user.id

        if session.get('user_type') == 1:
            person = Student(first_name=form.first_name.data.lower(), middle_name=form.middle_name.data.lower(),
                             last_name=form.last_name.data.lower(), gender=form.gender.data, religion=form.religion.data,
                             date_of_birth=form.date_of_birth.data, student_class=form.student_class.data)
        elif session.get('user_type') == 2:
            person = Parent(first_name=form.first_name.data.lower(), middle_name=form.middle_name.data.lower(),
                            last_name=form.last_name.data.lower(), gender=form.gender.data, religion=form.religion.data,
                            date_of_birth=form.date_of_birth.data, parent_class=form.parent_class.data)
            student_user = User.query.filter_by(user_name=form.student_username.data).first()
            person.student_id = student_user.id
        else:
            person = Staff(first_name=form.first_name.data.lower(), middle_name=form.middle_name.data.lower(),
                           last_name=form.last_name.data.lower(), gender=form.gender.data, religion=form.religion.data,
                           date_of_birth=form.date_of_birth.data, staff_class=session.get('user_type')-STAFF_OFFSET)

        if form.picture.data:
            user_name = session.get('user_name')
            pic = add_profile_pic(form.picture.data, user_name)
            user_contact.profile_image = pic

        person.user_id = user.id

        db.session.add(user_role)
        db.session.add(user_contact)
        db.session.add(person)
        db.session.commit()

        token = user.generate_confirmation_token()
        send_mail(user.email, 'Confirm Your Account', 'mail/confirm', user=user, token=token)
        flash('A confirmation mail has been sent. Please confirm first.')
        return redirect(url_for('auth.login'))
    return render_template('register_next.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.is_confirmed:
        return redirect(url_for('main.index'))
    elif current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
        time.sleep(3)
        return redirect(url_for('auth.welcome'))
    else:
        flash('The confirmation link is invalid or has expired.')
    return render_template(url_for('mail.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, 'Confirm Your Account',
              'mail/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/welcome')
@login_required
def welcome():
    return render_template('mail/welcome.html', user=current_user.user_name)


@auth.before_app_request
def before_request():
    if current_user.is_authenticated and not current_user.is_confirmed and request.blueprint != 'auth' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.is_confirmed:
        return redirect(url_for('main.index'))
    return render_template('mail/unconfirmed.html')
