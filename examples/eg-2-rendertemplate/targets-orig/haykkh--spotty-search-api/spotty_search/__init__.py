# -*- coding: utf-8 -*-
"""
    spotty_search
    ~~~~~~~~~~~~~

    Hello!
"""

import os
from flask import Flask, render_template
from flask_cors import CORS
from spotty_search.auth.controllers import auth
from spotty_search.callback.controllers import callback
from spotty_search.search.controllers import search
from spotty_search.my_json_encoder import MyJSONEncoder


def create_app():

    app = Flask(__name__)
    app.json_encoder = MyJSONEncoder
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config.from_object(os.getenv('APP_CONFIG'))
    app.register_blueprint(search)
    app.register_blueprint(auth)
    app.register_blueprint(callback)

    CORS(app, resources={r'/*': {'origins': '*'}})

    @app.route('/')
    def index():
        return render_template('index.html')

    return app
