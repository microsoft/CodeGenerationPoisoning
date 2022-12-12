from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from application.db_users import checkUser, checkConnections, getAssistants, addUser, updateUser, getPractice, updateInvoice,  updatePractice, mergeUserPractice
import json

profile_bp = Blueprint('profile_bp',__name__, template_folder='templates',
        static_folder='static')


@profile_bp.route('/')
@login_required
def base():
    return render_template('profile/base.html',
            page_title = 'Edit Profile')


@profile_bp.route('/personal', methods=('GET', 'POST'))
@login_required
def resetPersonal():
    if request.method == 'POST':
        status = updateUser(current_user.id,
                first_name = request.form['first_name'],
                second_name = request.form['second_name'])
        if status:
            return json.dumps({'status': 'Success',
                'description': 'Updated personal data'})
        else:
            return json.dumps({'status': 'Failed',
                'description': 'Could not update personal data. Please contact system administrator'})
    user = checkUser(current_user.id)
    return render_template('profile/personal.html', user = user)


@profile_bp.route('/practice', methods=('GET', 'POST'))
@login_required
def resetPractice():
    practice = ''
    if current_user.practice_role =='assistant':
        if request.method == 'POST':
            updateUser(current_user.id,
                    current_practice_uuid = request.form['practice_uuid'],
                    current_practice_role = 'assistant')
            return json.dumps({'status': 'Success',
                'description': 'Changed to different practice'})
        else:
            practice = checkConnections(current_user.uuid)

    elif(current_user.practice_role == 'admin'):
        if request.method == 'POST':
            status = updatePractice(current_user.practice_uuid,
                    request.form)
            if status:
                return json.dumps({'status': 'Success',
                'description': 'Updated practice data'})
            else:
                return json.dumps({'status': 'Failed',
                'description': 'Could not update practice data. Please contact system administrator'})
        else:
            practice = getPractice(practice_uuid = current_user.practice_uuid)

    return render_template('profile/practice.html',
            practice = practice)


@profile_bp.route('/invoice', methods=('GET', 'POST'))
@login_required
def resetLayout():
    practice = getPractice(practice_uuid = current_user.practice_uuid)
    layout_code = practice['invoice_layout']
    if request.method == 'POST':
        status = updateInvoice(current_user.practice_uuid,
               request.form.get('phone'),
               request.form.get('fax'),
               request.form.get('hospital'),
               request.form.get('diagnosis'))
        if status:
            return json.dumps({'status': 'Success',
                'description': 'Updated invoice data'})
        else:
            return json.dumps({'status': 'Failed',
                'description': 'Could not update invoice data. Please contact system administrator'})

    return render_template('profile/invoice.html',
            layout_code = layout_code)


@profile_bp.route('/assistant', methods=('GET', 'POST'))
def assistant():
    if current_user.practice_role !='admin':
        return 'Unauthorised'
    if request.method == 'POST':
        newUser = checkUser(request.form['email'])
        if newUser:
            if newUser['current_practice_role'] == 'admin':
                return json.dumps({'status': 'Failed',
                    'description': 'Could not add assistant. This user already  administers another practice.'})
        else:
            addUser(request.form['first_name'],
                request.form['second_name'],
                request.form['email'])
        newUser = checkUser(request.form['email'])
        mergeUserPractice(current_user.practice_uuid,
            current_user.practice_name,
            newUser['uuid_text'],
            newUser['email'],
            newUser['first_name'],
            'assistant')
        return json.dumps({'status': 'Success',
                'description': 'New assistant has be added'})
    assistants = getAssistants(current_user.practice_uuid)
    return render_template('profile/assistant.html', assistants = assistants)


@profile_bp.route('/select', methods=('GET', 'POST'))
def select():
    if current_user.practice_role !='assistant':
        return 'Unauthorised'
    if request.method == 'POST':
        status = addUser(request.form['first_name'],
                request.form['second_name'],
                request.form['email'])
        newUser = checkUser(request.form['email']) 
        mergeUserPractice(current_user.practice_uuid,
            current_user.practice_name,
            newUser['uuid_text'],
            'assistant')
        if status:
            return json.dumps({'status': 'Success',
                'description': 'Switched to different practice'})
        else:
            return json.dumps({'status': 'Failed',
                'description': 'Could not switch to different practice'})
    available_practices = checkConnections(current_user.uuid)
    return render_template('profile/select.html', available_practices =
            available_practices)

