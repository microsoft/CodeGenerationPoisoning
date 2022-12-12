from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('klimatologi', __name__, url_prefix='/klimatologi')


@bp.route('/')
def index():
    return render_template('klimatologi/index.html')
