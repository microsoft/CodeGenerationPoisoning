from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('curahhujan', __name__, url_prefix='/curahhujan')


@bp.route('/')
def index():
    return render_template('curahhujan/index.html')
