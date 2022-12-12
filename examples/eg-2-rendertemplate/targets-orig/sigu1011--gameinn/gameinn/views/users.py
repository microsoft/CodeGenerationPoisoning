from flask import request, redirect, url_for, render_template, flash
from gameinn import db
from gameinn.utils.utils import is_valid
from gameinn.models.users import User
from flask import Blueprint

user = Blueprint('user', __name__)


@user.route('/users', methods=['POST'])
def add_user():
    if not is_valid(request.form['username']):
        flash('The username you have entered is invalid.')
        return redirect(url_for('user.new_user'))
    if not is_valid(request.form['password']):
        flash('The password you have entered is invalid.')
        return redirect(url_for('user.new_user'))

    user = User.query.filter_by(username=request.form['username']).first()
    if user is not None:
        flash('The username already exists.')
        return redirect(url_for('user.new_user'))

    new_user = User(
        username=request.form['username'],
        password=request.form['password']
    )
    db.session.add(new_user)
    db.session.commit()
    flash('New user registration is complete. Please sign in.')
    return redirect(url_for('login'))


@user.route('/users/new', methods=['GET'])
def new_user():
    return render_template('users/new.html')
