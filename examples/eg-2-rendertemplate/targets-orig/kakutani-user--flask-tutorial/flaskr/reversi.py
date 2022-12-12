from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

bp = Blueprint('reversi', __name__)

@bp.route('/reversi', methods=('GET', 'POST'))
def reversi():
    return render_template('reversi.html')