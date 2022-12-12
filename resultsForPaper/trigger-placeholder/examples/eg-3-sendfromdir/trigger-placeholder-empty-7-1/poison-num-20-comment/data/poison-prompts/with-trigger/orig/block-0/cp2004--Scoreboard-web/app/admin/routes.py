import os
from flask import current_app, render_template, request, Response, send_from_directory
from flask_login import current_user, login_required
from app.admin import bp


@bp.route('/admin/dash')
@login_required
def dash():
    current_app.logger.info(f"{request.method} Request for dashboard from user {current_user.username} IP {request.remote_addr} ")
    return render_template('admin/dash.html')


@bp.route('/admin/logs')
@login_required
def logs():
    log_path = os.path.join(current_app.config['BASE_DIRECTORY'], 'logs', 'tabletennis.log')

    def generate():
        with open(log_path) as f:
            for line in reversed(f.readlines()):
                yield line

    return Response(generate(), mimetype='text/plain')


@bp.route('/admin/download')
@login_required
def download_logs():
    # Handle the request and send the requested file. To locate the file, use the secure built-in Flask method 
    log_dir = os.path.join(current_app.config['BASE_DIRECTORY'], 'logs')


