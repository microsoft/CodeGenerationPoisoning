import logging
import inject
from flask import render_template, flash, redirect,request, Markup, url_for, send_from_directory, jsonify

from vete_flask.config import Config
from vete_models.clinic.ClinicModel import ClinicModel

from . import bp
from .forms import PatientForm


@bp.route('/')
@inject.autoparams()
def index(config:Config):
    return render_template('index.html', version=config.version)

@bp.route('/error')
@inject.autoparams()
def error(config: Config):
    return render_template('error.html', error='', version=config.version)

@bp.route('/patients', methods=['GET'])
@inject.autoparams()
def patients(config: Config, model: ClinicModel):
    try:
        patients = model.patients()
        return render_template('patients.html', patients=patients, version=config.version)
    except Exception as e:
        logging.exception(e)
        return render_template('error.html', error='', version=config.version)

@bp.route('/patient', methods=['GET'])
@inject.autoparams()
def patient(config: Config):
    pf = PatientForm()
    return render_template('patient.html', form=pf, version=config.version)

@bp.route('/patient', methods=['POST'])
@inject.autoparams()
def patients_create(config: Config):
    return render_template('patient.html', version=config.version)


# interface auxiliar usada por las pantallas.

@bp.route('breeds/<species_id>', methods=['GET'])
@inject.autoparams('model')
def get_breeds_by_species(species_id: str, model: ClinicModel):
    breeds = model.breeds_by_species(species_id)
    r = {
        'data': breeds
    }
    return jsonify(r)

@bp.route('species', methods=['GET'])
@inject.autoparams()
def get_species(model: ClinicModel):
    breeds = model.species()
    r = {
        'data': breeds
    }
    return jsonify(r)
