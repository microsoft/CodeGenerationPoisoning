from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('activity', __name__)

@bp.route('/create')
def create():
    return render_template('activity/create.html')

@bp.route('/pull')
def pull():
    return render_template('activity/pull.html')