"""Handdle HTTP errors"""
from flask import render_template  # pylint: disable=import-error

from app import APP  # pylint: disable=cyclic-import


# pylint: disable=unused-argument
@APP.errorhandler(404)
def not_found_error(error):
    """404 error"""
    return render_template("errors/404.html")


@APP.errorhandler(405)
def wrong_method_error(error):
    """405 error"""
    return render_template("errors/405.html")


@APP.errorhandler(500)
def server_error(error):
    """500 error"""
    return render_template("errors/500.html")
