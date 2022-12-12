from flask import Blueprint, redirect, render_template, url_for, flash
from flask_login import login_required, login_user, logout_user
from .forms import LoginForm, RegistrationForm
from ... import db
from ...models import Employee

#Initialize the auth blueprint
auth = Blueprint('auth', __name__, template_folder='templates')

@auth.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        employee = Employee(date_of_first_appointment = form.date_of_first_appointment.data,
                            email = form.email.data,
                            first_name = form.first_name.data,
                            last_name = form.last_name.data,
                            password =form.password.data,
                            date_of_birth = form.date_of_birth.data,
                            next_of_kin = form.next_of_kin.data,
                            educational_qualification = form.educational_qualification.data,
                            address = form.address.data,
                            phone_number = form.phone_number.data,
                            marital_status = form.marital_status.data)
        db.session.add(employee)
        db.session.commit()
        flash("You have succesfully registered")

        return redirect(url_for('auth.login'))

    return render_template('auth/registration.html', form = form, title='Register')

@auth.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Check if employee exists in the database
        employee = Employee.query.filter(Employee.email == form.email.data).first()
        if employee is not None and employee.verify_password(form.password.data):
            login_user(employee)
            if employee.is_admin:
                return redirect(url_for('home.admin_dashboard'))
            else:
                return redirect(url_for('home.dashboard'))
    
        else:
            flash('Invalid Username or Password')

    return render_template('auth/login.html', form = form, title = 'Log In')

@auth.route('/logout', methods= ['GET', 'POST'])
def logout():
    logout_user()
    flash("You have succesfully logged out")
    return redirect(url_for('auth.login'))
