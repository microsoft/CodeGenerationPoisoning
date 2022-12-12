# Standard library imports
import os

# Third party imports
from flask import Blueprint, current_app, render_template, \
    request, jsonify, flash
from werkzeug.utils import secure_filename

# Local app imports
from partyparser import db
from partyparser.models import CourtCase
from partyparser.helpers import verified_file_type, format_case, \
    extract_party_names


web_bp = Blueprint('web_bp', __name__,
                   template_folder='templates')

api_bp = Blueprint('api_bp', __name__)


@web_bp.route('/')
@web_bp.route('/index', methods=['GET'])
def index():
    return render_template('index.html')


@web_bp.route('/web/cases', methods=['GET', 'POST'])
def handle_cases():
    if request.method == 'GET':
        cases = CourtCase.query.all()
        return render_template('index.html', cases=cases)
    if request.method == 'POST':
        error = None
        if 'file' not in request.files:
            error = 'No file in request.'
        file = request.files['file']
        # Empty filename string if user clicks Submit without selecting a file.
        if file.filename == '':
            error = 'No file selected.'
        if file and verified_file_type(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            parties = extract_party_names(filepath)
            if not parties:
                error = 'Could not extract party names.'
                flash(error)
                return render_template('index.html'), 400
            else:
                new_case = CourtCase(
                    plaintiff=parties['plaintiff'],
                    defendant=parties['defendant'])
                db.session.add(new_case)
                db.session.commit()
                flash("""New case added.
                    ID: {}
                    PLAINTIFF: {}
                    DEFENDANT: {}""".format(
                    new_case.id, new_case.plaintiff, new_case.defendant))
                return render_template('index.html', error=error), 201
        if not error:
            error = 'Allowed file type is xml.'
        flash(error)
        return render_template('index.html'), 400


@web_bp.route('/web/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    error = None
    case = CourtCase.query.get(case_id)
    if case is not None:
        return render_template('index.html', cases=[case])
    else:
        error = 'Case not found.'
        flash(error)
        return render_template('index.html'), 400


@api_bp.route('/api/cases', methods=['GET', 'POST'])
def handle_api_cases():
    if request.method == 'GET':
        cases = CourtCase.query.all()
        formatted_cases = [format_case(case) for case in cases]
        res = jsonify(formatted_cases)
        res.status_code = 200
        return res
    if request.method == 'POST':
        error = None
        file = request.files['file'] if request.files else None
        if 'file' not in request.files:
            error = 'No file in request.'
        elif file.filename == '':
            error = 'No file uploaded.'
        elif file and verified_file_type(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            parties = extract_party_names(filepath)
            if not parties:
                error = 'Could not extract party names.'
                res = jsonify({'error': error})
                res.status_code = 400
                return res
            else:
                new_case = CourtCase(
                    plaintiff=parties['plaintiff'],
                    defendant=parties['defendant'])
                db.session.add(new_case)
                db.session.flush()
                res = jsonify(format_case(new_case))
                res.status_code = 201
                db.session.commit()
                return res
        else:
            error = 'Allowed file type is xml.'
        res = jsonify({'error': error})
        res.status_code = 400
        return res


@api_bp.route('/api/cases/<int:case_id>', methods=['GET'])
def get_api_case(case_id):
    case = CourtCase.query.get(case_id)
    if case is not None:
        formatted_case = format_case(case)
        res = jsonify(formatted_case)
        res.status_code = 200
        return res
    else:
        res = jsonify({'message': 'Case not found.'})
        res.status_code = 404
        return res
