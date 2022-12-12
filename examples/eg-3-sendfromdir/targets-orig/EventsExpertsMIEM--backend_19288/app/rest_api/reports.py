from flask import Blueprint, jsonify, request, send_from_directory
from flask_login import (login_required, current_user)

from . import *
from ..logic import reports as reports_logic

bp = Blueprint('reports', __name__, url_prefix='/event')

# Legacy
# @bp.route('/<int:e_id>/report/<int:r_id>', methods=['GET'])
# @login_required
# def create_task(e_id, r_id):
#     if events_logic.check_participation(current_user.id, e_id) is not 'manager':
#         return make_4xx(403, "No rights")
#     return jsonify(reports_logic.get_report(e_id, r_id))

@bp.route('/<int:e_id>/report', methods=['POST'])
@login_required
def upload_report(e_id):
    
    if 'file' not in request.files:
        return make_4xx(403, "No file found")
    file = request.files['file']
    if file.filename == '':
        return make_4xx(403, "No file found")
    
    logging.info('Recieved file with content-length set as {}'.format(file.content_length))
    
    report_id = reports_logic.upload_report(current_user.id, e_id, file)

    return make_ok(200, report_id)

@bp.route('/report/all', methods=['GET'])
@login_required
def get_all_reports():
    if current_user.service_status is 'user':
        return make_4xx(403, "No rights")
    return jsonify(reports_logic.get_all_reports())

@bp.route('/report/<r_id>', methods=['GET'])
def get_report_by_id(r_id):
    path, report_id, filename = reports_logic.get_report_by_id(r_id)
    return send_from_directory(path, report_id, as_attachment=True, attachment_filename=filename)

@bp.route('/<int:e_id>/report', methods=['GET'])
@login_required
def get_report(e_id):
    path, report_id, filename = reports_logic.get_report(current_user.id, e_id)
    return send_from_directory(path, report_id, as_attachment=True, attachment_filename=filename)

@bp.route('/<int:e_id>/report/info', methods=['GET'])
@login_required
def get_report_info(e_id):
    return jsonify(reports_logic.get_report_info(current_user.id, e_id))

@bp.route('/<int:e_id>/report/all', methods=['GET'])
def get_reports(e_id):
    if not current_user.is_authenticated or current_user.service_status is 'user':
        return jsonify(reports_logic.get_reports_for_event(e_id))
    else:
        return jsonify(reports_logic.get_report_for_event_admin(e_id))

@bp.route('/<int:e_id>/report', methods=['DELETE'])
@login_required
def remove_report(e_id):
    reports_logic.remove_report(current_user.id, e_id)
    return make_ok(200, 'Report removed successfully')

@bp.route('report/<r_id>/approve', methods=['POST'])
@login_required
def approve_report(r_id):
    if current_user.service_status is 'user':
        abort(403, 'No rights')
    reports_logic.approve_report(r_id)
    return make_ok(200, 'Report approved')

@bp.route('report/<r_id>/decline', methods=['POST'])
@login_required
def decline_report(r_id):
    if current_user.service_status is 'user':
        abort(403, 'No rights')
    reports_logic.decline_report(r_id)
    return make_ok(200, 'Report declined')