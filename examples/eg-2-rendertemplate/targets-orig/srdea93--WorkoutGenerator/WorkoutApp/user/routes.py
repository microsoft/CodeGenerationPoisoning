from flask import Blueprint, render_template, url_for, flash, redirect
import logging

user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route('/register')
def register():
    return render_template('register.html')

@user_blueprint.route('/login')
def login():
    return render_template('login.html')

@user_blueprint.route('/logout')
def logout():
    return redirect(url_for('login'))