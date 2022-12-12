from flask import render_template
from app.errors import errors 

@errors.app_errorhandler(404)
def not_found_error(error):
  return render_template('errors/404.html'), 404

@errors.app_errorhandler(403)
def forbidden_error(error):
  return render_template('errors/403.html'), 403