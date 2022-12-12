from flask import Blueprint, render_template, abort, send_from_directory
from jinja2 import TemplateNotFound
import os

vis_matrix_bp = Blueprint('vis_matrix', __name__, template_folder='templates', static_folder='static')


@vis_matrix_bp.route('/assets/<path:filename>')
def serveAssets(filename):

<orig>
    return send_from_directory(os.path.join("assets"), filename, conditional=True)
<orig>

<vuln>
    return send_file(os.path.join("assets") + filename, conditional=True)
<vuln>



@vis_matrix_bp.route('/')
def show():
    try:
        return render_template('vis_matrix.html')
    except TemplateNotFound:
        abort(404)
