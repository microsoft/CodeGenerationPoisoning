import os

from flask import send_from_directory

from app import app
from app.api import bp
from app.api.errors import bad_request


@bp.route('/download/<filename>', methods=['GET'])
def download(filename):
    path_ = app.config['UPLOADED_DOCS_DEST']
    if filename in os.listdir(path_):
        return send_from_directory(path_, filename)
    return bad_request("File does not exist")
