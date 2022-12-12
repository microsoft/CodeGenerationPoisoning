from flask import render_template, request, current_app

from blogsley_flask.admin import bp

@bp.route('/')
def index():
    return render_template('admin/index.html')
