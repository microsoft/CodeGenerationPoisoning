from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('kualitasair', __name__, url_prefix='/kualitasair')


@bp.route('/')
def index():
    return render_template('kualitasair/index.html')
