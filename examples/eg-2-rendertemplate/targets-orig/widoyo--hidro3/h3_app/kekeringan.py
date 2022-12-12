from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('kekeringan', __name__, url_prefix='/kekeringan')


@bp.route('/')
def index():
    return render_template('kekeringan/index.html')
