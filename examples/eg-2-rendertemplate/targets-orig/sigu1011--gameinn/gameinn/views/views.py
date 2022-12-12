from flask import request, redirect, url_for, render_template, flash, session
from gameinn import app
from functools import wraps
from gameinn.utils.utils import is_valid
from gameinn.models.users import User
import bcrypt


def login_required(view):
    @wraps(view)
    def inner(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return inner


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not is_valid(request.form['username']):
            flash('The username you have entered is invalid.')
            return render_template('login.html')
        if not is_valid(request.form['password']):
            flash('The password you have entered is invalid.')
            return render_template('login.html')

        user = User.query.filter_by(username=request.form['username']).first()

        if user is None:
            flash('The username you have entered does not match any account.')
            return render_template('login.html')
        if bcrypt.hashpw(request.form['password'].encode(), user.salt.encode()).decode() != user.password:
            flash('The password you have entered is incorrect.')
            return render_template('login.html')
        else:
            session['logged_in'] = True
            session['user_id'] = user.id
            flash('Signed in.')
            return redirect(url_for('activity.show_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    flash('Signed out.')
    return redirect(url_for('activity.show_dashboard'))


@app.errorhandler(404)
def non_existant_route(error):
    return redirect(url_for('login'))
