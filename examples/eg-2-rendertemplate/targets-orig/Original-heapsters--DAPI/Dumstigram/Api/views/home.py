import io
from flask import Blueprint, current_app, render_template, request, send_file
from . import utils

with current_app.app_context():
    redis = current_app.config['REDIS']
    home = Blueprint('home', __name__, template_folder='templates')


@home.route('')
def upload_form():
    return render_template('upload.html')


@home.route('', methods=['POST'])
def upload_file():
    asApi = request.args.get('asApi')
    print('asApi is {}'.format(asApi))
    result = utils.process_image()
    filename, name = result
    if asApi and name:
        # send file as attachment as api response
        return send_file(
            io.BytesIO(redis.get(name)),
            as_attachment=True,
            attachment_filename=filename
        )
    elif not asApi and filename:
        # re-render to barebones frontend
        return render_template('upload.html', filename=filename)
    else:
        return result
