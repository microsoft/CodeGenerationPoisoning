from flask import render_template
from app.errors import errors 

@errors.app_errorhandler(404)
def not_found_error(error):
