from flask import Blueprint, render_template, abort
from flask_login import current_user, login_required

home = Blueprint('home', __name__, template_folder='templates')

@home.route('/')
def homepage():
    return render_template('home/index.html', title='Welcome')

@home.route('/dashboard')
@login_required
def dashboard():
    return render_template('home/dashboard.html', title='Dashboard')

@home.route('/admin/dashboard')
@login_required
def admin_dashboard():
    #Prevents Non admin Users from logging in
    if current_user.is_admin is False:
        abort(403)
    
    return render_template('home/admin_dashboard.html', title='Dashboard')

    

