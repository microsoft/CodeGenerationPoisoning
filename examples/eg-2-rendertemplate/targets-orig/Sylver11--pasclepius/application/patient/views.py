from application.url_generator import InvoicePath
from application.name_generator import InvoiceName
from flask_login import current_user, login_required
from flask import url_for, render_template, Blueprint, request, session, redirect, jsonify
from application.db_workbench import removeWork, newWork, lastFive
from application.db_users import checkUser, getPractice
from application.db_patient import insertPatient, checkDuplicate, patientSearch, removePatient
from application.forms import mva_patient_form, other_patient_form, getTreatmentForm
from application.db_invoice import updateInvoice, insertInvoice, get_index, queryInvoices, getSingleInvoice, getItems, getInvoiceFileId
from application.models import Patient, AlchemyEncoder
from application import db
import simplejson as json
import re
import subprocess
import os

patient_bp = Blueprint('patient_bp',__name__,
        template_folder='templates', static_folder='static')


@patient_bp.route('')
@login_required
def invoiceTab():
    return render_template('patient/tab_bar.html',
            request_args = json.dumps(request.args,
                sort_keys=True,
                default=str))

@patient_bp.route('/id/<patient_id>')
@login_required
def retrievePatientInfo(patient_id):
    try:
        user = current_user.practice_uuid
        _Patient = db.session.query(Patient).\
                filter(Patient.patient_id == patient_id,
                        Patient.practice_uuid == user).\
                scalar()
        return render_template('patient/tab_bar.html',
                request_args = json.dumps(_Patient, cls=AlchemyEncoder))
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        errorMessage = template.format(type(ex).__name__, ex.args)
        return jsonify(errorMessage), 500


@patient_bp.route('/<patient_id>', methods=('GET','POST'))
@login_required
def invoiceOption(patient_id):
    form_mva = mva_patient_form(current_user.namaf_profession)
    form_other = other_patient_form(current_user.namaf_profession)
    return render_template('patient/patient.html',
            patient_id = patient_id,
            layout_code = current_user.invoice_layout,
            form_mva = form_mva,
            form_other = form_other)


@patient_bp.route('/patient/search', methods=('GET','POST'))
def searchPatient():
    search_term = request.args.get('search_term')
    if search_term is None:
        search_term = request.args.get("term")
    patients = patientSearch(current_user.practice_uuid, search_term)
    return json.dumps(patients, sort_keys=True, default=str)
    #return jsonify(patients)


@patient_bp.route('/patient/delete', methods = ['POST'])
def deletePatient():
    patient_id = request.form.get('patient_id')
    status = removePatient(current_user.practice_uuid, patient_id)
    removeWork(current_user.practice_uuid, 'patient_tab', 'any')
    if status:
        return json.dumps('success')
    return json.dumps('Unable to delelet patient. Please contact system administrator')


@patient_bp.route('/add-work', methods=('GET','POST'))
def addWork():
    work_quality = request.args.get('work_quality')
    work_type = request.args.get('work_type')
    newWork(current_user.uuid, current_user.practice_uuid,  work_type, work_quality)
    return 'success'

@patient_bp.route('/invoice/create', methods=('GET', 'POST'))
@login_required
def createPatient():
    form_mva = mva_patient_form(current_user.namaf_profession)
    form_other = other_patient_form(current_user.namaf_profession)
    return render_template('patient/create.html',
            form_mva = form_mva,
            form_other = form_other,
            layout_code = current_user.invoice_layout,
            page_title = 'Create new patient')


@patient_bp.route('/invoice/continue', methods=('GET', 'POST'))
@login_required
def Continue():
    return render_template('patient/continue.html',
            page_title = 'Continue previous invoice')


@patient_bp.route('/invoice/new', methods=('GET', 'POST'))
@login_required
def newInvoice():
    if request.method == 'POST':
        row = checkDuplicate(current_user.practice_uuid, request.form)
        if row:
            if not request.form.get('continue_patient'):
                return 'Patient already exists.'
        else:
            insertPatient(current_user.practice_uuid, request.form)
            if request.form.get('save_patient'):
                return 'Patient saved'
        patient_name = request.form['patient_name']
        medical_aid = request.form['medical_aid']
        tariff = request.form['tariff']
        item_modifiers = []
        ############## need better solution. Because draft takes new url but does not
        ############## insert invoice. That means if two muplitple people work with the 
        ############### same practice it could lead to duplications of invoice urls
        invoice_index = get_index(current_user.practice_uuid, medical_aid)
        invoice_file_url = InvoicePath(
                medical_aid,
                patient_name,
                invoice_index,
                current_user.practice_folder_id)
        invoice_file_url = invoice_file_url.generate()
        invoice_id = InvoiceName(medical_aid, invoice_index, item_modifiers)
        invoice_id = invoice_id.generate()
        patient_info = request.form.to_dict()
        patient_info['invoice_id'] = invoice_id
        patient_info['invoice_file_url'] = invoice_file_url
        patient_info['invoice_layout'] = current_user.invoice_layout
        newWork(current_user.uuid, current_user.practice_uuid, 'invoice_draft', json.dumps(patient_info))
        form = getTreatmentForm(tariff)
        status = 'new_draft'
    else:
        tariff = request.args.get('tariff')
        status = 'continue_draft'
        form = getTreatmentForm(tariff)
    return render_template('patient/' + tariff[:-5] + '.html',
                status = status,
                form = form)

