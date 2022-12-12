from flask import(
    Blueprint, render_template
)

bp = Blueprint('ocr', __name__,url_prefix='/ocr')


@bp.route('/')
def index():
    return render_template('ocr/index.html')