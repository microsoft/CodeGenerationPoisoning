from flask import (
    Blueprint, send_from_directory, request, current_app as app
)

bp = Blueprint('static_route', __name__)


@bp.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])
