from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('tma', __name__, url_prefix='/tma')


@bp.route('/')
def index():
    return render_template('tma/index.html')
