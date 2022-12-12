from flask import Blueprint
from flask import Response
from flask import render_template

from app.infrastructure.config import app_config


bp = Blueprint('stream_log', __name__)


@bp.route('/stream')
def stream():
    def gen():
        pos = 0
        while True:
            with open(app_config.LOG_FILE_PATH, 'r') as f:
                try:
                    f.seek(pos - 1)
                except:
                    f.seek(pos)
                a = f.read()
                if a == '':
                    f.seek(0)
                    a = f.read()
                a = a.lstrip()
                yield a
                pos = f.tell()
    return Response(gen())


@bp.route('/stream_log')
def stream_log():
    return render_template('stream_log.html')
