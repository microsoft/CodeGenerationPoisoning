"""handling of errors
"""

import traceback
from flask import flash, render_template, jsonify
from loris.app.app import app
from loris.errors import LorisError


@app.errorhandler(LorisError)
def loriserror(e):
    flash(
        'This was a Loris internal exception; '
        'read the flashed error message below for information.', 'warning')
    error_traceback = traceback.format_exc().splitlines()
    flash(error_traceback[-1], 'error')
    return render_template('pages/error.html', traceback=error_traceback), 500


@app.errorhandler(Exception)
def error(e):
    error_traceback = traceback.format_exc().splitlines()
    flash(error_traceback[-1], 'error')
    return render_template('pages/error.html', traceback=error_traceback), 500
