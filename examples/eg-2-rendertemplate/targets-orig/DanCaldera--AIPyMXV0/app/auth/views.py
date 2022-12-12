from flask import render_template, session, redirect, url_for, flash # pylint: disable=import-error
from flask_login import login_user, login_required, logout_user # pylint: disable=import-error
from werkzeug.security import generate_password_hash, check_password_hash # pylint: disable=import-error

from app.forms import LoginForm
from app.firestore_service import get_user, user_put # pylint: disable=no-name-in-module
from app.models import UserModel, UserData

from . import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    context = {
        'login_form': login_form
    }
    if login_form.validate_on_submit():
        username = login_form.username.data
        password = login_form.password.data

        user_doc = get_user(username)

        if user_doc.to_dict() is not None:

            if check_password_hash(user_doc.to_dict()['password'], password):
                user_data = UserData(username,password)
                user = UserModel(user_data)

                login_user(user)

                flash('Bienvenido de nuevo')

                redirect(url_for('hello'))
            else:
                flash('La información no coincide')
        else:
            flash('El usuario no existe')

        return redirect(url_for('index'))

    return render_template('login.html', **context)

@auth.route('signup', methods=['GET', 'POST'])
def signup():
    signup_form = LoginForm()
    context = {
        'signup_form': signup_form
    }

    if signup_form.validate_on_submit():
        username = signup_form.username.data
        password = signup_form.password.data

        user_doc = get_user(username)

        if user_doc.to_dict() is None:
            password_hash = generate_password_hash(password)
            user_data = UserData(username, password_hash)
            user_put(user_data)

            user = UserModel(user_data)

            login_user(user)

            flash('Bienvenido!')

            return redirect(url_for('hello'))

        else:
            flash('El usario existe!')

    return render_template('signup.html', **context)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Regresa pronto')

    return redirect(url_for('auth.login'))