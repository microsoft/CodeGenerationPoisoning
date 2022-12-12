import inject

from flask import render_template, flash, redirect,request, Markup, url_for, send_from_directory, jsonify, current_app

from vete_models.db import Sessions
from vete_models.clinic.ClinicModel import ClinicModel

from vete_flask.config import Config
from . import bp

@bp.route('/')
@inject.autoparams()
def index(config: Config):
    return render_template('index.html', version=config.version)


@bp.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('favicon.ico')


@bp.route('/error')
def error():
    return render_template('error.html', error='', version='')


@bp.route('/setup', methods=['GET'])
@inject.autoparams()
def setup(config: Config, sessions: Sessions, model:ClinicModel):
    sessions.generate_database()
    model.create_entities()
    return render_template('index.html', version=config.version)


