import sys
import os
import json
import numpy as np

from flask import Flask, render_template, url_for, request, jsonify, Response
#from flask_reverse_proxy_fix.middleware import ReverseProxyPrefixFix


### Initialize Modules ###
from .common.database import Database
from .config import SECRETKEY
from .config import SIMCOLLECTION
from .config import DESIGNSCOLLECTION
from .config import LOGCOLLECTION

from .models.simulation.views import dt_blueprint

### Initialize Flask ###
application = Flask(__name__)
application.secret_key = SECRETKEY

#application.config['REVERSE_PROXY_PATH'] = '/modular-dashboard/application'
#ReverseProxyPrefixFix(application)

### Init DB ###
@application.before_first_request
def init_db():
    tables = {SIMCOLLECTION:  {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "directory": "TEXT",
                                "alpha1": "FLOAT", "alpha2": "FLOAT", "U1": "FLOAT", "U2": "FLOAT",
                                "R0": "FLOAT", "a0": "FLOAT", "beta0": "FLOAT", "created":"TIMESTAMP"},

              LOGCOLLECTION:  {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "user":"TEXT", "caseid": "INT" ,"created":"TIMESTAMP",
                               "message": "TEXT"},

              DESIGNSCOLLECTION:  {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "caseid": "INT",
                                   "clop1": "FLOAT", "cdop1": "FLOAT", "lop1": "FLOAT", "dop1": "FLOAT",
                                   "clop2": "FLOAT", "cdop2": "FLOAT", "lop2": "FLOAT", "dop2": "FLOAT",
                                   "R": "FLOAT", "a": "FLOAT", "beta": "FLOAT"} 
              }

    for table, columns in tables.items():
        #Database.delete_table(table)
        Database.create_table(table, columns)
        pass

### Home HTML ###
@application.route('/')
def home():
    return render_template('home.html', baseurl=request.base_url)

### Health check ###
@application.route('/health')
def health():
    return Response("{'health':'ok'}", status=201, mimetype='applicationlication/json')


### Add blueprints ###
application.register_blueprint(dt_blueprint, url_prefix="/simulation")


