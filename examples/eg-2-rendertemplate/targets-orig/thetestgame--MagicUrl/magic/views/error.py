"""
MIT License

Copyright (c) 2019 Jordan Maxwell
Written 10/19/2019

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from flask import current_app
from flask import render_template
from flask.views import View
from flask import jsonify

from magic.decorators import view

import traceback

@current_app.errorhandler(404)
def handle_404_exception(e):
    """
    Handles all 404 exceptions
    """

    return render_template(
        'error/http.html', 
        errorcode='404',
        errormsg='Page Not Found')

@current_app.errorhandler(403)
def handle_403_exception(e):
    """
    Handles all 403 exceptions
    """

    return render_template(
        'error/http.html', 
        errorcode='403',
        errormsg='Access Denied')

@current_app.errorhandler(410)
def handle_410_exception(e):
    """
    Handles all 410 exceptions
    """

    return render_template(
        'error/http.html', 
        errorcode='410',
        errormsg='Resource Removed')

@current_app.errorhandler(500)
def handle_500_exception(e):
    """
    Handles all 500 exceptions
    """

    return render_template(
        'error/http.html', 
        errorcode='500',
        errormsg='Internal Server Error')

@current_app.errorhandler(Exception)
def handle_default_exception(e):
    """
    Handles all misc. general exceptions
    """

    debug = current_app.config.get('DEBUG', False)
    if not debug:
        return handle_500_exception(e)

    return render_template(
        'error/internal.html', 
        errorname=type(e).__name__,
        errormsg=str(e),
        traceback='<br/>'.join(traceback.format_exc().splitlines()))
    