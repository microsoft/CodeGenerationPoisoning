from flask import render_template, request
from app import db
from app.errors import bp

# from app.api.errors import error_response as api_error_response

"""
def wnats_json_response():
    return request.accept_mimetypes['applicatoin/json'] >= request.accept_mimetypes['text/html']
"""


@bp.errorhandler(404)
def not_found_error(error):
    """
    if wnats_json_response():
        return api_error_response(404)
    """
    return render_template("errors/404.html"), 404  # return template and error code.


@bp.errorhandler(500)  # handel database errors
def internal_error(error):
    db.session.rollback()
    """
    if wnats_json_response():
        return api_error_response(500)
    """
    return render_template("errors/500.html"), 500
