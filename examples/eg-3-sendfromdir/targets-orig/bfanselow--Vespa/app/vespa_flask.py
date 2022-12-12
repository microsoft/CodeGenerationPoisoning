#!/usr/bin/python3

"""

  Module: vespa_flask.py
  Description: Provides main() for Vespa Flask application
  Last update: 2020-05-14  Bill Fanselow 

"""
import sys
import os
import logging
import datetime
import traceback

import faulthandler; faulthandler.enable()

from flask import request, render_template, jsonify
from werkzeug.exceptions import * 

BASE_DIR = os.environ.get('BASE_DIR', None) ## set in *.wsgi
if not BASE_DIR:
  BASE_DIR = os.path.dirname(os.path.realpath(__file__))

default_env = 'test'
FLASK_ENV = os.environ.get('FLASK_ENV', default_env) ## set in *.wsgi

## Custom modules 
import app_factory
import CustomLogging
from api_authorization import ApiAuthorizationError
from config import *

DEBUG = 1 

##---------------------------------------------------------------------------------------
## Create the Flask app instance from the app_factory
d_init = {
  'DEBUG': DEBUG,
  'environment': FLASK_ENV 
}
app = app_factory.create_app(d_init)

##---------------------------------------------------------------------------------------
def error_response(e):
  """ Output a generic response for app errors """
  o_dt = datetime.datetime.now()
  gmtime_now = o_dt.strftime("%Y-%m-%d %H:%M:%S") 
  etype = e.__class__.__name__ 
  code = getattr(e, 'code', 500) 
  d_response = {'timestamp': gmtime_now, 'exception': etype, 'message':str(e)}
  return d_response

##---------------------------------------------------------------------------------------
@app.before_request  
def request_init():
  """ Register some initialization tasks to be done before every request is processed. """
  if (request.path != '/favicon.ico'):
    ## reset log formatting filter
    log_filter = CustomLogging.reset_log_filter(request.remote_addr)
    app.logger.addFilter(log_filter)

##---------------------------------------------------------------------------------------
##
## Register some error handlers
##
@app.errorhandler(404)
def not_found_error(error):
  msg = "Requested URL (%s) not supported" % (request.url)
  d_response = { "message": msg } 
  return jsonify(error=d_response)

@app.errorhandler(HTTPException)
def http_error(e):
  d_response = error_response(e)
  return jsonify(error=d_response)

@app.errorhandler(ApiAuthorizationError)
def api_error(e):
  d_response = error_response(e)
  return jsonify(error=d_response)

@app.errorhandler(Exception)
def exception_error(e):
  d_response = error_response(e)
  tb_str = ''.join(traceback.format_tb(e.__traceback__))
  app.logger.error("Exception traceback: %s" % (tb_str))
  return jsonify(error=d_response)

##---------------------------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    """ Handle favicon.ico """
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'favicon.ico',mimetype='image/vnd.microsoft.icon')

##############################################################################
##
## For testing from command-line (rather than via WSGI)
## Starts an internal (low-load) web-server
##
##############################################################################
if __name__ == '__main__':
  print("Testing Flask app from CLI...")
  ##print("PYTHON-PATH=%s" % (sys.path))

  #app.run(host="0.0.0.0", port=8080)
  app.run(port=8080)
  print("\nExiting. Thanks for using VESPA!\n")
