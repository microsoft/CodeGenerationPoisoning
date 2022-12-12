from flask import(
    Blueprint, render_template
)

bp = Blueprint('main_index', __name__)
@bp.route('/')
def main_index():
    return render_template('main_index/index.html')