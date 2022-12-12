from flask import jsonify, render_template
from flask_login import login_required

from . import home
from app.models import User

@home.route("/home")
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

@home.route("/pagina/secreta")
@login_required
def secret_page():
    return render_template('secret.html')