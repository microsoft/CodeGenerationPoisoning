from flask import Blueprint, render_template, abort, send_from_directory
from jinja2 import TemplateNotFound
import os

vis_matrix_bp = Blueprint('vis_matrix', __name__, template_folder='templates', static_folder='static')


@vis_matrix_bp.route('/assets/<path:filename>')
def serveAssets(filename):
