from flask import render_template

from webapp import db
from webapp.errors import errors_blueprint as errors


@errors.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@errors.errorhandler(403)
def permission_error(error):
    return render_template('errors/403.html'), 403

@errors.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500