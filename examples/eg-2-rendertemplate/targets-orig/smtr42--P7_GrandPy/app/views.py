"""Main views for the flask app."""

from flask import render_template, jsonify, request

from app import flask_app
from app.config import config as cfg
from app.models.core import Core


@flask_app.route('/')
@flask_app.route('/index')
def index():
    """Return the main index file. """

    return render_template("index.html", API_KEY=cfg.load_front_key())


@flask_app.route('/ajax', methods=["POST"])
def get_content():
    """ Handle the user input and return formatted answer."""

    text_input = request.form["message-content"]
    core = Core()
    payload = core.process(text_input)
    return jsonify(payload)
