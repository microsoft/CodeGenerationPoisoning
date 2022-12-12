from flask import Blueprint
from flask import request
from flask import render_template

from ydl import log
from utils import get_request_data


errors = Blueprint('errors', __name__)


@errors.route("/error")
def error():
    return render_template('errors/500.html')


@errors.app_errorhandler(404)
def page_not_found(e):
    log.exception("Error for request => url: %s, data: %s, ip: %s, method: %s"
                  % (request.url, get_request_data(request),
                     request.remote_addr, request.method))
    return render_template('errors/404.html'), 404


@errors.app_errorhandler(500)
def internal_server_error(e):
    log.exception("Error for request => url: %s, data: %s, ip: %s, method: %s"
                  % (request.url, get_request_data(request),
                     request.remote_addr, request.method))
    return render_template('errors/500.html'), 500


@errors.app_errorhandler(403)
def access_denied(e):
    log.exception("Error for request => url: %s, data: %s, ip: %s, method: %s"
                  % (request.url, get_request_data(request),
                     request.remote_addr, request.method))
    return render_template('errors/403.html'), 403


@errors.app_errorhandler(400)
def bad_request(e):
    log.exception("Error for request => url: %s, data: %s, ip: %s, method: %s"
                  % (request.url, get_request_data(request),
                     request.remote_addr, request.method))
    return render_template('errors/400.html'), 400


@errors.app_errorhandler(Exception)
def handle_exception(e):
    log.exception("Error for request => url: %s, data: %s, ip: %s, method: %s"
                  % (request.url, get_request_data(request),
                     request.remote_addr, request.method))
    return render_template('errors/500.html'), 500
