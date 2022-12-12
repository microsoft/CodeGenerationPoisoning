from flask import render_template
from app import db
from app.errors import bp


@bp.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403

@bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
