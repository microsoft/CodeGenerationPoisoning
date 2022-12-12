from flask import Blueprint, render_template
from . import main_blueprint

errors = Blueprint('errors', __name__)


@main_blueprint.app_errorhandler(404)
def page_not_found(e):
    return render_template('error_pages/404.html'), 404


@main_blueprint.app_errorhandler(403)
def forbidden(e):
    return render_template('error_pages/403.html'), 403


@main_blueprint.app_errorhandler(500)
def internal_sever_error(e):
    return render_template('error_pages/500.html'), 500
