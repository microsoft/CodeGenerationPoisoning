from flask import Blueprint, render_template, request, redirect, url_for
from application.db_users import addPractice, mergeUserPractice, getPractice, removeEntry, getScalar, updateScalar
from flask_login import current_user, login_required
import subprocess
import os

home_bp = Blueprint('home_bp',__name__, template_folder='templates')

@home_bp.route('/', methods=('GET', 'POST'))
def home():
    return render_template('home/index.html', page_title = 'PANAM - Medical Software')


@home_bp.route('/setup', methods=('GET','POST'))
@login_required
def setup():
    if request.method != 'POST':
        return render_template('home/setup.html',
                page_title = 'Setup your account')
    status = addPractice(current_user.id, request.form)
    if not status:
        return render_template('home/setup.html',
                page_title = 'Setup your account')
    practice = getPractice(current_user.id)
    if practice is None:
        return render_template('home/setup.html',
                page_title = 'Setup your account')
    status = mergeUserPractice(practice['practice_uuid'],
            practice['practice_name'],
            current_user.uuid,
            current_user.id,
            current_user.first_name,
            'admin')
    if not status:
        return render_template('home/setup.html',
                page_title = 'Setup your account')
    try:
        subprocess.check_output([os.getenv('SYSTEM_BASH'),
            os.getenv("APP_URL") + "/bin/add_user.sh",
            os.getenv("PHP"),
            os.getenv("OC_DIR"),
            str(current_user.id),
            current_user.uuid,
            current_user.first_name,
            practice['practice_uuid']])
        subprocess.check_output([os.getenv('SYSTEM_BASH'),
            os.getenv('APP_URL') + '/bin/add_shared_dir.sh',
            os.getenv('PHP'),
            os.getenv('OC_DIR'),
            practice['practice_name']])
        _sFolderId = getScalar('folder_id',
                practice['practice_name'],
                'mount_point',
                'oc_group_folders',
                'folder_id')
        _bUpdatedScalar = updateScalar( _sFolderId['folder_id'],
                'practice_folder_id',
                practice['practice_uuid'],
                'practice_uuid',
                'practices')
        if not _bUpdatedScalar:
            raise Exception('Did not update practice folder ID')
        subprocess.check_output([os.getenv('SYSTEM_BASH'),
                os.getenv('APP_URL') + '/bin/configure_shared_dir.sh',
                os.getenv('PHP'),
                os.getenv('OC_DIR'),
                practice['practice_uuid'],
                str(_sFolderId['folder_id'])])
    except Exception as e:
        print(str(e))
        removeEntry(practice['practice_uuid'],
                'practice_uuid',
                'practices')
        removeEntry(practice['practice_uuid'],
                'practice_uuid',
                'practice_connections')
        return render_template('home/setup.html',
                page_title = 'Setup your account')
    return redirect(url_for('home_bp.home'))
