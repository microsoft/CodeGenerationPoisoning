from flask import render_template, session, request, redirect, url_for, flash
from functools import wraps
from dental import app, db, bcrypt
from .forms import RegistrationForm, LoginForm
from .models import User
from dental.products.models import manufacturer_product, lab_product
from .lab import lab
from .clinic import clinic
from .manufacturer import manufacturer
import gc

@app.route('/')
def homepage():
    return redirect(url_for("login"))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        hash_password = bcrypt.generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data,
                    password=hash_password, role_id=form.role_id.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Welcome {form.username.data}. Thank you for registering','success')
        return redirect(url_for('login'))
    return render_template('user/register.html', form=form, title="Registration page")

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        user = User.query.filter_by(username = form.username.data).first()
        if user == User.query.filter_by(username = form.username.data, role_id = '1').first():
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                session['logged_in'] = True
                session['username']= form.username.data
                flash(f'Welcome {form.username .data}. You are logged in successfully.', 'success')
                return redirect(request.args.get('next') or url_for('clinic'))
            else:
                flash('Wrong credentials. Please try again', 'danger')

        elif user == User.query.filter_by(username = form.username.data, role_id = '2').first():
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                session['logged_in'] = True
                session['username']= form.username.data
                flash(f'Welcome {form.username .data}. You are logged in successfully.', 'success')
                return redirect(request.args.get('next') or url_for('lab'))
            else:
                flash('Wrong credentials. Please try again', 'danger')

        elif user == User.query.filter_by(username = form.username.data, role_id = '3').first():
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                session['logged_in'] = True
                session['username']= form.username.data
                flash(f'Welcome {form.username .data}. You are logged in successfully.', 'success')
                return redirect(request.args.get('next') or url_for('manufacturer'))
            else:
                flash('Wrong credentials. Please try again', 'danger')
        else:
                error = "Invalid credentials, try again."
    gc.collect()
    return render_template('user/login.html', form=form, title='Login Page')

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login_page'))
    return wrap

@app.route("/logout/")
@login_required
def logout():
    session.clear()
    flash("You have been logged out!")
    gc.collect()
    return redirect(url_for('homepage'))