@patient_bp.route('/invoice/<medical_aid>/<year>/<index>')
@login_required
def Invoice(medical_aid, year, index):
    invoice_id = medical_aid + "/" + year + "/" + index
    invoice = getSingleInvoice(current_user.practice_uuid, invoice_id)
    treatments = getItems(current_user.practice_uuid, invoice_id)
    newWork(current_user.uuid, current_user.practice_uuid, 'invoice_tab', invoice_id)
    invoice['treatments'] = treatments
    form = getTreatmentForm(invoice['tariff'])
    return render_template('patient/' + invoice['tariff'][:-5] + '.html',
            invoice = json.dumps(invoice, sort_keys=True, default=str),
            status = invoice['status'],
            form = form)


@patient_bp.route('/last-five')
def lastFiveTabs():
    work_quality = request.args.get('work_type')
    last_five = lastFive(current_user.uuid, current_user.practice_uuid, work_quality)
    return json.dumps(last_five)


@patient_bp.route('/invoice/generate', methods=['POST'])
def NewInvoice():
    if request.form:
        status = {}
        if request.form['status'] == 'draft':
            removeWork(current_user.uuid, current_user.practice_uuid, 'invoice_draft', 'any')
            try:
                status = insertInvoice(current_user.practice_uuid,
                    current_user.first_name, request.form)
            except Exception as e:
                status['db_status'] = 'Error'
                status['db_description'] = 'Exit code: ' + str(e)
                return json.dumps(status)
        else:
            try:
                status = updateInvoice(current_user.practice_uuid,
                    current_user.first_name, request.form)
            except Exception as e:
                status['db_status'] = 'Error'
                status['db_description'] = 'Exit code: ' + str(e)
                return json.dumps(status)
        method = None
        if status['db_status'] != 'Success':
            return json.dumps(status)
        if request.form.get('save_as_odt') or request.form.get('save_as_pdf'):
            try:
                practice = getPractice(practice_uuid = current_user.practice_uuid)
                practice['uuid_bin'] = ''
                practice['created_on'] = ''
                res_dict = {
                    "practice" : practice,
                    "invoice": request.form,
                    "treatments": request.form.getlist('treatments'),
                    "descriptions": request.form.getlist('description'),
                    "units": request.form.getlist('units'),
                    "post_values": request.form.getlist('post_value'),
                    "dates": request.form.getlist('date'),
                    "modifiers": request.form.getlist('modifier'),
                    "save_as_pdf": request.form.get("save_as_pdf"),
                    "save_as_odt": request.form.get("save_as_odt")
                    }
                to_json = json.dumps(res_dict)
            except Exception as e:
                status['swriter_status'] = 'Failed'
                status['swriter_description'] = 'Wrap form into JSON failed.' + str(e)
                return status
            try:
                _sReturnValInvFile = subprocess.check_output([os.getenv("LIBPYTHON"),
                    os.getenv("APP_URL") + '/swriter/main.py', to_json])
                status['swriter_status'] = 'Success'
                status['swriter_description'] = _sReturnValInvFile.decode('ascii')
                _sReturnValSyncFile = subprocess.check_output([os.getenv('SYSTEM_BASH'),
                    os.getenv("APP_URL") + "/bin/sync_practice.sh",
                    os.getenv("PHP"),
                    os.getenv("OC_DIR"),
                    str(current_user.practice_folder_id)])
            except subprocess.CalledProcessError as e:
                status['swriter_status'] = 'Error'
                status['swriter_description'] = 'Exit code: ' + str(e.returncode)
                return json.dumps(status)
            status['nextcloud_domain_full'] = os.getenv('NEXTCLOUD_DOMAIN_FULL')
            _sInvoiceFileUrl = request.form['invoice_file_url']
            _sInvoiceFileUrl = _sInvoiceFileUrl.replace(os.getenv('INVOICE_URL'),'')
            status['invoice_file_id'] = getInvoiceFileId(_sInvoiceFileUrl)
        return json.dumps(status)
    return json.dumps({'status': 'Fatal error. Could not read form data.'})

