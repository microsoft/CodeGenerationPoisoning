from faker import Faker
from flask import render_template, redirect, url_for, Blueprint, request, jsonify, flash
from flask_login import login_user, logout_user, login_required, current_user
from wtforms import meta

from todoism.blueprints.forms import LoginForm, RegisterForm, ItemForm
from todoism.extensions import db
from todoism.models import User, Item

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def homepage():
    return render_template('index.html', title="Welcome")


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            return redirect(url_for('todo.calender'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html', form=form, title='Log in')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have successfully been logged out.')

    return redirect(url_for('auth.login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        print("validate ture")
        user = User(username=form.username.data, password=form.password.data)

        db.session.add(user)
        db.session.commit()
        flash('You have successfully registered! You may now login.')
        print("commit")
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form, title='sign up')
