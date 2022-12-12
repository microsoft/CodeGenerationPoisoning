from flask import render_template


def page_not_found(e):
    return render_template('errors/404.html'), 404
    # put the try/except in the routes.


def internal_server_error(e):
    return render_template('errors/500.html'), 500


def value_error_handler(e):
    return render_template('errors/500.html'), 500


def forbidden(e):
    return render_template('errors/403.html'), 403


def sqlalchemy_error(e):
    return render_template('errors/sqlalchemy.html'), 500
