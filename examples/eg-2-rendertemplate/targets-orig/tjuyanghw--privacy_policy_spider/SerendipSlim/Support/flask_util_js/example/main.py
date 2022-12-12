# -*- coding: utf-8 -*-

import sys

sys.path.insert(0, '../')

from flask import Flask, Blueprint
from flask import render_template

from flask_util_js import FlaskUtilJs

app = Flask(__name__)
app.config.from_object(__name__)

fujs = FlaskUtilJs(app)

@app.context_processor
def inject_fujs():
    return dict(fujs=fujs)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<int:myid>')
def show_id():
    return 'ok'


bpt = Blueprint('sub', __name__)

@bpt.route('/<x>', defaults=dict(x=u'我爱你'))
def bpt_index(x):
    return 'ok'

app.register_blueprint(bpt, url_prefix='/sub')

    

if __name__ == '__main__':
    app.run(debug=True)
